"""
Health check and monitoring endpoints.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, engine
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "service": settings.app_name
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with database connectivity.

    Args:
        db: Database session

    Returns:
        Detailed health status with component checks
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "service": settings.app_name,
        "components": {}
    }

    # Check database connectivity
    try:
        db.execute("SELECT 1")
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

    # Check file system
    try:
        import os
        upload_dir = settings.upload_dir
        if os.path.exists(upload_dir):
            health_status["components"]["filesystem"] = {
                "status": "healthy",
                "message": "Upload directory accessible",
                "upload_dir": upload_dir
            }
        else:
            health_status["components"]["filesystem"] = {
                "status": "warning",
                "message": "Upload directory does not exist",
                "upload_dir": upload_dir
            }
    except Exception as e:
        health_status["components"]["filesystem"] = {
            "status": "unhealthy",
            "message": f"File system check failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"

    # Check configuration
    try:
        health_status["components"]["configuration"] = {
            "status": "healthy",
            "message": "Configuration loaded successfully",
            "debug_mode": settings.debug,
            "max_file_size": settings.max_file_size,
            "allowed_formats": settings.allowed_audio_formats
        }
    except Exception as e:
        health_status["components"]["configuration"] = {
            "status": "unhealthy",
            "message": f"Configuration error: {str(e)}"
        }
        health_status["status"] = "unhealthy"

    return health_status


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration.

    Returns:
        Readiness status
    """
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check for Kubernetes/container orchestration.

    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
