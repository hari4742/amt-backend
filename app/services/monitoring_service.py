"""
Monitoring service for tracking task performance, health, and metrics.
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from celery import current_task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.transcription import Transcription, TranscriptionStatus


class MonitoringService:
    """Service for monitoring task performance and system health."""

    @staticmethod
    def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed status of a Celery task.

        Args:
            task_id: Celery task ID

        Returns:
            Task status information or None if not found
        """
        try:
            result = celery_app.AsyncResult(task_id)

            status_info = {
                "task_id": task_id,
                "status": result.status,
                "successful": result.successful(),
                "failed": result.failed(),
                "ready": result.ready(),
                "info": result.info if result.ready() else None,
                "traceback": result.traceback if result.failed() else None,
                "date_done": result.date_done.isoformat() if result.date_done else None
            }

            return status_info

        except Exception:
            return None

    @staticmethod
    def get_queue_stats() -> Dict[str, Any]:
        """
        Get statistics about Celery queues.

        Returns:
            Queue statistics
        """
        try:
            # Get queue information from Redis
            redis_client = celery_app.broker_connection().default_channel.client

            queue_stats = {}
            queues = [
                "transcription_high",
                "transcription_default",
                "midi_generation",
                "maintenance",
                "validation"
            ]

            for queue in queues:
                try:
                    # Get queue length
                    queue_length = redis_client.llen(f"celery:{queue}")
                    queue_stats[queue] = {
                        "length": queue_length,
                        "name": queue
                    }
                except Exception:
                    queue_stats[queue] = {
                        "length": 0,
                        "name": queue,
                        "error": "Could not retrieve queue info"
                    }

            return {
                "queues": queue_stats,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "error": f"Failed to get queue stats: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def get_worker_stats() -> Dict[str, Any]:
        """
        Get statistics about Celery workers.

        Returns:
            Worker statistics
        """
        try:
            # Get active workers
            active_workers = celery_app.control.inspect().active()
            registered_workers = celery_app.control.inspect().registered()
            stats_workers = celery_app.control.inspect().stats()

            worker_stats = {}

            if active_workers:
                for worker_name, tasks in active_workers.items():
                    worker_stats[worker_name] = {
                        "active_tasks": len(tasks),
                        "registered": registered_workers.get(worker_name, []) if registered_workers else [],
                        "stats": stats_workers.get(worker_name, {}) if stats_workers else {}
                    }

            return {
                "workers": worker_stats,
                "total_workers": len(worker_stats),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "error": f"Failed to get worker stats: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }

    @staticmethod
    def get_transcription_stats() -> Dict[str, Any]:
        """
        Get statistics about transcriptions.

        Returns:
            Transcription statistics
        """
        db = SessionLocal()
        try:
            # Get counts by status
            total = db.query(Transcription).count()
            pending = db.query(Transcription).filter(
                Transcription.status == TranscriptionStatus.PENDING).count()
            processing = db.query(Transcription).filter(
                Transcription.status == TranscriptionStatus.PROCESSING).count()
            completed = db.query(Transcription).filter(
                Transcription.status == TranscriptionStatus.COMPLETED).count()
            failed = db.query(Transcription).filter(
                Transcription.status == TranscriptionStatus.FAILED).count()

            # Get average processing time for completed transcriptions
            completed_transcriptions = db.query(Transcription).filter(
                Transcription.status == TranscriptionStatus.COMPLETED,
                Transcription.processing_time.isnot(None)
            ).all()

            avg_processing_time = 0
            if completed_transcriptions:
                total_time = sum(t.processing_time for t in completed_transcriptions)
                avg_processing_time = total_time / len(completed_transcriptions)

            # Get success rate
            success_rate = 0
            if total > 0:
                success_rate = (completed / total) * 100

            # Get recent activity (last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_total = db.query(Transcription).filter(
                Transcription.created_at >= yesterday).count()
            recent_completed = db.query(Transcription).filter(
                Transcription.status == TranscriptionStatus.COMPLETED,
                Transcription.completed_at >= yesterday
            ).count()

            return {
                "total": total,
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "success_rate_percent": round(success_rate, 2),
                "avg_processing_time_seconds": round(avg_processing_time, 2),
                "recent_24h": {
                    "total": recent_total,
                    "completed": recent_completed
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "error": f"Failed to get transcription stats: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        finally:
            db.close()

    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """
        Get overall system health status.

        Returns:
            System health information
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }

        # Check database connectivity
        try:
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            health_status["components"]["database"] = {
                "status": "healthy",
                "message": "Database connection successful"
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }
            health_status["status"] = "unhealthy"

        # Check Redis connectivity
        try:
            redis_client = celery_app.broker_connection().default_channel.client
            redis_client.ping()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "message": "Redis connection successful"
            }
        except Exception as e:
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "message": f"Redis connection failed: {str(e)}"
            }
            health_status["status"] = "unhealthy"

        # Check Celery workers
        try:
            active_workers = celery_app.control.inspect().active()
            if active_workers:
                health_status["components"]["celery_workers"] = {
                    "status": "healthy",
                    "message": f"{len(active_workers)} active workers",
                    "workers": list(active_workers.keys())
                }
            else:
                health_status["components"]["celery_workers"] = {
                    "status": "warning",
                    "message": "No active workers found"
                }
        except Exception as e:
            health_status["components"]["celery_workers"] = {
                "status": "unhealthy",
                "message": f"Worker check failed: {str(e)}"
            }
            health_status["status"] = "unhealthy"

        return health_status

    @staticmethod
    def log_task_event(task_id: str, event_type: str, data: Dict[str, Any]):
        """
        Log task events for monitoring.

        Args:
            task_id: Celery task ID
            event_type: Type of event (started, completed, failed, etc.)
            data: Event data
        """
        event = {
            "task_id": task_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Store in Redis with expiration (24 hours)
            celery_app.backend.set(
                f"task_event:{task_id}:{event_type}",
                json.dumps(event),
                ex=86400
            )
        except Exception:
            # Fallback to logging if Redis fails
            pass

    @staticmethod
    def get_task_events(task_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get task events for a specific task.

        Args:
            task_id: Celery task ID
            hours: Number of hours to look back

        Returns:
            List of task events
        """
        events = []
        try:
            # Get all events for this task
            pattern = f"task_event:{task_id}:*"
            keys = celery_app.backend.client.keys(pattern)

            for key in keys:
                try:
                    event_data = celery_app.backend.get(key)
                    if event_data:
                        event = json.loads(event_data)
                        event_time = datetime.fromisoformat(event["timestamp"])

                        # Filter by time
                        if event_time >= datetime.utcnow() - timedelta(hours=hours):
                            events.append(event)
                except Exception:
                    continue

            # Sort by timestamp
            events.sort(key=lambda x: x["timestamp"])

        except Exception:
            pass

        return events
