"""
Advanced API endpoints for Phase 5 features.
"""

import os
from typing import List, Optional, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from app.core.database import get_db
from app.services.comparison_service import ComparisonService, ComparisonType
from app.services.export_service import ExportService, ExportFormat
from app.services.batch_service import BatchService
from app.services.file_service import FileService
from app.schemas.advanced import (
    ComparisonRequest,
    ComparisonResponse,
    ExportRequest,
    ExportResponse,
    BatchRequest,
    BatchResponse,
    BatchStatusResponse,
    NoteAnalysisResponse
)
from app.core.exceptions import (
    TranscriptionNotFoundError,
    FileNotFoundError,
    ComparisonError,
    ExportError,
    BatchProcessingError
)

router = APIRouter()


@router.post("/compare", response_model=ComparisonResponse)
async def compare_midi_files(
    request: ComparisonRequest,
    db=Depends(get_db)
):
    """
    Compare a generated MIDI file with a reference MIDI file.

    Args:
        request: Comparison request with transcription ID and reference file
        db: Database session

    Returns:
        Detailed comparison results
    """
    try:
        # Get transcription files
        transcription_files = FileService.get_transcription_files(
            request.transcription_id)
        if not transcription_files or not transcription_files.get('midi_path'):
            raise TranscriptionNotFoundError(
                f"Transcription {request.transcription_id} not found")

        # Validate reference file exists
        if not os.path.exists(request.reference_midi_path):
            raise FileNotFoundError(
                f"Reference MIDI file not found: {request.reference_midi_path}")

        # Perform comparison
        comparison_result = ComparisonService.compare_midi_files(
            transcription_files['midi_path'],
            request.reference_midi_path,
            request.comparison_types
        )

        # Generate detailed report
        report = ComparisonService.generate_comparison_report(
            comparison_result,
            transcription_files['midi_path'],
            request.reference_midi_path
        )

        return ComparisonResponse(
            transcription_id=request.transcription_id,
            reference_file=request.reference_midi_path,
            overall_score=comparison_result.overall_score,
            note_accuracy=comparison_result.note_accuracy,
            timing_accuracy=comparison_result.timing_accuracy,
            rhythm_accuracy=comparison_result.rhythm_accuracy,
            velocity_accuracy=comparison_result.velocity_accuracy,
            detailed_report=report
        )

    except (TranscriptionNotFoundError, FileNotFoundError, ComparisonError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/compare/upload", response_model=ComparisonResponse)
async def compare_with_uploaded_midi(
    transcription_id: str = Form(...),
    reference_midi: UploadFile = File(...),
    comparison_types: Optional[List[str]] = Form(None),
    db=Depends(get_db)
):
    """
    Compare a generated MIDI file with an uploaded reference MIDI file.

    Args:
        transcription_id: Transcription ID
        reference_midi: Uploaded reference MIDI file
        comparison_types: Types of comparison to perform
        db: Database session

    Returns:
        Comparison results
    """
    try:
        # Validate file type
        if not reference_midi.filename.lower().endswith('.mid'):
            raise HTTPException(
                status_code=400, detail="Reference file must be a MIDI file")

        # Save uploaded file temporarily
        temp_path = f"temp/reference_{transcription_id}_{reference_midi.filename}"
        os.makedirs("temp", exist_ok=True)

        with open(temp_path, "wb") as f:
            content = await reference_midi.read()
            f.write(content)

        # Convert comparison types
        comparison_types_enum = []
        if comparison_types:
            for comp_type in comparison_types:
                try:
                    comparison_types_enum.append(ComparisonType(comp_type))
                except ValueError:
                    pass

        # Perform comparison
        request = ComparisonRequest(
            transcription_id=transcription_id,
            reference_midi_path=temp_path,
            comparison_types=comparison_types_enum or list(ComparisonType)
        )

        result = await compare_midi_files(request, db)

        # Clean up temporary file
        try:
            os.remove(temp_path)
        except:
            pass

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@router.post("/export", response_model=ExportResponse)
async def export_transcription(
    request: ExportRequest,
    db=Depends(get_db)
):
    """
    Export transcription in specified format.

    Args:
        request: Export request with transcription ID and format
        db: Database session

    Returns:
        Export result with file download information
    """
    try:
        # Get transcription files
        transcription_files = FileService.get_transcription_files(
            request.transcription_id)
        if not transcription_files or not transcription_files.get('midi_path'):
            raise TranscriptionNotFoundError(
                f"Transcription {request.transcription_id} not found")

        # Validate export format
        try:
            export_format = ExportFormat(request.format)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Unsupported export format: {request.format}")

        # Generate output path
        base_name = f"export_{request.transcription_id}"
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)

        if export_format == ExportFormat.JSON:
            output_path = os.path.join(export_dir, f"{base_name}.json")
        elif export_format == ExportFormat.XML:
            output_path = os.path.join(export_dir, f"{base_name}.xml")
        elif export_format == ExportFormat.CSV:
            output_path = os.path.join(export_dir, f"{base_name}.csv")
        else:
            output_path = os.path.join(export_dir, f"{base_name}.mid")

        # Export file
        export_result = ExportService.export_midi(
            transcription_files['midi_path'],
            output_path,
            export_format,
            request.metadata
        )

        return ExportResponse(
            transcription_id=request.transcription_id,
            export_format=request.format,
            output_path=output_path,
            file_size=export_result['file_size'],
            download_url=f"/api/v1/advanced/download/{request.transcription_id}?format={request.format}"
        )

    except (TranscriptionNotFoundError, ExportError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/download/{transcription_id}")
async def download_export(
    transcription_id: str,
    format: str = "midi_1",
    db=Depends(get_db)
):
    """
    Download exported transcription file.

    Args:
        transcription_id: Transcription ID
        format: Export format
        db: Database session

    Returns:
        File download response
    """
    try:
        # Generate file path
        base_name = f"export_{transcription_id}"
        export_dir = "exports"

        if format == "json":
            file_path = os.path.join(export_dir, f"{base_name}.json")
        elif format == "xml":
            file_path = os.path.join(export_dir, f"{base_name}.xml")
        elif format == "csv":
            file_path = os.path.join(export_dir, f"{base_name}.csv")
        else:
            file_path = os.path.join(export_dir, f"{base_name}.mid")

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Export file not found")

        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type="application/octet-stream"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/batch", response_model=BatchResponse)
async def create_batch_job(
    request: BatchRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """
    Create and start a batch processing job.

    Args:
        request: Batch processing request
        background_tasks: Background tasks
        db: Database session

    Returns:
        Batch job information
    """
    try:
        # Create batch job
        batch_job = BatchService.create_batch_job(
            request.audio_files,
            request.options
        )

        # Start batch processing in background
        background_tasks.add_task(
            BatchService.process_batch,
            batch_job.batch_id,
            request.audio_files,
            request.options
        )

        return BatchResponse(
            batch_id=batch_job.batch_id,
            status=batch_job.status.value,
            total_files=batch_job.total_files,
            created_at=batch_job.created_at.isoformat(),
            status_url=f"/api/v1/advanced/batch/{batch_job.batch_id}/status"
        )

    except BatchProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch creation failed: {str(e)}")


@router.get("/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(
    batch_id: str,
    db=Depends(get_db)
):
    """
    Get batch processing status.

    Args:
        batch_id: Batch job ID
        db: Database session

    Returns:
        Batch status information
    """
    try:
        batch_job = BatchService.get_batch_status(batch_id)
        if not batch_job:
            raise HTTPException(
                status_code=404, detail=f"Batch job {batch_id} not found")

        return BatchStatusResponse(
            batch_id=batch_job.batch_id,
            status=batch_job.status.value,
            total_files=batch_job.total_files,
            completed_files=batch_job.completed_files,
            failed_files=batch_job.failed_files,
            created_at=batch_job.created_at.isoformat(),
            updated_at=batch_job.updated_at.isoformat(),
            completed_at=batch_job.completed_at.isoformat() if batch_job.completed_at else None,
            error_message=batch_job.error_message,
            results=batch_job.results or []
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get batch status: {str(e)}")


@router.post("/batch/{batch_id}/compare")
async def compare_batch_results(
    batch_id: str,
    reference_files: List[Dict[str, str]],
    db=Depends(get_db)
):
    """
    Compare batch results with reference files.

    Args:
        batch_id: Batch job ID
        reference_files: List of reference file mappings
        db: Database session

    Returns:
        Batch comparison results
    """
    try:
        comparison_results = BatchService.batch_compare(batch_id, reference_files)
        return comparison_results

    except BatchProcessingError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Batch comparison failed: {str(e)}")


@router.post("/batch/{batch_id}/export")
async def export_batch_results(
    batch_id: str,
    format: str = "midi_1",
    include_metadata: bool = True,
    db=Depends(get_db)
):
    """
    Export batch results in specified format.

    Args:
        batch_id: Batch job ID
        format: Export format
        include_metadata: Whether to include metadata
        db: Database session

    Returns:
        Batch export results
    """
    try:
        # Validate export format
        try:
            export_format = ExportFormat(format)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Unsupported export format: {format}")

        export_results = BatchService.batch_export(
            batch_id, export_format, include_metadata)
        return export_results

    except BatchProcessingError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch export failed: {str(e)}")


@router.delete("/batch/{batch_id}")
async def cleanup_batch(
    batch_id: str,
    days_old: int = 7,
    db=Depends(get_db)
):
    """
    Clean up batch processing files.

    Args:
        batch_id: Batch job ID
        days_old: Age threshold in days
        db: Database session

    Returns:
        Cleanup result
    """
    try:
        cleanup_result = BatchService.cleanup_batch(batch_id, days_old)
        return cleanup_result

    except BatchProcessingError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch cleanup failed: {str(e)}")


@router.get("/analysis/{transcription_id}", response_model=NoteAnalysisResponse)
async def analyze_transcription(
    transcription_id: str,
    db=Depends(get_db)
):
    """
    Analyze note distribution in a transcription.

    Args:
        transcription_id: Transcription ID
        db: Database session

    Returns:
        Note analysis results
    """
    try:
        # Get transcription files
        transcription_files = FileService.get_transcription_files(transcription_id)
        if not transcription_files or not transcription_files.get('midi_path'):
            raise TranscriptionNotFoundError(
                f"Transcription {transcription_id} not found")

        # Perform analysis
        analysis = ComparisonService.analyze_note_distribution(
            transcription_files['midi_path'])

        return NoteAnalysisResponse(
            transcription_id=transcription_id,
            analysis=analysis
        )

    except TranscriptionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/formats")
async def get_supported_formats():
    """
    Get list of supported export formats.

    Returns:
        List of supported formats
    """
    return {
        "export_formats": ExportService.get_supported_formats(),
        "comparison_types": [comp_type.value for comp_type in ComparisonType]
    }
