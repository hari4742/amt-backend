"""
Transcription API endpoints.
"""

from typing import List, Optional
import uuid
import os
import json
import base64
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.transcription import (
    TranscriptionCreate,
    TranscriptionResponse,
    TranscriptionStatusResponse,
    TranscriptionOptions,
    TranscriptionListResponse
)
from app.models.transcription import Transcription, TranscriptionStatus
from app.services.file_service import FileService
from app.services.transcription_tasks import process_transcription
import pretty_midi

router = APIRouter()


@router.post("/")
async def upload_and_transcribe(
    audio: UploadFile = File(...),
    options: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload an audio file and start transcription process.

    Args:
        audio: Audio file to transcribe
        options: Transcription options
        db: Database session

    Returns:
        Transcription creation response with ID
    """
    # Generate unique transcription ID
    transcription_id = str(uuid.uuid4())

    try:
        # Save audio file and create transcription record
        audio_path, file_size = await FileService.save_audio_file(
            audio, transcription_id, db
        )

        # Parse and apply options sent as JSON string
        model_type = "default"
        quality = "medium"
        try:
            if options:
                parsed = json.loads(options)
                # Map frontend option names to backend fields
                frontend_model = parsed.get("model")
                if frontend_model:
                    model_type = str(frontend_model)
                frontend_quality = parsed.get("quality")
                if frontend_quality:
                    quality_map = {"fast": "low", "balanced": "medium", "high": "high"}
                    quality = quality_map.get(str(frontend_quality), "medium")
        except Exception:
            # Ignore malformed options and use defaults
            pass

        # Update transcription with options
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id).first()
        if transcription:
            transcription.model_type = model_type
            transcription.quality = quality
            db.commit()

        # Start async transcription task
        process_transcription.delay(transcription_id)

        return {
            "success": True,
            "transcriptionId": transcription_id,
            "status": "processing",
            "progress": 0
        }

    except Exception as e:
        # Clean up on error
        FileService.delete_transcription_files(transcription_id, db)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{transcription_id}/status")
async def get_status(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the status of a transcription task.

    Args:
        transcription_id: Unique identifier for the transcription
        db: Database session

    Returns:
        Current status and progress information
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Calculate progress based on status
    progress = 0.0
    if transcription.status == TranscriptionStatus.PENDING:
        progress = 0.0
    elif transcription.status == TranscriptionStatus.PROCESSING:
        progress = 50.0  # Simplified progress calculation
    elif transcription.status == TranscriptionStatus.COMPLETED:
        progress = 100.0
    elif transcription.status == TranscriptionStatus.FAILED:
        progress = 0.0

    # Map pending -> processing for frontend expectations
    status_value = transcription.status
    if status_value == TranscriptionStatus.PENDING:
        status_value = TranscriptionStatus.PROCESSING

    # Basic ETA placeholder (None for now)
    return {
        "transcriptionId": transcription_id,
        "status": status_value,
        "progress": progress,
        "estimatedTimeRemaining": None
    }


@router.get("/{transcription_id}/result")
async def get_result(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the result of a completed transcription.

    Args:
        transcription_id: Unique identifier for the transcription
        db: Database session

    Returns:
        Transcription result with MIDI data
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if transcription.status != TranscriptionStatus.COMPLETED:
        return {
            "success": False,
            "transcriptionId": transcription_id,
            "status": transcription.status,
            "error": transcription.error_message or "Transcription not completed"
        }

    if not transcription.midi_path or not os.path.exists(transcription.midi_path):
        raise HTTPException(status_code=404, detail="MIDI file not found")

    # Read MIDI file and encode as base64 string
    try:
        with open(transcription.midi_path, "rb") as f:
            midi_bytes = f.read()
        midi_b64 = base64.b64encode(midi_bytes).decode("ascii")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read MIDI: {str(e)}")

    # Extract note events (simplified)
    notes = []
    try:
        pm = pretty_midi.PrettyMIDI(transcription.midi_path)
        for instrument in pm.instruments:
            for note in instrument.notes:
                notes.append({
                    "note": int(note.pitch),
                    "velocity": int(note.velocity),
                    "startTime": float(note.start),
                    "endTime": float(note.end),
                    "channel": 0
                })
        duration = transcription.duration or pm.get_end_time()
    except Exception:
        duration = transcription.duration or 0.0

    return {
        "success": True,
        "transcriptionId": transcription_id,
        "status": TranscriptionStatus.COMPLETED,
        "progress": 100,
        "result": {
            "midiData": midi_b64,
            "duration": duration,
            "notes": notes,
            "metadata": {
                "model": transcription.model_type,
                "processingTime": transcription.processing_time or 0.0,
                "confidence": transcription.confidence_score or 0.0
            }
        }
    }


@router.get("/", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db)
):
    """
    List all transcriptions with pagination.

    Args:
        page: Page number
        size: Page size
        db: Database session

    Returns:
        Paginated list of transcriptions
    """
    # TODO: Implement pagination
    # Placeholder implementation
    total = db.query(Transcription).count()
    transcriptions = db.query(Transcription).offset(
        (page - 1) * size).limit(size).all()

    return TranscriptionListResponse(
        transcriptions=[TranscriptionResponse.from_orm(
            t) for t in transcriptions],
        total=total,
        page=page,
        size=size
    )


@router.delete("/{transcription_id}")
async def delete_transcription(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a transcription and associated files.

    Args:
        transcription_id: Unique identifier for the transcription
        db: Database session

    Returns:
        Success message
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # Delete files and database record
    success = FileService.delete_transcription_files(transcription_id, db)

    if success:
        return {"message": "Transcription deleted successfully"}
    else:
        raise HTTPException(
            status_code=500, detail="Failed to delete transcription files")


@router.delete("/{transcription_id}/cancel")
async def cancel_transcription(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    Cancel an ongoing transcription.

    Args:
        transcription_id: Unique identifier for the transcription
        db: Database session

    Returns:
        Success response
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if transcription.status in [TranscriptionStatus.COMPLETED, TranscriptionStatus.FAILED]:
        return {"message": "Transcription already finished"}

    transcription.status = TranscriptionStatus.FAILED
    transcription.error_message = "Cancelled by user"
    db.commit()

    return {"message": "Transcription cancelled"}


@router.get("/{transcription_id}/download")
async def download_midi(
    transcription_id: str,
    db: Session = Depends(get_db)
):
    """
    Download the generated MIDI file.

    Args:
        transcription_id: Unique identifier for the transcription
        db: Database session

    Returns:
        MIDI file download
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if transcription.status != TranscriptionStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Transcription is not completed")

    if not transcription.midi_path or not os.path.exists(transcription.midi_path):
        raise HTTPException(status_code=404, detail="MIDI file not found")

    filename = f"{transcription_id}.mid"
    return FileResponse(
        path=transcription.midi_path,
        filename=filename,
        media_type="audio/midi"
    )
