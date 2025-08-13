"""
Utility endpoints for system information and supported formats.
"""

from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/formats")
async def get_supported_formats():
    """
    Get supported audio formats and their specifications.

    Returns:
        Dictionary of supported formats with details
    """
    formats = {
        "audio": {
            "wav": {
                "description": "Waveform Audio File Format",
                "mime_type": "audio/wav",
                "extensions": [".wav"],
                "max_size_mb": settings.max_file_size // (1024 * 1024),
                "supported": True
            },
            "mp3": {
                "description": "MPEG Audio Layer III",
                "mime_type": "audio/mpeg",
                "extensions": [".mp3"],
                "max_size_mb": settings.max_file_size // (1024 * 1024),
                "supported": True
            },
            "flac": {
                "description": "Free Lossless Audio Codec",
                "mime_type": "audio/flac",
                "extensions": [".flac"],
                "max_size_mb": settings.max_file_size // (1024 * 1024),
                "supported": True
            },
            "m4a": {
                "description": "MPEG-4 Audio",
                "mime_type": "audio/mp4",
                "extensions": [".m4a", ".mp4"],
                "max_size_mb": settings.max_file_size // (1024 * 1024),
                "supported": True
            },
            "ogg": {
                "description": "Ogg Vorbis Audio",
                "mime_type": "audio/ogg",
                "extensions": [".ogg", ".oga"],
                "max_size_mb": settings.max_file_size // (1024 * 1024),
                "supported": True
            }
        },
        "output": {
            "midi": {
                "description": "Musical Instrument Digital Interface",
                "mime_type": "audio/midi",
                "extensions": [".mid", ".midi"],
                "supported": True
            }
        }
    }

    return {
        "supported_formats": formats,
        "max_file_size_bytes": settings.max_file_size,
        "max_audio_duration_seconds": settings.max_audio_duration,
        "sample_rate": settings.sample_rate
    }


@router.get("/info")
async def get_system_info():
    """
    Get system information and capabilities.

    Returns:
        System information and configuration details
    """
    import platform
    import psutil

    return {
        "service": {
            "name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug
        },
        "system": {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "architecture": platform.architecture()[0]
        },
        "resources": {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "disk_usage_percent": psutil.disk_usage('/').percent
        },
        "configuration": {
            "upload_directory": settings.upload_dir,
            "max_file_size_mb": settings.max_file_size // (1024 * 1024),
            "max_audio_duration_minutes": settings.max_audio_duration // 60,
            "sample_rate": settings.sample_rate,
            "allowed_audio_formats": settings.allowed_audio_formats
        }
    }


@router.get("/stats")
async def get_service_stats():
    """
    Get service statistics and usage information.

    Returns:
        Service statistics
    """
    from sqlalchemy.orm import Session
    from app.core.database import get_db
    from app.models.transcription import Transcription, TranscriptionStatus

    # This would typically be called with a database session
    # For now, return basic stats structure
    stats = {
        "transcriptions": {
            "total": 0,
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0
        },
        "storage": {
            "upload_directory": settings.upload_dir,
            "total_files": 0,
            "total_size_mb": 0
        },
        "performance": {
            "average_processing_time_seconds": 0,
            "success_rate_percent": 0
        }
    }

    return stats


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for connectivity testing.

    Returns:
        Pong response
    """
    return {"message": "pong", "timestamp": "2024-01-01T12:00:00Z"}
