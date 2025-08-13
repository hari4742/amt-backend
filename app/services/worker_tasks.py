"""
Separate worker tasks for different processing stages.
"""

import os
import time
from datetime import datetime
from celery import current_task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.transcription import Transcription, TranscriptionStatus
from app.services.audio_service import AudioService
from app.services.midi_service import MIDIService
from app.services.progress_service import ProgressService, update_transcription_step
from app.core.exceptions import (
    AudioProcessingError,
    MIDIGenerationError,
    TranscriptionProcessingError
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def audio_processing_worker(self, transcription_id: str):
    """
    Dedicated worker for audio processing tasks.

    Args:
        transcription_id: Unique identifier for the transcription
    """
    db = SessionLocal()
    start_time = datetime.utcnow()

    try:
        # Get transcription record
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        if not transcription:
            raise TranscriptionProcessingError(
                f"Transcription {transcription_id} not found")

        # Update status to processing
        transcription.status = TranscriptionStatus.PROCESSING
        transcription.updated_at = datetime.utcnow()
        db.commit()

        # Step 1: Load audio file
        update_transcription_step(
            transcription_id, "audio_loading", 0, "Loading audio file")

        if not os.path.exists(transcription.audio_path):
            raise AudioProcessingError(
                f"Audio file not found: {transcription.audio_path}")

        audio_data, sample_rate = AudioService.load_audio(transcription.audio_path)
        update_transcription_step(transcription_id, "audio_loading",
                                  100, "Audio loaded successfully")

        # Step 2: Validate audio quality
        update_transcription_step(
            transcription_id, "audio_validation", 0, "Validating audio quality")

        audio_analysis = AudioService.analyze_audio(audio_data, sample_rate)
        is_valid, error_message = AudioService.validate_audio_quality(
            audio_data, sample_rate)

        if not is_valid:
            raise AudioProcessingError(
                f"Audio quality validation failed: {error_message}")

        update_transcription_step(
            transcription_id, "audio_validation", 100, "Audio validation passed")

        # Step 3: Preprocess audio
        update_transcription_step(
            transcription_id, "audio_processing", 0, "Preprocessing audio")

        processed_audio = AudioService.preprocess_audio(audio_data, sample_rate)
        update_transcription_step(
            transcription_id, "audio_processing", 100, "Audio preprocessing completed")

        # Update transcription with audio analysis
        transcription.duration = audio_analysis['duration']
        db.commit()

        # Store processed audio path for MIDI generation
        processed_audio_path = transcription.audio_path.replace('.', '_processed.')
        AudioService.save_processed_audio(
            processed_audio, processed_audio_path, sample_rate)

        # Update transcription with processed audio path
        transcription.audio_path = processed_audio_path
        db.commit()

        return {
            "status": "audio_processing_completed",
            "transcription_id": transcription_id,
            "duration": audio_analysis['duration'],
            "sample_rate": sample_rate,
            "processed_audio_path": processed_audio_path
        }

    except Exception as e:
        # Update status to failed
        if transcription:
            transcription.status = TranscriptionStatus.FAILED
            transcription.error_message = f"Audio processing failed: {str(e)}"
            transcription.updated_at = datetime.utcnow()
            db.commit()

        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        else:
            raise e

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def midi_generation_worker(self, transcription_id: str, audio_path: str, sample_rate: int):
    """
    Dedicated worker for MIDI generation tasks.

    Args:
        transcription_id: Unique identifier for the transcription
        audio_path: Path to the processed audio file
        sample_rate: Sample rate of the audio
    """
    db = SessionLocal()
    start_time = datetime.utcnow()

    try:
        # Get transcription record
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()

        if not transcription:
            raise TranscriptionProcessingError(
                f"Transcription {transcription_id} not found")

        # Step 1: Load processed audio
        update_transcription_step(
            transcription_id, "midi_generation", 0, "Loading processed audio")

        audio_data, _ = AudioService.load_audio(audio_path)
        update_transcription_step(
            transcription_id, "midi_generation", 20, "Audio loaded for MIDI generation")

        # Step 2: Generate MIDI
        update_transcription_step(
            transcription_id, "midi_generation", 40, "Generating MIDI from audio")

        midi_results = MIDIService.generate_midi_from_audio(
            audio_data,
            sample_rate,
            transcription.midi_path,
            quality=transcription.quality
        )

        update_transcription_step(
            transcription_id, "midi_generation", 80, "MIDI generation completed")

        # Step 3: Validate MIDI
        update_transcription_step(
            transcription_id, "midi_validation", 0, "Validating generated MIDI")

        is_midi_valid, midi_error = MIDIService.validate_midi_file(
            transcription.midi_path)
        if not is_midi_valid:
            raise MIDIGenerationError(f"MIDI validation failed: {midi_error}")

        update_transcription_step(
            transcription_id, "midi_validation", 100, "MIDI validation passed")

        # Step 4: Complete transcription
        update_transcription_step(transcription_id, "completion",
                                  0, "Finalizing transcription")

        processing_time = (datetime.utcnow() - start_time).total_seconds()

        transcription.status = TranscriptionStatus.COMPLETED
        transcription.completed_at = datetime.utcnow()
        transcription.processing_time = processing_time
        transcription.confidence_score = midi_results['confidence_score']
        transcription.updated_at = datetime.utcnow()
        db.commit()

        update_transcription_step(transcription_id, "completion",
                                  100, "Transcription completed successfully")

        return {
            "status": "midi_generation_completed",
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
            transcription.error_message = f"MIDI generation failed: {str(e)}"
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
def file_cleanup_worker(self, days_old: int = 7):
    """
    Dedicated worker for file cleanup tasks.

    Args:
        days_old: Number of days to keep files
    """
    try:
        from app.services.file_service import FileService

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
def audio_validation_worker(self, file_path: str):
    """
    Dedicated worker for audio validation tasks.

    Args:
        file_path: Path to the audio file to validate
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


@celery_app.task(bind=True)
def progress_cleanup_worker(self):
    """
    Worker for cleaning up old progress data.
    """
    try:
        deleted_count = ProgressService.cleanup_old_progress_data(hours_old=24)

        return {
            "status": "progress_cleanup_completed",
            "deleted_progress_entries": deleted_count,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        # Log error but don't retry for cleanup tasks
        raise e
