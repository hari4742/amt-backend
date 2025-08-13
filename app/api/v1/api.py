"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import transcription

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(transcription.router,
                          prefix="/api", tags=["transcription"])
