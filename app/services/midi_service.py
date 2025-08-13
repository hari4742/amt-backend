"""
MIDI generation service for audio-to-MIDI conversion and processing.
"""

import os
import numpy as np
import pretty_midi
import librosa
from typing import List, Dict, Any, Tuple, Optional
from app.config import settings


class MIDIService:
    """Service for MIDI generation and processing."""

    @staticmethod
    def extract_notes_from_audio(
        audio_data: np.ndarray,
        sample_rate: int,
        quality: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Extract musical notes from audio data.

        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of the audio
            quality: Quality level for note detection

        Returns:
            List of detected notes with timing information
        """
        # Extract pitch information
        pitches, magnitudes = librosa.piptrack(
            y=audio_data,
            sr=sample_rate,
            hop_length=512,
            threshold=0.1
        )

        # Get onset times
        onset_frames = librosa.onset.onset_detect(
            y=audio_data,
            sr=sample_rate,
            hop_length=512,
            units='frames'
        )
        onset_times = librosa.frames_to_time(
            onset_frames, sr=sample_rate, hop_length=512)

        # Extract notes based on quality settings
        notes = []
        time_step = 512 / sample_rate  # Time per frame

        # Quality-based thresholds
        if quality == "high":
            pitch_threshold = 0.05
            min_note_duration = 0.1
        elif quality == "low":
            pitch_threshold = 0.2
            min_note_duration = 0.2
        else:  # medium
            pitch_threshold = 0.1
            min_note_duration = 0.15

        # Process each time frame
        for t in range(pitches.shape[1]):
            # Find the strongest pitch at this time
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            magnitude = magnitudes[index, t]

            if pitch > 0 and magnitude > pitch_threshold:
                # Convert frequency to MIDI note number
                midi_note = int(round(12 * np.log2(pitch / 440) + 69))

                # Ensure note is in valid MIDI range
                if 21 <= midi_note <= 108:  # Piano range
                    # Calculate note timing
                    start_time = t * time_step

                    # Find note end time (simplified - in practice, you'd want more sophisticated note tracking)
                    end_time = start_time + min_note_duration

                    # Check if this is a new note (not overlapping with previous)
                    is_new_note = True
                    for note in notes:
                        if (note['midi_note'] == midi_note and
                                abs(note['start_time'] - start_time) < 0.1):
                            is_new_note = False
                            break

                    if is_new_note:
                        notes.append({
                            'midi_note': midi_note,
                            'start_time': start_time,
                            'end_time': end_time,
                            'velocity': int(min(127, magnitude * 100)),
                            'frequency': pitch
                        })

        return notes

    @staticmethod
    def create_midi_from_notes(
        notes: List[Dict[str, Any]],
        output_path: str,
        tempo: float = 120.0
    ) -> pretty_midi.PrettyMIDI:
        """
        Create MIDI file from extracted notes.

        Args:
            notes: List of note dictionaries
            output_path: Output MIDI file path
            tempo: Tempo in BPM

        Returns:
            PrettyMIDI object
        """
        # Create MIDI object
        midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)

        # Create piano program
        piano_program = pretty_midi.Instrument(
            program=0,  # Acoustic Grand Piano
            name='Piano'
        )

        # Add notes to the piano track
        for note_data in notes:
            note = pretty_midi.Note(
                velocity=note_data['velocity'],
                pitch=note_data['midi_note'],
                start=note_data['start_time'],
                end=note_data['end_time']
            )
            piano_program.notes.append(note)

        # Add piano to MIDI
        midi.instruments.append(piano_program)

        # Save MIDI file
        midi.write(output_path)

        return midi

    @staticmethod
    def generate_midi_from_audio(
        audio_data: np.ndarray,
        sample_rate: int,
        output_path: str,
        quality: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate MIDI file from audio data.

        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of the audio
            output_path: Output MIDI file path
            quality: Quality level for transcription

        Returns:
            Dictionary containing generation results and metadata
        """
        # Detect tempo
        tempo, _ = librosa.beat.beat_track(y=audio_data, sr=sample_rate)

        # Extract notes
        notes = MIDIService.extract_notes_from_audio(audio_data, sample_rate, quality)

        # Create MIDI file
        midi = MIDIService.create_midi_from_notes(notes, output_path, tempo)

        # Calculate quality metrics
        total_notes = len(notes)
        avg_velocity = np.mean([note['velocity'] for note in notes]) if notes else 0
        note_density = total_notes / \
            (len(audio_data) / sample_rate) if len(audio_data) > 0 else 0

        # Calculate confidence score (simplified)
        # Normalize by expected note density
        confidence_score = min(1.0, note_density / 10.0)

        results = {
            "midi_path": output_path,
            "total_notes": total_notes,
            "tempo": tempo,
            "avg_velocity": avg_velocity,
            "note_density": note_density,
            "confidence_score": confidence_score,
            "quality": quality,
            "duration": len(audio_data) / sample_rate
        }

        return results

    @staticmethod
    def validate_midi_file(midi_path: str) -> Tuple[bool, str]:
        """
        Validate generated MIDI file.

        Args:
            midi_path: Path to the MIDI file

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Load MIDI file
            midi = pretty_midi.PrettyMIDI(midi_path)

            # Check if file has any notes
            total_notes = sum(len(instrument.notes) for instrument in midi.instruments)
            if total_notes == 0:
                return False, "MIDI file contains no notes"

            # Check file duration
            if midi.get_end_time() < 0.5:  # Less than 0.5 seconds
                return False, "MIDI file is too short"

            # Check for reasonable note velocities
            for instrument in midi.instruments:
                for note in instrument.notes:
                    if note.velocity < 1 or note.velocity > 127:
                        return False, "MIDI file contains invalid note velocities"

            return True, "MIDI file is valid"

        except Exception as e:
            return False, f"Failed to validate MIDI file: {str(e)}"

    @staticmethod
    def get_midi_metadata(midi_path: str) -> Dict[str, Any]:
        """
        Extract metadata from MIDI file.

        Args:
            midi_path: Path to the MIDI file

        Returns:
            Dictionary containing MIDI metadata
        """
        try:
            midi = pretty_midi.PrettyMIDI(midi_path)

            # Count notes per instrument
            instrument_notes = {}
            for instrument in midi.instruments:
                instrument_notes[instrument.name] = len(instrument.notes)

            # Calculate note statistics
            all_notes = []
            for instrument in midi.instruments:
                all_notes.extend(instrument.notes)

            if all_notes:
                velocities = [note.velocity for note in all_notes]
                pitches = [note.pitch for note in all_notes]
                durations = [note.end - note.start for note in all_notes]

                metadata = {
                    "duration": midi.get_end_time(),
                    "tempo": midi.estimate_tempo(),
                    "total_notes": len(all_notes),
                    "instruments": list(instrument_notes.keys()),
                    "avg_velocity": np.mean(velocities),
                    "avg_pitch": np.mean(pitches),
                    "avg_duration": np.mean(durations),
                    "pitch_range": (min(pitches), max(pitches)) if pitches else (0, 0),
                    "velocity_range": (min(velocities), max(velocities)) if velocities else (0, 0)
                }
            else:
                metadata = {
                    "duration": midi.get_end_time(),
                    "tempo": midi.estimate_tempo(),
                    "total_notes": 0,
                    "instruments": [],
                    "avg_velocity": 0,
                    "avg_pitch": 0,
                    "avg_duration": 0,
                    "pitch_range": (0, 0),
                    "velocity_range": (0, 0)
                }

            return metadata

        except Exception as e:
            raise ValueError(f"Failed to extract MIDI metadata: {str(e)}")

    @staticmethod
    def compare_midi_files(midi_path_1: str, midi_path_2: str) -> Dict[str, Any]:
        """
        Compare two MIDI files and calculate similarity metrics.

        Args:
            midi_path_1: Path to first MIDI file
            midi_path_2: Path to second MIDI file

        Returns:
            Dictionary containing comparison metrics
        """
        try:
            midi_1 = pretty_midi.PrettyMIDI(midi_path_1)
            midi_2 = pretty_midi.PrettyMIDI(midi_path_2)

            # Extract all notes from both files
            notes_1 = []
            notes_2 = []

            for instrument in midi_1.instruments:
                notes_1.extend(instrument.notes)

            for instrument in midi_2.instruments:
                notes_2.extend(instrument.notes)

            # Calculate basic metrics
            duration_1 = midi_1.get_end_time()
            duration_2 = midi_2.get_end_time()

            # Calculate note timing accuracy (simplified)
            timing_accuracy = 0.0
            if notes_1 and notes_2:
                # This is a simplified comparison - in practice, you'd want more sophisticated alignment
                timing_accuracy = min(duration_1, duration_2) / \
                    max(duration_1, duration_2)

            comparison = {
                "duration_similarity": timing_accuracy,
                "notes_count_1": len(notes_1),
                "notes_count_2": len(notes_2),
                "notes_ratio": len(notes_1) / len(notes_2) if notes_2 else 0,
                "duration_1": duration_1,
                "duration_2": duration_2,
                "overall_similarity": timing_accuracy * 0.7 + (len(notes_1) / max(len(notes_1), len(notes_2))) * 0.3 if notes_1 and notes_2 else 0
            }

            return comparison

        except Exception as e:
            raise ValueError(f"Failed to compare MIDI files: {str(e)}")
