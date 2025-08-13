"""
File utility functions for file management and validation.
"""

import os
import uuid
import magic
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
from app.config import settings


def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """
    Generate a unique filename with UUID.

    Args:
        original_filename: Original filename
        prefix: Optional prefix for the filename

    Returns:
        Unique filename with extension
    """
    # Get file extension
    file_ext = Path(original_filename).suffix.lower()

    # Generate unique ID
    unique_id = str(uuid.uuid4())

    # Create filename
    if prefix:
        filename = f"{prefix}_{unique_id}{file_ext}"
    else:
        filename = f"{unique_id}{file_ext}"

    return filename


def validate_audio_file(file: UploadFile) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded audio file.

    Args:
        file: Uploaded file object

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    if file.size and file.size > settings.max_file_size:
        return False, f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"

    # Check file extension
    file_ext = Path(file.filename).suffix.lower().lstrip('.')
    if file_ext not in settings.allowed_audio_formats:
        return False, f"File format '{file_ext}' is not supported. Allowed formats: {', '.join(settings.allowed_audio_formats)}"

    # Check MIME type (basic validation)
    if file.content_type:
        audio_mime_types = [
            'audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/flac',
            'audio/mp4', 'audio/ogg', 'audio/x-wav', 'audio/x-m4a'
        ]
        if file.content_type not in audio_mime_types:
            return False, f"Invalid MIME type: {file.content_type}"

    return True, None


def get_file_mime_type(file_path: str) -> str:
    """
    Get MIME type of a file using python-magic.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string
    """
    try:
        mime_type = magic.from_file(file_path, mime=True)
        return mime_type
    except Exception:
        return "application/octet-stream"


def ensure_directory_exists(directory_path: str) -> None:
    """
    Ensure a directory exists, create if it doesn't.

    Args:
        directory_path: Path to the directory
    """
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes
    """
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def cleanup_file(file_path: str) -> bool:
    """
    Safely delete a file.

    Args:
        file_path: Path to the file to delete

    Returns:
        True if file was deleted, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except OSError:
        return False


def get_upload_paths(transcription_id: str, original_filename: str) -> Tuple[str, str]:
    """
    Generate upload paths for audio and MIDI files.

    Args:
        transcription_id: Unique transcription ID
        original_filename: Original audio filename

    Returns:
        Tuple of (audio_path, midi_path)
    """
    # Ensure upload directories exist
    audio_dir = os.path.join(settings.upload_dir, "audio")
    midi_dir = os.path.join(settings.upload_dir, "midi")

    ensure_directory_exists(audio_dir)
    ensure_directory_exists(midi_dir)

    # Generate filenames
    audio_filename = generate_unique_filename(original_filename, "audio")
    midi_filename = f"{transcription_id}.mid"

    # Generate full paths
    audio_path = os.path.join(audio_dir, audio_filename)
    midi_path = os.path.join(midi_dir, midi_filename)

    return audio_path, midi_path
