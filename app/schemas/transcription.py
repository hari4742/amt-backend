"""
Pydantic schemas for transcription requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.transcription import TranscriptionStatus


class TranscriptionOptions(BaseModel):
    """Options for transcription processing."""
    model_type: str = Field(
        default="default", description="Type of transcription model to use")
    quality: str = Field(
        default="medium", description="Quality level: low, medium, high")

    class Config:
        json_schema_extra = {
            "example": {
                "model_type": "default",
                "quality": "medium"
            }
        }


class TranscriptionCreate(BaseModel):
    """Schema for creating a new transcription."""
    transcription_id: str = Field(...,
                                  description="Unique identifier for the transcription")
    original_filename: str = Field(...,
                                   description="Original filename of the uploaded audio")
    file_size: int = Field(...,
                           description="Size of the uploaded file in bytes")

    class Config:
        json_schema_extra = {
            "example": {
                "transcription_id": "550e8400-e29b-41d4-a716-446655440000",
                "original_filename": "sample_audio.wav",
                "file_size": 1024000
            }
        }


class TranscriptionResponse(BaseModel):
    """Schema for transcription response."""
    id: str
    status: TranscriptionStatus
    original_filename: str
    file_size: int
    duration: Optional[float] = None
    model_type: str
    quality: str
    confidence_score: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "original_filename": "sample_audio.wav",
                "file_size": 1024000,
                "duration": 120.5,
                "model_type": "default",
                "quality": "medium",
                "confidence_score": 0.85,
                "processing_time": 45.2,
                "error_message": None,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:01:00Z",
                "completed_at": "2024-01-01T12:01:00Z"
            }
        }


class TranscriptionStatusResponse(BaseModel):
    """Schema for transcription status response."""
    id: str
    status: TranscriptionStatus
    progress: Optional[float] = Field(
        None, ge=0, le=100, description="Progress percentage")
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "progress": 75.5,
                "estimated_completion": "2024-01-01T12:02:00Z",
                "error_message": None,
                "updated_at": "2024-01-01T12:01:30Z"
            }
        }


class TranscriptionListResponse(BaseModel):
    """Schema for list of transcriptions."""
    transcriptions: list[TranscriptionResponse]
    total: int
    page: int
    size: int

    class Config:
        json_schema_extra = {
            "example": {
                "transcriptions": [],
                "total": 0,
                "page": 1,
                "size": 10
            }
        }
