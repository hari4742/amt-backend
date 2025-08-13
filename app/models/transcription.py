"""
Transcription model for storing audio transcription data.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, Integer, Float
from sqlalchemy.sql import func
from app.core.database import Base


class TranscriptionStatus(str, Enum):
    """Status enum for transcription tasks."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Transcription(Base):
    """Transcription model for storing audio transcription data."""

    __tablename__ = "transcriptions"

    id = Column(String(36), primary_key=True, index=True)
    status = Column(
        String(20), default=TranscriptionStatus.PENDING, nullable=False)

    # File paths
    audio_path = Column(String(500), nullable=False)
    midi_path = Column(String(500), nullable=True)

    # Metadata
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    duration = Column(Float, nullable=True)  # Audio duration in seconds

    # Processing options
    model_type = Column(String(50), default="default", nullable=False)
    quality = Column(String(20), default="medium", nullable=False)

    # Results and metrics
    confidence_score = Column(Float, nullable=True)
    # Processing time in seconds
    processing_time = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(
    ), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Transcription(id={self.id}, status={self.status}, filename={self.original_filename})>"
