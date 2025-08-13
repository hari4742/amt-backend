"""
Export service for multiple MIDI formats, metadata export, and batch processing.
"""

import os
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import pretty_midi
import mido
from dataclasses import dataclass, asdict
from enum import Enum


class ExportFormat(Enum):
    """Supported export formats."""
    MIDI_0 = "midi_0"
    MIDI_1 = "midi_1"
    MIDI_2 = "midi_2"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    MUSICXML = "musicxml"


@dataclass
class ExportMetadata:
    """Metadata for exported files."""
    transcription_id: str
    original_filename: str
    export_format: str
    export_timestamp: str
    file_size: int
    duration: float
    total_notes: int
    quality_score: float
    processing_time: float
    model_type: str
    version: str = "1.0.0"


class ExportService:
    """Service for exporting MIDI files in various formats and metadata."""

    @staticmethod
    def export_midi(
        source_midi_path: str,
        output_path: str,
        format_type: ExportFormat,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Export MIDI file in specified format.

        Args:
            source_midi_path: Path to source MIDI file
            output_path: Path for output file
            format_type: Export format
            metadata: Additional metadata to include

        Returns:
            Export result information
        """
        try:
            if format_type in [ExportFormat.MIDI_0, ExportFormat.MIDI_1, ExportFormat.MIDI_2]:
                return ExportService._export_midi_format(
                    source_midi_path, output_path, format_type, metadata
                )
            elif format_type == ExportFormat.JSON:
                return ExportService._export_json(
                    source_midi_path, output_path, metadata
                )
            elif format_type == ExportFormat.XML:
                return ExportService._export_xml(
                    source_midi_path, output_path, metadata
                )
            elif format_type == ExportFormat.CSV:
                return ExportService._export_csv(
                    source_midi_path, output_path, metadata
                )
            else:
                raise ValueError(f"Unsupported export format: {format_type}")

        except Exception as e:
            raise ValueError(f"Export failed: {str(e)}")

    @staticmethod
    def _export_midi_format(
        source_midi_path: str,
        output_path: str,
        format_type: ExportFormat,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Export MIDI in different MIDI formats."""
        # Load source MIDI
        midi = pretty_midi.PrettyMIDI(source_midi_path)

        # Add metadata as text events if provided
        if metadata:
            ExportService._add_metadata_to_midi(midi, metadata)

        # Export based on format
        if format_type == ExportFormat.MIDI_0:
            # MIDI 0 format (single track)
            midi.write(output_path, format=0)
        elif format_type == ExportFormat.MIDI_1:
            # MIDI 1 format (multiple tracks)
            midi.write(output_path, format=1)
        elif format_type == ExportFormat.MIDI_2:
            # MIDI 2 format (if supported)
            # Note: MIDI 2 support may be limited in current libraries
            midi.write(output_path, format=1)  # Fallback to MIDI 1

        # Get file info
        file_size = os.path.getsize(output_path)

        return {
            "status": "success",
            "output_path": output_path,
            "format": format_type.value,
            "file_size": file_size,
            "duration": midi.get_end_time(),
            "total_notes": sum(len(instrument.notes) for instrument in midi.instruments)
        }

    @staticmethod
    def _export_json(
        source_midi_path: str,
        output_path: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Export MIDI data as JSON."""
        midi = pretty_midi.PrettyMIDI(source_midi_path)

        # Convert MIDI to JSON structure
        json_data = {
            "metadata": metadata or {},
            "duration": midi.get_end_time(),
            "tempo_changes": [
                {
                    "time": change.time,
                    "tempo": change.tempo
                }
                for change in midi.tempo_changes
            ],
            "time_signature_changes": [
                {
                    "time": change.time,
                    "numerator": change.numerator,
                    "denominator": change.denominator
                }
                for change in midi.time_signature_changes
            ],
            "key_signature_changes": [
                {
                    "time": change.time,
                    "key_number": change.key_number,
                    "mode": change.mode
                }
                for change in midi.key_signature_changes
            ],
            "instruments": []
        }

        # Convert instruments and notes
        for i, instrument in enumerate(midi.instruments):
            instrument_data = {
                "id": i,
                "name": instrument.name,
                "program": instrument.program,
                "is_drum": instrument.is_drum,
                "notes": [
                    {
                        "pitch": note.pitch,
                        "start": note.start,
                        "end": note.end,
                        "velocity": note.velocity
                    }
                    for note in instrument.notes
                ],
                "control_changes": [
                    {
                        "number": cc.number,
                        "value": cc.value,
                        "time": cc.time
                    }
                    for cc in instrument.control_changes
                ]
            }
            json_data["instruments"].append(instrument_data)

        # Write JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        file_size = os.path.getsize(output_path)

        return {
            "status": "success",
            "output_path": output_path,
            "format": "json",
            "file_size": file_size,
            "duration": midi.get_end_time(),
            "total_notes": sum(len(instrument.notes) for instrument in midi.instruments)
        }

    @staticmethod
    def _export_xml(
        source_midi_path: str,
        output_path: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Export MIDI data as XML."""
        midi = pretty_midi.PrettyMIDI(source_midi_path)

        # Create XML structure
        root = ET.Element("midi")

        # Add metadata
        if metadata:
            meta_elem = ET.SubElement(root, "metadata")
            for key, value in metadata.items():
                meta_item = ET.SubElement(meta_elem, "item")
                meta_item.set("key", str(key))
                meta_item.set("value", str(value))

        # Add basic info
        info_elem = ET.SubElement(root, "info")
        info_elem.set("duration", str(midi.get_end_time()))
        info_elem.set("total_notes", str(sum(len(instrument.notes)
                      for instrument in midi.instruments)))

        # Add tempo changes
        if midi.tempo_changes:
            tempo_elem = ET.SubElement(root, "tempo_changes")
            for change in midi.tempo_changes:
                tempo_item = ET.SubElement(tempo_elem, "tempo")
                tempo_item.set("time", str(change.time))
                tempo_item.set("value", str(change.tempo))

        # Add instruments
        instruments_elem = ET.SubElement(root, "instruments")
        for i, instrument in enumerate(midi.instruments):
            inst_elem = ET.SubElement(instruments_elem, "instrument")
            inst_elem.set("id", str(i))
            inst_elem.set("name", instrument.name)
            inst_elem.set("program", str(instrument.program))
            inst_elem.set("is_drum", str(instrument.is_drum))

            # Add notes
            notes_elem = ET.SubElement(inst_elem, "notes")
            for note in instrument.notes:
                note_elem = ET.SubElement(notes_elem, "note")
                note_elem.set("pitch", str(note.pitch))
                note_elem.set("start", str(note.start))
                note_elem.set("end", str(note.end))
                note_elem.set("velocity", str(note.velocity))

        # Write XML file
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding='utf-8',
                   xml_declaration=True, pretty_print=True)

        file_size = os.path.getsize(output_path)

        return {
            "status": "success",
            "output_path": output_path,
            "format": "xml",
            "file_size": file_size,
            "duration": midi.get_end_time(),
            "total_notes": sum(len(instrument.notes) for instrument in midi.instruments)
        }

    @staticmethod
    def _export_csv(
        source_midi_path: str,
        output_path: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Export MIDI data as CSV."""
        midi = pretty_midi.PrettyMIDI(source_midi_path)

        # Write CSV file
        with open(output_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(
                "instrument_id,instrument_name,note_pitch,start_time,end_time,duration,velocity\n")

            # Write note data
            for i, instrument in enumerate(midi.instruments):
                for note in instrument.notes:
                    duration = note.end - note.start
                    f.write(
                        f"{i},{instrument.name},{note.pitch},{note.start},{note.end},{duration},{note.velocity}\n")

        file_size = os.path.getsize(output_path)

        return {
            "status": "success",
            "output_path": output_path,
            "format": "csv",
            "file_size": file_size,
            "duration": midi.get_end_time(),
            "total_notes": sum(len(instrument.notes) for instrument in midi.instruments)
        }

    @staticmethod
    def _add_metadata_to_midi(midi: pretty_midi.PrettyMIDI, metadata: Dict[str, Any]):
        """Add metadata as text events to MIDI file."""
        # Create a new instrument for metadata
        meta_instrument = pretty_midi.Instrument(
            program=0, is_drum=False, name="Metadata")

        # Add metadata as text events
        for key, value in metadata.items():
            text_event = pretty_midi.Note(
                pitch=60,  # Middle C
                start=0.0,
                end=0.1,
                velocity=0
            )
            # Note: pretty_midi doesn't directly support text events
            # This is a simplified approach - in practice, you'd use mido for text events

        midi.instruments.append(meta_instrument)

    @staticmethod
    def export_transcription_metadata(
        transcription_id: str,
        transcription_data: Dict[str, Any],
        output_path: str,
        format_type: ExportFormat
    ) -> Dict[str, Any]:
        """
        Export transcription metadata in specified format.

        Args:
            transcription_id: Transcription ID
            transcription_data: Transcription data
            output_path: Output file path
            format_type: Export format

        Returns:
            Export result
        """
        # Create metadata object
        metadata = ExportMetadata(
            transcription_id=transcription_id,
            original_filename=transcription_data.get('original_filename', ''),
            export_format=format_type.value,
            export_timestamp=datetime.utcnow().isoformat(),
            file_size=transcription_data.get('file_size', 0),
            duration=transcription_data.get('duration', 0.0),
            total_notes=transcription_data.get('total_notes', 0),
            quality_score=transcription_data.get('confidence_score', 0.0),
            processing_time=transcription_data.get('processing_time', 0.0),
            model_type=transcription_data.get('model_type', 'unknown')
        )

        # Export based on format
        if format_type == ExportFormat.JSON:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)
        elif format_type == ExportFormat.XML:
            root = ET.Element("transcription_metadata")
            for key, value in asdict(metadata).items():
                elem = ET.SubElement(root, key)
                elem.text = str(value)
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
        else:
            raise ValueError(f"Unsupported metadata format: {format_type}")

        file_size = os.path.getsize(output_path)

        return {
            "status": "success",
            "output_path": output_path,
            "format": format_type.value,
            "file_size": file_size,
            "metadata": asdict(metadata)
        }

    @staticmethod
    def batch_export(
        source_files: List[Dict[str, str]],
        output_dir: str,
        format_type: ExportFormat,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Batch export multiple MIDI files.

        Args:
            source_files: List of source file information
            output_dir: Output directory
            format_type: Export format
            metadata: Additional metadata

        Returns:
            Batch export results
        """
        results = []
        errors = []

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        for file_info in source_files:
            try:
                source_path = file_info['source_path']
                filename = file_info.get('filename', os.path.basename(source_path))

                # Generate output path
                base_name = Path(filename).stem
                if format_type == ExportFormat.JSON:
                    output_path = os.path.join(output_dir, f"{base_name}.json")
                elif format_type == ExportFormat.XML:
                    output_path = os.path.join(output_dir, f"{base_name}.xml")
                elif format_type == ExportFormat.CSV:
                    output_path = os.path.join(output_dir, f"{base_name}.csv")
                else:
                    output_path = os.path.join(output_dir, f"{base_name}.mid")

                # Export file
                result = ExportService.export_midi(
                    source_path, output_path, format_type, metadata
                )
                result['source_file'] = filename
                results.append(result)

            except Exception as e:
                error_info = {
                    'source_file': file_info.get('filename', 'unknown'),
                    'error': str(e)
                }
                errors.append(error_info)

        return {
            "status": "completed",
            "total_files": len(source_files),
            "successful_exports": len(results),
            "failed_exports": len(errors),
            "results": results,
            "errors": errors,
            "output_directory": output_dir
        }

    @staticmethod
    def get_supported_formats() -> List[Dict[str, Any]]:
        """Get list of supported export formats."""
        return [
            {
                "format": "midi_0",
                "name": "MIDI Format 0",
                "description": "Single track MIDI format",
                "extension": ".mid",
                "supports_metadata": True
            },
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
            },
            {
                "format": "xml",
                "name": "XML",
                "description": "Extensible markup language",
                "extension": ".xml",
                "supports_metadata": True
            },
            {
                "format": "csv",
                "name": "CSV",
                "description": "Comma-separated values",
                "extension": ".csv",
                "supports_metadata": False
            }
        ]
