"""
File management service for handling file uploads and storage.
"""

import os
import aiofiles
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models.transcription import Transcription
from app.utils.file_utils import (
    validate_audio_file,
    get_upload_paths,
    cleanup_file,
    get_file_size
)
from app.config import settings


class FileService:
    """Service for managing file operations."""

    @staticmethod
    async def save_audio_file(
        file: UploadFile,
        transcription_id: str,
        db: Session
    ) -> Tuple[str, int]:
        """
        Save uploaded audio file and create transcription record.

        Args:
            file: Uploaded audio file
            transcription_id: Unique transcription ID
            db: Database session

        Returns:
            Tuple of (audio_path, file_size)
        """
        # Validate file
        is_valid, error_message = validate_audio_file(file)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        # Generate file paths
        audio_path, midi_path = get_upload_paths(transcription_id, file.filename)

        # Save file
        try:
            async with aiofiles.open(audio_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to save file: {str(e)}")

        # Get file size
        file_size = get_file_size(audio_path)

        # Create transcription record
        transcription = Transcription(
            id=transcription_id,
            audio_path=audio_path,
            midi_path=midi_path,
            original_filename=file.filename,
            file_size=file_size,
            status="pending"
        )

        db.add(transcription)
        db.commit()
        db.refresh(transcription)

        return audio_path, file_size

    @staticmethod
    def get_transcription_files(transcription_id: str, db: Session) -> Tuple[Optional[str], Optional[str]]:
        """
        Get file paths for a transcription.

        Args:
            transcription_id: Unique transcription ID
            db: Database session

        Returns:
            Tuple of (audio_path, midi_path)
        """
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id).first()
        if not transcription:
            return None, None

        return transcription.audio_path, transcription.midi_path

    @staticmethod
    def delete_transcription_files(transcription_id: str, db: Session) -> bool:
        """
        Delete all files associated with a transcription.

        Args:
            transcription_id: Unique transcription ID
            db: Database session

        Returns:
            True if files were deleted successfully
        """
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id).first()
        if not transcription:
            return False

        # Delete audio file
        audio_deleted = cleanup_file(transcription.audio_path)

        # Delete MIDI file if it exists
        midi_deleted = True
        if transcription.midi_path and os.path.exists(transcription.midi_path):
            midi_deleted = cleanup_file(transcription.midi_path)

        # Delete database record
        db.delete(transcription)
        db.commit()

        return audio_deleted and midi_deleted

    @staticmethod
    def cleanup_old_files(days_old: int = 7) -> int:
        """
        Clean up files older than specified days.

        Args:
            days_old: Number of days to keep files

        Returns:
            Number of files deleted
        """
        import time
        from datetime import datetime, timedelta

        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        deleted_count = 0

        # Clean up audio files
        audio_dir = os.path.join(settings.upload_dir, "audio")
        if os.path.exists(audio_dir):
            for filename in os.listdir(audio_dir):
                file_path = os.path.join(audio_dir, filename)
                if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                    if cleanup_file(file_path):
                        deleted_count += 1

        # Clean up MIDI files
        midi_dir = os.path.join(settings.upload_dir, "midi")
        if os.path.exists(midi_dir):
            for filename in os.listdir(midi_dir):
                file_path = os.path.join(midi_dir, filename)
                if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                    if cleanup_file(file_path):
                        deleted_count += 1

        return deleted_count
