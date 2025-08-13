"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import transcription, health, utils, advanced

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(transcription.router,
                          prefix="/transcribe", tags=["transcription"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(advanced.router, prefix="/advanced", tags=["advanced"])
