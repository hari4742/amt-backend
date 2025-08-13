"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import transcription, health, utils

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(transcription.router, prefix="/api", tags=["transcription"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(utils.router, prefix="/api", tags=["utils"])
