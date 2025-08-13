"""
Progress tracking service for monitoring task progress and status updates.
"""

import time
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from celery import current_task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.transcription import Transcription, TranscriptionStatus


class ProgressService:
    """Service for tracking task progress and status updates."""

    @staticmethod
    def update_progress(task_id: str, progress: float, status: str, message: str = ""):
        """
        Update task progress in Redis.

        Args:
            task_id: Celery task ID
            progress: Progress percentage (0-100)
            status: Current status
            message: Optional status message
        """
        progress_data = {
            "progress": min(100.0, max(0.0, progress)),
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id
        }

        # Store in Redis with expiration (1 hour)
        celery_app.backend.set(
            f"progress:{task_id}",
            json.dumps(progress_data),
            ex=3600
        )

    @staticmethod
    def get_progress(task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task progress from Redis.

        Args:
            task_id: Celery task ID

        Returns:
            Progress data or None if not found
        """
        try:
            progress_data = celery_app.backend.get(f"progress:{task_id}")
            if progress_data:
                return json.loads(progress_data)
        except Exception:
            pass
        return None

    @staticmethod
    def update_transcription_progress(
        transcription_id: str,
        progress: float,
        status: str,
        message: str = ""
    ):
        """
        Update transcription progress in database.

        Args:
            transcription_id: Transcription ID
            progress: Progress percentage (0-100)
            status: Current status
            message: Optional status message
        """
        db = SessionLocal()
        try:
            transcription = db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()

            if transcription:
                transcription.status = status
                transcription.updated_at = datetime.utcnow()

                # Store progress in a JSON field or separate table
                # For now, we'll use the error_message field for progress info
                if message:
                    transcription.error_message = f"Progress: {progress:.1f}% - {message}"

                db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    @staticmethod
    def estimate_completion_time(
        transcription_id: str,
        current_progress: float,
        start_time: datetime
    ) -> Optional[datetime]:
        """
        Estimate completion time based on current progress.

        Args:
            transcription_id: Transcription ID
            current_progress: Current progress percentage
            start_time: Task start time

        Returns:
            Estimated completion time or None if cannot estimate
        """
        if current_progress <= 0:
            return None

        elapsed_time = datetime.utcnow() - start_time
        estimated_total_time = elapsed_time * (100 / current_progress)
        estimated_completion = start_time + estimated_total_time

        return estimated_completion

    @staticmethod
    def cleanup_old_progress_data(hours_old: int = 24):
        """
        Clean up old progress data from Redis.

        Args:
            hours_old: Age threshold in hours
        """
        try:
            # Get all progress keys
            pattern = "progress:*"
            keys = celery_app.backend.client.keys(pattern)

            cutoff_time = time.time() - (hours_old * 3600)
            deleted_count = 0

            for key in keys:
                try:
                    # Check if key is old enough to delete
                    if celery_app.backend.client.ttl(key) > 0:
                        # Key has TTL, let it expire naturally
                        continue

                    # For keys without TTL, check creation time
                    # This is a simplified approach - in production, you might want
                    # to store creation timestamps in the progress data
                    deleted_count += 1
                    celery_app.backend.client.delete(key)

                except Exception:
                    continue

            return deleted_count

        except Exception:
            return 0


# Celery task progress tracking decorator
def track_progress(progress_steps: Dict[str, float]):
    """
    Decorator to track progress in Celery tasks.

    Args:
        progress_steps: Dictionary mapping step names to progress percentages
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            task_id = current_task.request.id if current_task else None

            if task_id:
                ProgressService.update_progress(
                    task_id, 0.0, "started", "Task started"
                )

            try:
                result = func(*args, **kwargs)

                if task_id:
                    ProgressService.update_progress(
                        task_id, 100.0, "completed", "Task completed successfully"
                    )

                return result

            except Exception as e:
                if task_id:
                    ProgressService.update_progress(
                        task_id, 0.0, "failed", f"Task failed: {str(e)}"
                    )
                raise e

        return wrapper
    return decorator


# Progress tracking for specific transcription steps
def update_transcription_step(
    transcription_id: str,
    step: str,
    progress: float,
    message: str = ""
):
    """
    Update progress for a specific transcription step.

    Args:
        transcription_id: Transcription ID
        step: Step name (e.g., "audio_loading", "processing", "midi_generation")
        progress: Progress percentage for this step
        message: Optional message
    """
    step_progress = {
        "audio_loading": (0, 10),
        "audio_validation": (10, 20),
        "audio_processing": (20, 40),
        "midi_generation": (40, 80),
        "midi_validation": (80, 90),
        "completion": (90, 100)
    }

    if step in step_progress:
        start_progress, end_progress = step_progress[step]
        overall_progress = start_progress + \
            (progress / 100) * (end_progress - start_progress)

        ProgressService.update_transcription_progress(
            transcription_id,
            overall_progress,
            "processing",
            f"{step}: {message}"
        )
