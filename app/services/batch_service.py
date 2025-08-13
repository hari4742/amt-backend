"""
Batch processing service for handling multiple transcription requests and operations.
"""

import os
import json
import zipfile
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from celery import group
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.transcription import Transcription, TranscriptionStatus
from app.services.transcription_tasks import process_transcription
from app.services.export_service import ExportService, ExportFormat
from app.services.comparison_service import ComparisonService
from app.services.file_service import FileService
from app.core.exceptions import BatchProcessingError


class BatchStatus(Enum):
    """Batch processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class BatchJob:
    """Represents a batch processing job."""
    batch_id: str
    status: BatchStatus
    total_files: int
    completed_files: int
    failed_files: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results: List[Dict[str, Any]] = None


class BatchService:
    """Service for batch processing operations."""

    @staticmethod
    def create_batch_job(
        audio_files: List[Dict[str, Any]],
        options: Dict[str, Any] = None
    ) -> BatchJob:
        """
        Create a new batch processing job.

        Args:
            audio_files: List of audio file information
            options: Processing options

        Returns:
            Batch job information
        """
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(audio_files)}"

        batch_job = BatchJob(
            batch_id=batch_id,
            status=BatchStatus.PENDING,
            total_files=len(audio_files),
            completed_files=0,
            failed_files=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            results=[]
        )

        # Store batch job information (in practice, this would be in a database)
        BatchService._store_batch_job(batch_job)

        return batch_job

    @staticmethod
    def process_batch(
        batch_id: str,
        audio_files: List[Dict[str, Any]],
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a batch of audio files.

        Args:
            batch_id: Batch job ID
            audio_files: List of audio file information
            options: Processing options

        Returns:
            Batch processing result
        """
        try:
            # Update batch status
            BatchService._update_batch_status(batch_id, BatchStatus.PROCESSING)

            # Process each file
            results = []
            completed_count = 0
            failed_count = 0

            for file_info in audio_files:
                try:
                    # Create transcription record
                    transcription_id = BatchService._create_transcription_record(
                        file_info, options
                    )

                    # Start transcription task
                    task = process_transcription.delay(transcription_id)

                    results.append({
                        "file_info": file_info,
                        "transcription_id": transcription_id,
                        "task_id": task.id,
                        "status": "started"
                    })

                    completed_count += 1

                except Exception as e:
                    failed_count += 1
                    results.append({
                        "file_info": file_info,
                        "error": str(e),
                        "status": "failed"
                    })

            # Update batch results
            BatchService._update_batch_results(
                batch_id, completed_count, failed_count, results
            )

            # Determine final status
            if failed_count == 0:
                final_status = BatchStatus.COMPLETED
            elif completed_count == 0:
                final_status = BatchStatus.FAILED
            else:
                final_status = BatchStatus.PARTIAL

            BatchService._update_batch_status(batch_id, final_status)

            return {
                "batch_id": batch_id,
                "status": final_status.value,
                "total_files": len(audio_files),
                "completed_files": completed_count,
                "failed_files": failed_count,
                "results": results
            }

        except Exception as e:
            BatchService._update_batch_status(batch_id, BatchStatus.FAILED, str(e))
            raise BatchProcessingError(f"Batch processing failed: {str(e)}")

    @staticmethod
    def get_batch_status(batch_id: str) -> Optional[BatchJob]:
        """
        Get batch job status.

        Args:
            batch_id: Batch job ID

        Returns:
            Batch job information or None
        """
        return BatchService._get_batch_job(batch_id)

    @staticmethod
    def batch_compare(
        batch_id: str,
        reference_files: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Compare batch results with reference files.

        Args:
            batch_id: Batch job ID
            reference_files: List of reference file mappings

        Returns:
            Comparison results
        """
        batch_job = BatchService._get_batch_job(batch_id)
        if not batch_job:
            raise BatchProcessingError(f"Batch job {batch_id} not found")

        comparison_results = []

        for result in batch_job.results:
            if result.get('status') == 'completed':
                transcription_id = result.get('transcription_id')

                # Find corresponding reference file
                reference_file = None
                for ref_file in reference_files:
                    if ref_file.get('original_filename') == result['file_info'].get('filename'):
                        reference_file = ref_file
                        break

                if reference_file and transcription_id:
                    try:
                        # Get transcription files
                        transcription_files = FileService.get_transcription_files(
                            transcription_id)

                        if transcription_files and transcription_files.get('midi_path'):
                            # Perform comparison
                            comparison = ComparisonService.compare_midi_files(
                                transcription_files['midi_path'],
                                reference_file['reference_path']
                            )

                            comparison_results.append({
                                "transcription_id": transcription_id,
                                "original_filename": result['file_info'].get('filename'),
                                "comparison": comparison
                            })

                    except Exception as e:
                        comparison_results.append({
                            "transcription_id": transcription_id,
                            "original_filename": result['file_info'].get('filename'),
                            "error": str(e)
                        })

        return {
            "batch_id": batch_id,
            "total_comparisons": len(comparison_results),
            "comparison_results": comparison_results
        }

    @staticmethod
    def batch_export(
        batch_id: str,
        export_format: ExportFormat,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Export batch results in specified format.

        Args:
            batch_id: Batch job ID
            export_format: Export format
            include_metadata: Whether to include metadata

        Returns:
            Export result
        """
        batch_job = BatchService._get_batch_job(batch_id)
        if not batch_job:
            raise BatchProcessingError(f"Batch job {batch_id} not found")

        # Create export directory
        export_dir = f"exports/batch_{batch_id}"
        os.makedirs(export_dir, exist_ok=True)

        export_files = []
        metadata_files = []

        for result in batch_job.results:
            if result.get('status') == 'completed':
                transcription_id = result.get('transcription_id')

                try:
                    # Get transcription files
                    transcription_files = FileService.get_transcription_files(
                        transcription_id)

                    if transcription_files and transcription_files.get('midi_path'):
                        # Export MIDI file
                        filename = result['file_info'].get('filename', 'unknown')
                        base_name = os.path.splitext(filename)[0]

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
                            export_format
                        )

                        export_files.append({
                            "original_filename": filename,
                            "export_path": output_path,
                            "export_result": export_result
                        })

                        # Export metadata if requested
                        if include_metadata:
                            metadata_path = os.path.join(
                                export_dir, f"{base_name}_metadata.json")

                            # Get transcription data
                            db = SessionLocal()
                            try:
                                transcription = db.query(Transcription).filter(
                                    Transcription.id == transcription_id
                                ).first()

                                if transcription:
                                    transcription_data = {
                                        "id": transcription.id,
                                        "original_filename": transcription.original_filename,
                                        "file_size": transcription.file_size,
                                        "duration": transcription.duration,
                                        "quality": transcription.quality,
                                        "confidence_score": transcription.confidence_score,
                                        "processing_time": transcription.processing_time,
                                        "created_at": transcription.created_at.isoformat(),
                                        "completed_at": transcription.completed_at.isoformat() if transcription.completed_at else None
                                    }

                                    metadata_result = ExportService.export_transcription_metadata(
                                        transcription_id,
                                        transcription_data,
                                        metadata_path,
                                        ExportFormat.JSON
                                    )

                                    metadata_files.append({
                                        "original_filename": filename,
                                        "metadata_path": metadata_path,
                                        "metadata_result": metadata_result
                                    })

                            finally:
                                db.close()

                except Exception as e:
                    export_files.append({
                        "original_filename": result['file_info'].get('filename', 'unknown'),
                        "error": str(e)
                    })

        # Create zip file if multiple files
        zip_path = None
        if len(export_files) > 1:
            zip_path = os.path.join(export_dir, f"batch_{batch_id}_export.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for export_file in export_files:
                    if 'export_path' in export_file:
                        zipf.write(export_file['export_path'], os.path.basename(
                            export_file['export_path']))

                for metadata_file in metadata_files:
                    if 'metadata_path' in metadata_file:
                        zipf.write(metadata_file['metadata_path'], os.path.basename(
                            metadata_file['metadata_path']))

        return {
            "batch_id": batch_id,
            "export_format": export_format.value,
            "export_directory": export_dir,
            "total_files": len(export_files),
            "export_files": export_files,
            "metadata_files": metadata_files,
            "zip_file": zip_path
        }

    @staticmethod
    def cleanup_batch(batch_id: str, days_old: int = 7) -> Dict[str, Any]:
        """
        Clean up old batch files.

        Args:
            batch_id: Batch job ID
            days_old: Age threshold in days

        Returns:
            Cleanup result
        """
        try:
            # Get batch job
            batch_job = BatchService._get_batch_job(batch_id)
            if not batch_job:
                raise BatchProcessingError(f"Batch job {batch_id} not found")

            # Clean up transcription files
            deleted_count = 0
            for result in batch_job.results:
                if result.get('transcription_id'):
                    try:
                        FileService.delete_transcription_files(
                            result['transcription_id'])
                        deleted_count += 1
                    except Exception:
                        pass

            # Remove batch job record
            BatchService._delete_batch_job(batch_id)

            return {
                "batch_id": batch_id,
                "deleted_transcriptions": deleted_count,
                "status": "cleaned"
            }

        except Exception as e:
            raise BatchProcessingError(f"Batch cleanup failed: {str(e)}")

    # Private helper methods (in practice, these would interact with a database)

    @staticmethod
    def _store_batch_job(batch_job: BatchJob):
        """Store batch job information."""
        # In practice, this would save to a database
        pass

    @staticmethod
    def _get_batch_job(batch_id: str) -> Optional[BatchJob]:
        """Get batch job information."""
        # In practice, this would retrieve from a database
        return None

    @staticmethod
    def _update_batch_status(batch_id: str, status: BatchStatus, error_message: str = None):
        """Update batch job status."""
        # In practice, this would update a database
        pass

    @staticmethod
    def _update_batch_results(batch_id: str, completed: int, failed: int, results: List[Dict[str, Any]]):
        """Update batch job results."""
        # In practice, this would update a database
        pass

    @staticmethod
    def _delete_batch_job(batch_id: str):
        """Delete batch job record."""
        # In practice, this would delete from a database
        pass

    @staticmethod
    def _create_transcription_record(file_info: Dict[str, Any], options: Dict[str, Any] = None) -> str:
        """Create a transcription record in the database."""
        db = SessionLocal()
        try:
            # Save audio file
            audio_path = file_info['file_path']
            transcription_id = FileService.save_audio_file(
                audio_path,
                file_info.get('filename', os.path.basename(audio_path)),
                options or {}
            )

            return transcription_id

        finally:
            db.close()
