"""
Transcription API endpoints.
"""

from typing import List
import uuid
import os
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

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionCreate)
async def upload_and_transcribe(
    audio: UploadFile = File(...),
    options: TranscriptionOptions = Form(TranscriptionOptions()),
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

        # Update transcription with options
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id).first()
        if transcription:
            transcription.model_type = options.model_type
            transcription.quality = options.quality
            db.commit()

        # Start async transcription task
        process_transcription.delay(transcription_id)

        return TranscriptionCreate(
            transcription_id=transcription_id,
            original_filename=audio.filename or "unknown",
            file_size=file_size
        )

    except Exception as e:
        # Clean up on error
        FileService.delete_transcription_files(transcription_id, db)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transcribe/{transcription_id}/status", response_model=TranscriptionStatusResponse)
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

    return TranscriptionStatusResponse(
        id=transcription_id,
        status=transcription.status,
        progress=progress,
        estimated_completion=None,  # TODO: Implement estimated completion calculation
        error_message=transcription.error_message,
        updated_at=transcription.updated_at
    )


@router.get("/transcribe/{transcription_id}/result", response_model=TranscriptionResponse)
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
    # TODO: Implement result retrieval
    # Placeholder implementation
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    return TranscriptionResponse.from_orm(transcription)


@router.get("/transcriptions", response_model=TranscriptionListResponse)
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


@router.delete("/transcribe/{transcription_id}")
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


@router.get("/transcribe/{transcription_id}/download")
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
