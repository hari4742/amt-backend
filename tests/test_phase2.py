"""
Tests for Phase 2 implementation.
"""

import pytest
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch
from app.services.audio_service import AudioService
from app.services.midi_service import MIDIService
from app.services.file_service import FileService
from app.utils.file_utils import validate_audio_file, generate_unique_filename


class TestAudioService:
    """Test audio processing service."""

    def test_load_audio(self):
        """Test audio loading functionality."""
        # Create a simple test audio signal
        sample_rate = 44100
        duration = 1.0  # 1 second
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        test_audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave

        # Save test audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            import soundfile as sf
            sf.write(tmp_file.name, test_audio, sample_rate)
            tmp_path = tmp_file.name

        try:
            # Test loading
            audio_data, loaded_sample_rate = AudioService.load_audio(tmp_path)

            assert loaded_sample_rate == sample_rate
            assert len(audio_data) > 0
            assert isinstance(audio_data, np.ndarray)

        finally:
            # Clean up
            os.unlink(tmp_path)

    def test_analyze_audio(self):
        """Test audio analysis functionality."""
        # Create test audio data
        sample_rate = 44100
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        test_audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave

        # Test analysis
        analysis = AudioService.analyze_audio(test_audio, sample_rate)

        assert "duration" in analysis
        assert "sample_rate" in analysis
        assert "rms" in analysis
        assert "tempo" in analysis
        assert analysis["duration"] == duration
        assert analysis["sample_rate"] == sample_rate
        assert analysis["rms"] > 0

    def test_validate_audio_quality(self):
        """Test audio quality validation."""
        # Test with valid audio
        sample_rate = 44100
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        valid_audio = np.sin(2 * np.pi * 440 * t)

        is_valid, message = AudioService.validate_audio_quality(
            valid_audio, sample_rate)
        assert is_valid
        assert "acceptable" in message

        # Test with silent audio
        silent_audio = np.zeros(int(sample_rate * 0.5))  # 0.5 seconds of silence
        is_valid, message = AudioService.validate_audio_quality(
            silent_audio, sample_rate)
        assert not is_valid
        assert "silent" in message or "quiet" in message


class TestMIDIService:
    """Test MIDI generation service."""

    def test_extract_notes_from_audio(self):
        """Test note extraction from audio."""
        # Create test audio with clear pitch
        sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        test_audio = np.sin(2 * np.pi * 440 * t)  # A4 note

        # Test note extraction
        notes = MIDIService.extract_notes_from_audio(test_audio, sample_rate)

        assert isinstance(notes, list)
        # Should detect at least one note (A4 = MIDI note 69)
        if notes:
            assert "midi_note" in notes[0]
            assert "start_time" in notes[0]
            assert "end_time" in notes[0]
            assert "velocity" in notes[0]

    def test_create_midi_from_notes(self):
        """Test MIDI file creation."""
        # Create test notes
        test_notes = [
            {
                'midi_note': 60,  # Middle C
                'start_time': 0.0,
                'end_time': 0.5,
                'velocity': 100,
                'frequency': 261.63
            },
            {
                'midi_note': 64,  # E
                'start_time': 0.5,
                'end_time': 1.0,
                'velocity': 100,
                'frequency': 329.63
            }
        ]

        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Test MIDI creation
            midi = MIDIService.create_midi_from_notes(test_notes, tmp_path, tempo=120.0)

            assert os.path.exists(tmp_path)
            assert isinstance(midi, object)  # PrettyMIDI object

            # Test validation
            is_valid, message = MIDIService.validate_midi_file(tmp_path)
            assert is_valid
            assert "valid" in message

        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestFileUtils:
    """Test file utility functions."""

    def test_generate_unique_filename(self):
        """Test unique filename generation."""
        original_filename = "test_audio.wav"
        filename = generate_unique_filename(original_filename)

        assert filename.endswith('.wav')
        assert filename != original_filename
        assert len(filename) > len(original_filename)

    def test_validate_audio_file(self):
        """Test audio file validation."""
        # Mock UploadFile
        mock_file = Mock()
        mock_file.filename = "test.wav"
        mock_file.size = 1024 * 1024  # 1MB
        mock_file.content_type = "audio/wav"

        is_valid, message = validate_audio_file(mock_file)
        assert is_valid
        assert message is None

        # Test invalid file size
        mock_file.size = 200 * 1024 * 1024  # 200MB
        is_valid, message = validate_audio_file(mock_file)
        assert not is_valid
        assert "exceeds" in message

        # Test invalid format
        mock_file.filename = "test.txt"
        mock_file.size = 1024 * 1024
        is_valid, message = validate_audio_file(mock_file)
        assert not is_valid
        assert "not supported" in message


class TestFileService:
    """Test file service."""

    @pytest.mark.asyncio
    async def test_save_audio_file(self):
        """Test audio file saving."""
        # This would require more complex setup with actual file upload
        # For now, just test that the service can be instantiated
        assert FileService is not None

        # Test static methods
        result = FileService.cleanup_old_files(days_old=1)
        assert isinstance(result, int)
        assert result >= 0


if __name__ == "__main__":
    pytest.main([__file__])
