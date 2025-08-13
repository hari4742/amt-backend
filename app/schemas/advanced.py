"""
Pydantic schemas for Phase 5 advanced features.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ComparisonType(str, Enum):
    """Types of MIDI comparisons."""
    NOTE_ACCURACY = "note_accuracy"
    TIMING_ACCURACY = "timing_accuracy"
    RHYTHM_ACCURACY = "rhythm_accuracy"
    VELOCITY_ACCURACY = "velocity_accuracy"
    OVERALL_QUALITY = "overall_quality"


class ExportFormat(str, Enum):
    """Supported export formats."""
    MIDI_0 = "midi_0"
    MIDI_1 = "midi_1"
    MIDI_2 = "midi_2"
    JSON = "json"
    XML = "xml"
    CSV = "csv"


class BatchStatus(str, Enum):
    """Batch processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# Comparison Schemas
class ComparisonRequest(BaseModel):
    """Request for MIDI file comparison."""
    transcription_id: str = Field(..., description="Transcription ID to compare")
    reference_midi_path: str = Field(..., description="Path to reference MIDI file")
    comparison_types: Optional[List[ComparisonType]] = Field(
        default=None,
        description="Types of comparison to perform"
    )

    class Config:
        schema_extra = {
            "example": {
                "transcription_id": "trans_123456",
                "reference_midi_path": "/path/to/reference.mid",
                "comparison_types": ["note_accuracy", "timing_accuracy", "rhythm_accuracy"]
            }
        }


class NoteMatchInfo(BaseModel):
    """Information about a matched note."""
    generated_note: Dict[str, Any] = Field(...,
                                           description="Generated note information")
    reference_note: Dict[str, Any] = Field(...,
                                           description="Reference note information")
    timing_error: float = Field(..., description="Timing error in seconds")
    pitch_error: int = Field(..., description="Pitch error in semitones")
    velocity_error: int = Field(..., description="Velocity error")
    match_quality: float = Field(..., description="Match quality score (0.0 to 1.0)")


class ComparisonResponse(BaseModel):
    """Response for MIDI file comparison."""
    transcription_id: str = Field(..., description="Transcription ID")
    reference_file: str = Field(..., description="Reference file path")
    overall_score: float = Field(..., description="Overall comparison score")
    note_accuracy: float = Field(..., description="Note accuracy score")
    timing_accuracy: float = Field(..., description="Timing accuracy score")
    rhythm_accuracy: float = Field(..., description="Rhythm accuracy score")
    velocity_accuracy: float = Field(..., description="Velocity accuracy score")
    detailed_report: Dict[str,
                          Any] = Field(..., description="Detailed comparison report")

    class Config:
        schema_extra = {
            "example": {
                "transcription_id": "trans_123456",
                "reference_file": "/path/to/reference.mid",
                "overall_score": 0.85,
                "note_accuracy": 0.92,
                "timing_accuracy": 0.78,
                "rhythm_accuracy": 0.88,
                "velocity_accuracy": 0.75,
                "detailed_report": {
                    "comparison_summary": {
                        "overall_score": 0.85,
                        "note_accuracy": 0.92,
                        "timing_accuracy": 0.78
                    },
                    "detailed_metrics": {
                        "precision": 0.92,
                        "recall": 0.88,
                        "f1_score": 0.90
                    }
                }
            }
        }


# Export Schemas
class ExportRequest(BaseModel):
    """Request for transcription export."""
    transcription_id: str = Field(..., description="Transcription ID to export")
    format: ExportFormat = Field(..., description="Export format")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata to include"
    )

    class Config:
        schema_extra = {
            "example": {
                "transcription_id": "trans_123456",
                "format": "json",
                "metadata": {
                    "export_notes": "Exported for analysis",
                    "version": "1.0.0"
                }
            }
        }


class ExportResponse(BaseModel):
    """Response for transcription export."""
    transcription_id: str = Field(..., description="Transcription ID")
    export_format: str = Field(..., description="Export format used")
    output_path: str = Field(..., description="Output file path")
    file_size: int = Field(..., description="File size in bytes")
    download_url: str = Field(..., description="Download URL")

    class Config:
        schema_extra = {
            "example": {
                "transcription_id": "trans_123456",
                "export_format": "json",
                "output_path": "exports/export_trans_123456.json",
                "file_size": 2048,
                "download_url": "/api/v1/advanced/download/trans_123456?format=json"
            }
        }


# Batch Processing Schemas
class AudioFileInfo(BaseModel):
    """Information about an audio file for batch processing."""
    file_path: str = Field(..., description="Path to audio file")
    filename: str = Field(..., description="Original filename")
    file_size: Optional[int] = Field(None, description="File size in bytes")

    class Config:
        schema_extra = {
            "example": {
                "file_path": "/uploads/audio1.wav",
                "filename": "audio1.wav",
                "file_size": 1024000
            }
        }


