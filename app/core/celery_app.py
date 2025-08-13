"""
Celery configuration for async task processing.
"""

import platform
from celery import Celery
from app.config import settings

# Create Celery instance
celery_app = Celery(
    "amt_backend",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.services.transcription_tasks",
        "app.services.worker_tasks"
    ]
)

# Windows-specific configuration
if platform.system() == "Windows":
    # Use threads pool on Windows to avoid permission issues
    celery_app.conf.update(
        broker_connection_retry_on_startup=True,
        worker_pool_restarts=True,
        worker_pool="threads",
        worker_concurrency=4,
    )

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    # Remove soft time limit on Windows to avoid SIGUSR1 issues
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject task if worker dies
    task_always_eager=False,  # Run tasks asynchronously
    worker_send_task_events=True,  # Send task events
    task_send_sent_event=True,  # Send task sent events
    task_ignore_result=False,  # Store task results
    task_store_errors_even_if_ignored=True,  # Store errors
    task_compression="gzip",  # Compress task data
    result_compression="gzip",  # Compress results
    result_expires=3600,  # Results expire in 1 hour
    result_backend_transport_options={
        "retry_policy": {
            "timeout": 5.0,
            "max_retries": 3,
        }
    },
    broker_transport_options={
        "retry_policy": {
            "timeout": 5.0,
            "max_retries": 3,
        }
    }
)

# Add soft time limit only on non-Windows platforms
if platform.system() != "Windows":
    celery_app.conf.task_soft_time_limit = 25 * 60  # 25 minutes

# Task routing with priority queues
celery_app.conf.task_routes = {
    "app.services.transcription_tasks.process_transcription": {"queue": "transcription_high"},
    "app.services.transcription_tasks.generate_midi": {"queue": "midi_generation"},
    "app.services.transcription_tasks.cleanup_old_files": {"queue": "maintenance"},
    "app.services.transcription_tasks.validate_audio_file": {"queue": "validation"},
    "app.services.transcription_tasks.*": {"queue": "transcription_default"},
}

# Task priority settings
celery_app.conf.task_queue_max_priority = {
    "transcription_high": 10,
    "transcription_default": 5,
    "midi_generation": 7,
    "maintenance": 1,
    "validation": 3,
}
