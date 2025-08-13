"""
Tests for Phase 5 advanced features implementation.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.services.comparison_service import (
    ComparisonService,
    ComparisonType,
    NoteMatch,
    ComparisonResult
)
from app.services.export_service import ExportService, ExportFormat
from app.services.batch_service import BatchService, BatchStatus, BatchJob
from app.schemas.advanced import (
    ComparisonRequest,
    ExportRequest,
    BatchRequest,
    ComparisonType as SchemaComparisonType,
    ExportFormat as SchemaExportFormat
)


class TestComparisonService:
    """Test MIDI comparison service."""

    def test_compare_midi_files_basic(self):
        """Test basic MIDI file comparison."""
        # Mock MIDI files
        mock_generated_midi = Mock()
        mock_reference_midi = Mock()

        # Mock notes
        mock_generated_note = Mock()
        mock_generated_note.pitch = 60
        mock_generated_note.start = 1.0
        mock_generated_note.end = 2.0
        mock_generated_note.velocity = 100

        mock_reference_note = Mock()
        mock_reference_note.pitch = 60
        mock_reference_note.start = 1.1
        mock_reference_note.end = 2.1
        mock_reference_note.velocity = 95

        mock_generated_midi.instruments = [Mock(notes=[mock_generated_note])]
        mock_reference_midi.instruments = [Mock(notes=[mock_reference_note])]
        mock_generated_midi.get_end_time.return_value = 3.0
        mock_reference_midi.get_end_time.return_value = 3.0

        with patch('pretty_midi.PrettyMIDI') as mock_pretty_midi:
            mock_pretty_midi.side_effect = [mock_generated_midi, mock_reference_midi]

            # Test comparison
            result = ComparisonService.compare_midi_files(
                "generated.mid",
                "reference.mid"
            )

            assert isinstance(result, ComparisonResult)
            assert 0.0 <= result.overall_score <= 1.0
            assert 0.0 <= result.note_accuracy <= 1.0
            assert 0.0 <= result.timing_accuracy <= 1.0

    def test_analyze_note_distribution(self):
        """Test note distribution analysis."""
        # Mock MIDI file
        mock_midi = Mock()
        mock_midi.get_end_time.return_value = 120.0

        mock_note1 = Mock()
        mock_note1.pitch = 60
        mock_note1.velocity = 100
        mock_note1.start = 0.0
        mock_note1.end = 1.0

        mock_note2 = Mock()
        mock_note2.pitch = 72
        mock_note2.velocity = 80
        mock_note2.start = 1.0
        mock_note2.end = 2.0

        mock_midi.instruments = [Mock(notes=[mock_note1, mock_note2])]

        with patch('pretty_midi.PrettyMIDI', return_value=mock_midi):
            analysis = ComparisonService.analyze_note_distribution("test.mid")

            assert "total_notes" in analysis
            assert "duration" in analysis
            assert "pitch_range" in analysis
            assert "velocity_stats" in analysis
            assert analysis["total_notes"] == 2
            assert analysis["duration"] == 120.0

    def test_generate_comparison_report(self):
        """Test comparison report generation."""
        # Mock comparison result
        mock_result = Mock()
        mock_result.overall_score = 0.85
        mock_result.note_accuracy = 0.92
        mock_result.timing_accuracy = 0.78
        mock_result.rhythm_accuracy = 0.88
        mock_result.velocity_accuracy = 0.75
        mock_result.note_matches = []
        mock_result.unmatched_generated = []
        mock_result.unmatched_reference = []

        report = ComparisonService.generate_comparison_report(
            mock_result,
            "generated.mid",
            "reference.mid"
        )

        assert "comparison_summary" in report
        assert "detailed_metrics" in report
        assert "file_analysis" in report
        assert report["comparison_summary"]["overall_score"] == 0.85


class TestExportService:
    """Test export service."""

    def test_export_midi_json(self):
        """Test MIDI export to JSON format."""
        # Mock MIDI file
        mock_midi = Mock()
        mock_midi.get_end_time.return_value = 60.0

        mock_note = Mock()
        mock_note.pitch = 60
        mock_note.start = 0.0
        mock_note.end = 1.0
        mock_note.velocity = 100

        mock_midi.instruments = [Mock(notes=[mock_note])]
        mock_midi.tempo_changes = []
        mock_midi.time_signature_changes = []
        mock_midi.key_signature_changes = []

        with patch('pretty_midi.PrettyMIDI', return_value=mock_midi):
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                result = ExportService.export_midi(
                    "source.mid",
                    temp_path,
                    ExportFormat.JSON
                )

                assert result["status"] == "success"
                assert result["format"] == "json"
                assert "file_size" in result

                # Check that file was created
                assert os.path.exists(temp_path)

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_export_midi_xml(self):
        """Test MIDI export to XML format."""
        # Mock MIDI file
        mock_midi = Mock()
        mock_midi.get_end_time.return_value = 60.0
        mock_midi.instruments = [Mock(notes=[], name="Piano", program=0, is_drum=False)]
        mock_midi.tempo_changes = []
        mock_midi.time_signature_changes = []
        mock_midi.key_signature_changes = []

        with patch('pretty_midi.PrettyMIDI', return_value=mock_midi):
            with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                result = ExportService.export_midi(
                    "source.mid",
                    temp_path,
                    ExportFormat.XML
                )

                assert result["status"] == "success"
                assert result["format"] == "xml"

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def test_export_transcription_metadata(self):
        """Test transcription metadata export."""
        transcription_data = {
            "original_filename": "test.wav",
            "file_size": 1024000,
            "duration": 60.0,
            "total_notes": 150,
            "confidence_score": 0.85,
            "processing_time": 30.0,
            "model_type": "default"
        }

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            result = ExportService.export_transcription_metadata(
                "trans_123",
                transcription_data,
                temp_path,
                ExportFormat.JSON
            )

            assert result["status"] == "success"
            assert result["format"] == "json"
            assert "metadata" in result

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_get_supported_formats(self):
        """Test getting supported export formats."""
        formats = ExportService.get_supported_formats()

        assert isinstance(formats, list)
        assert len(formats) > 0

        for format_info in formats:
            assert "format" in format_info
            assert "name" in format_info
            assert "description" in format_info
            assert "extension" in format_info
            assert "supports_metadata" in format_info


class TestBatchService:
    """Test batch processing service."""

    def test_create_batch_job(self):
        """Test batch job creation."""
        audio_files = [
            {"file_path": "/path/to/audio1.wav", "filename": "audio1.wav"},
            {"file_path": "/path/to/audio2.wav", "filename": "audio2.wav"}
        ]

        options = {"quality": "high"}

        batch_job = BatchService.create_batch_job(audio_files, options)

        assert isinstance(batch_job, BatchJob)
        assert batch_job.batch_id.startswith("batch_")
        assert batch_job.status == BatchStatus.PENDING
        assert batch_job.total_files == 2
        assert batch_job.completed_files == 0
        assert batch_job.failed_files == 0

    def test_batch_export(self):
        """Test batch export functionality."""
        # Mock batch job
        mock_batch_job = Mock()
        mock_batch_job.batch_id = "batch_123"
        mock_batch_job.results = [
            {
                "status": "completed",
                "transcription_id": "trans_1",
                "file_info": {"filename": "audio1.wav"}
            }
        ]

        with patch.object(BatchService, '_get_batch_job', return_value=mock_batch_job):
            with patch.object(FileService, 'get_transcription_files') as mock_get_files:
                mock_get_files.return_value = {"midi_path": "/path/to/midi.mid"}

                with patch.object(ExportService, 'export_midi') as mock_export:
                    mock_export.return_value = {
                        "status": "success",
                        "file_size": 1024
                    }

                    result = BatchService.batch_export(
                        "batch_123",
                        ExportFormat.JSON,
                        include_metadata=True
                    )

                    assert "batch_id" in result
                    assert "export_format" in result
                    assert "total_files" in result


class TestAdvancedSchemas:
    """Test advanced feature schemas."""

    def test_comparison_request_schema(self):
        """Test comparison request schema."""
        request = ComparisonRequest(
            transcription_id="trans_123",
            reference_midi_path="/path/to/reference.mid",
            comparison_types=[SchemaComparisonType.NOTE_ACCURACY,
                              SchemaComparisonType.TIMING_ACCURACY]
        )

        assert request.transcription_id == "trans_123"
        assert request.reference_midi_path == "/path/to/reference.mid"
        assert len(request.comparison_types) == 2

    def test_export_request_schema(self):
        """Test export request schema."""
        request = ExportRequest(
            transcription_id="trans_123",
            format=SchemaExportFormat.JSON,
            metadata={"version": "1.0.0"}
        )

        assert request.transcription_id == "trans_123"
        assert request.format == SchemaExportFormat.JSON
        assert request.metadata["version"] == "1.0.0"

    def test_batch_request_schema(self):
        """Test batch request schema."""
        from app.schemas.advanced import AudioFileInfo

        audio_files = [
            AudioFileInfo(
                file_path="/path/to/audio1.wav",
                filename="audio1.wav",
                file_size=1024000
            )
        ]

        request = BatchRequest(
            audio_files=audio_files,
            options={"quality": "high"}
        )

        assert len(request.audio_files) == 1
        assert request.audio_files[0].filename == "audio1.wav"
        assert request.options["quality"] == "high"


class TestAdvancedEndpoints:
    """Test advanced API endpoints."""

    def test_get_supported_formats_endpoint(self, client):
        """Test getting supported formats endpoint."""
        response = client.get("/api/v1/advanced/formats")

        assert response.status_code == 200
        data = response.json()

        assert "export_formats" in data
        assert "comparison_types" in data
        assert isinstance(data["export_formats"], list)
        assert isinstance(data["comparison_types"], list)

    def test_compare_midi_files_endpoint(self, client):
        """Test MIDI comparison endpoint."""
        request_data = {
            "transcription_id": "trans_123",
            "reference_midi_path": "/path/to/reference.mid",
            "comparison_types": ["note_accuracy", "timing_accuracy"]
        }

        with patch.object(FileService, 'get_transcription_files') as mock_get_files:
            mock_get_files.return_value = {"midi_path": "/path/to/generated.mid"}

            with patch.object(ComparisonService, 'compare_midi_files') as mock_compare:
                mock_result = Mock()
                mock_result.overall_score = 0.85
                mock_result.note_accuracy = 0.92
                mock_result.timing_accuracy = 0.78
                mock_result.rhythm_accuracy = 0.88
                mock_result.velocity_accuracy = 0.75
                mock_compare.return_value = mock_result

                with patch.object(ComparisonService, 'generate_comparison_report') as mock_report:
                    mock_report.return_value = {"summary": "test"}

                    response = client.post(
                        "/api/v1/advanced/compare", json=request_data)

                    # Should fail because reference file doesn't exist
                    assert response.status_code == 404

    def test_export_transcription_endpoint(self, client):
        """Test transcription export endpoint."""
        request_data = {
            "transcription_id": "trans_123",
            "format": "json",
            "metadata": {"version": "1.0.0"}
        }

        with patch.object(FileService, 'get_transcription_files') as mock_get_files:
            mock_get_files.return_value = {"midi_path": "/path/to/midi.mid"}

            with patch.object(ExportService, 'export_midi') as mock_export:
                mock_export.return_value = {
                    "status": "success",
                    "file_size": 1024
                }

                response = client.post("/api/v1/advanced/export", json=request_data)

                # Should succeed
                assert response.status_code == 200
                data = response.json()
                assert data["transcription_id"] == "trans_123"
                assert data["export_format"] == "json"


if __name__ == "__main__":
    pytest.main([__file__])
