"""
Celery tasks for transcription processing.
"""

import os
import uuid
from datetime import datetime
from celery import current_task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.transcription import Transcription, TranscriptionStatus
from app.services.file_service import FileService
from app.services.audio_service import AudioService
from app.services.midi_service import MIDIService
from app.services.worker_tasks import audio_processing_worker, midi_generation_worker
from app.services.progress_service import ProgressService, update_transcription_step


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def process_transcription(self, transcription_id: str):
    """
    Process audio transcription asynchronously.

    Args:
        transcription_id: Unique identifier for the transcription
    """
    db = SessionLocal()
    start_time = datetime.utcnow()

    try:
        # Update status to processing
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id).first()
        if not transcription:
            raise ValueError(f"Transcription {transcription_id} not found")

        transcription.status = TranscriptionStatus.PROCESSING
        transcription.updated_at = datetime.utcnow()
        db.commit()

        # 1. Load and validate audio file
        if not os.path.exists(transcription.audio_path):
            raise ValueError(f"Audio file not found: {transcription.audio_path}")

        audio_data, sample_rate = AudioService.load_audio(transcription.audio_path)

        # 2. Analyze and validate audio quality
        audio_analysis = AudioService.analyze_audio(audio_data, sample_rate)
        is_valid, error_message = AudioService.validate_audio_quality(
            audio_data, sample_rate)

        if not is_valid:
            raise ValueError(f"Audio quality validation failed: {error_message}")

        # Update transcription with audio analysis
        transcription.duration = audio_analysis['duration']
        db.commit()

        # 3. Preprocess audio
        processed_audio = AudioService.preprocess_audio(audio_data, sample_rate)

        # 4. Generate MIDI from audio
        midi_results = MIDIService.generate_midi_from_audio(
            processed_audio,
            sample_rate,
            transcription.midi_path,
            quality=transcription.quality
        )

        # 5. Validate generated MIDI
        is_midi_valid, midi_error = MIDIService.validate_midi_file(
            transcription.midi_path)
        if not is_midi_valid:
            raise ValueError(f"MIDI validation failed: {midi_error}")

        # 6. Calculate processing time and update results
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        transcription.status = TranscriptionStatus.COMPLETED
        transcription.completed_at = datetime.utcnow()
        transcription.processing_time = processing_time
        transcription.confidence_score = midi_results['confidence_score']
        transcription.updated_at = datetime.utcnow()

        db.commit()

        return {
            "status": "completed",
            "transcription_id": transcription_id,
            "processing_time": processing_time,
            "confidence_score": midi_results['confidence_score'],
            "total_notes": midi_results['total_notes'],
            "tempo": midi_results['tempo']
        }

    except Exception as e:
        # Update status to failed
        if transcription:
            transcription.status = TranscriptionStatus.FAILED
            transcription.error_message = str(e)
            transcription.updated_at = datetime.utcnow()
            db.commit()

        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        else:
            raise e

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=300)
def cleanup_old_files(self, days_old: int = 7):
    """
    Clean up old transcription files.

    Args:
        days_old: Number of days to keep files
    """
    try:
        deleted_count = FileService.cleanup_old_files(days_old)

        return {
            "status": "cleanup_completed",
            "deleted_files": deleted_count,
            "days_old": days_old,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        # Retry once after 5 minutes
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)
        else:
            raise e


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def validate_audio_file(self, file_path: str):
    """
    Validate audio file format and quality.

    Args:
        file_path: Path to the audio file
    """
    try:
        # Load and validate audio
        audio_data, sample_rate = AudioService.load_audio(file_path)
        audio_analysis = AudioService.analyze_audio(audio_data, sample_rate)
        is_valid, error_message = AudioService.validate_audio_quality(
            audio_data, sample_rate)

        return {
            "status": "validation_completed",
            "file_path": file_path,
            "is_valid": is_valid,
            "error_message": error_message if not is_valid else None,
            "analysis": audio_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10 * (2 ** self.request.retries))
        else:
            raise e