class BatchRequest(BaseModel):
    """Request for batch processing."""
    audio_files: List[AudioFileInfo] = Field(...,
                                             description="List of audio files to process")
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Processing options"
    )

    class Config:
        schema_extra = {
            "example": {
                "audio_files": [
                    {
                        "file_path": "/uploads/audio1.wav",
                        "filename": "audio1.wav",
                        "file_size": 1024000
                    },
                    {
                        "file_path": "/uploads/audio2.wav",
                        "filename": "audio2.wav",
                        "file_size": 2048000
                    }
                ],
                "options": {
                    "quality": "high",
                    "model_type": "default"
                }
            }
        }


class BatchResponse(BaseModel):
    """Response for batch job creation."""
    batch_id: str = Field(..., description="Batch job ID")
    status: str = Field(..., description="Batch job status")
    total_files: int = Field(..., description="Total number of files")
    created_at: str = Field(..., description="Creation timestamp")
    status_url: str = Field(..., description="URL to check batch status")

    class Config:
        schema_extra = {
            "example": {
                "batch_id": "batch_20240101_120000_2",
                "status": "pending",
                "total_files": 2,
                "created_at": "2024-01-01T12:00:00Z",
                "status_url": "/api/v1/advanced/batch/batch_20240101_120000_2/status"
            }
        }


class BatchResultInfo(BaseModel):
    """Information about a batch processing result."""
    file_info: Optional[Dict[str, Any]] = Field(None, description="File information")
    transcription_id: Optional[str] = Field(None, description="Transcription ID")
    task_id: Optional[str] = Field(None, description="Task ID")
    status: str = Field(..., description="Processing status")
    error: Optional[str] = Field(None, description="Error message if failed")


class BatchStatusResponse(BaseModel):
    """Response for batch status check."""
    batch_id: str = Field(..., description="Batch job ID")
    status: str = Field(..., description="Batch job status")
    total_files: int = Field(..., description="Total number of files")
    completed_files: int = Field(..., description="Number of completed files")
    failed_files: int = Field(..., description="Number of failed files")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    results: List[BatchResultInfo] = Field(..., description="Processing results")

    class Config:
        schema_extra = {
            "example": {
                "batch_id": "batch_20240101_120000_2",
                "status": "completed",
                "total_files": 2,
                "completed_files": 2,
                "failed_files": 0,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:05:00Z",
                "completed_at": "2024-01-01T12:05:00Z",
                "error_message": None,
                "results": [
                    {
                        "file_info": {"filename": "audio1.wav"},
                        "transcription_id": "trans_123456",
                        "task_id": "task_789",
                        "status": "completed"
                    }
                ]
            }
        }


# Analysis Schemas
class NoteAnalysisResponse(BaseModel):
    """Response for note analysis."""
    transcription_id: str = Field(..., description="Transcription ID")
    analysis: Dict[str, Any] = Field(..., description="Note analysis results")

    class Config:
        schema_extra = {
            "example": {
                "transcription_id": "trans_123456",
                "analysis": {
                    "total_notes": 150,
                    "duration": 120.5,
                    "pitch_range": {
                        "min": 60,
                        "max": 84,
                        "mean": 72.5,
                        "std": 6.2
                    },
                    "velocity_stats": {
                        "min": 40,
                        "max": 127,
                        "mean": 85.3,
                        "std": 15.7
                    },
                    "note_density": 1.24
                }
            }
        }


# Format Information Schemas
class ExportFormatInfo(BaseModel):
    """Information about an export format."""
    format: str = Field(..., description="Format identifier")
    name: str = Field(..., description="Format name")
    description: str = Field(..., description="Format description")
    extension: str = Field(..., description="File extension")
    supports_metadata: bool = Field(..., description="Whether format supports metadata")


class SupportedFormatsResponse(BaseModel):
    """Response for supported formats."""
    export_formats: List[ExportFormatInfo] = Field(
        ..., description="Supported export formats")
    comparison_types: List[str] = Field(..., description="Supported comparison types")

    class Config:
        schema_extra = {
            "example": {
                "export_formats": [
                    {
                        "format": "midi_1",
                        "name": "MIDI Format 1",
                        "description": "Multi-track MIDI format",
                        "extension": ".mid",
                        "supports_metadata": True
                    },
                    {
                        "format": "json",
                        "name": "JSON",
                        "description": "Structured data format",
                        "extension": ".json",
                        "supports_metadata": True
                    }
                ],
                "comparison_types": [
                    "note_accuracy",
                    "timing_accuracy",
                    "rhythm_accuracy",
                    "velocity_accuracy",
                    "overall_quality"
                ]
            }
        }
