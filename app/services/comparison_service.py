"""
Advanced MIDI comparison and analysis service.
"""

import os
import numpy as np
import pretty_midi
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class ComparisonType(Enum):
    """Types of MIDI comparisons."""
    NOTE_ACCURACY = "note_accuracy"
    TIMING_ACCURACY = "timing_accuracy"
    RHYTHM_ACCURACY = "rhythm_accuracy"
    VELOCITY_ACCURACY = "velocity_accuracy"
    OVERALL_QUALITY = "overall_quality"


@dataclass
class NoteMatch:
    """Represents a matched note between two MIDI files."""
    generated_note: pretty_midi.Note
    reference_note: pretty_midi.Note
    timing_error: float  # Time difference in seconds
    pitch_error: int     # Pitch difference in semitones
    velocity_error: int  # Velocity difference
    match_quality: float  # 0.0 to 1.0


@dataclass
class ComparisonResult:
    """Result of MIDI file comparison."""
    overall_score: float
    note_accuracy: float
    timing_accuracy: float
    rhythm_accuracy: float
    velocity_accuracy: float
    note_matches: List[NoteMatch]
    unmatched_generated: List[pretty_midi.Note]
    unmatched_reference: List[pretty_midi.Note]
    detailed_metrics: Dict[str, Any]


class ComparisonService:
    """Service for advanced MIDI file comparison and analysis."""

    # Configuration constants
    TIMING_TOLERANCE = 0.1  # 100ms tolerance for note timing
    PITCH_TOLERANCE = 0     # Exact pitch matching
    VELOCITY_TOLERANCE = 10  # Velocity tolerance

    @staticmethod
    def compare_midi_files(
        generated_midi_path: str,
        reference_midi_path: str,
        comparison_types: List[ComparisonType] = None
    ) -> ComparisonResult:
        """
        Comprehensive comparison of two MIDI files.

        Args:
            generated_midi_path: Path to generated MIDI file
            reference_midi_path: Path to reference MIDI file
            comparison_types: Types of comparison to perform

        Returns:
            Detailed comparison result
        """
        if comparison_types is None:
            comparison_types = list(ComparisonType)

        # Load MIDI files
        generated_midi = pretty_midi.PrettyMIDI(generated_midi_path)
        reference_midi = pretty_midi.PrettyMIDI(reference_midi_path)

        # Extract all notes
        generated_notes = []
        reference_notes = []

        for instrument in generated_midi.instruments:
            generated_notes.extend(instrument.notes)

        for instrument in reference_midi.instruments:
            reference_notes.extend(instrument.notes)

        # Sort notes by start time
        generated_notes.sort(key=lambda x: x.start)
        reference_notes.sort(key=lambda x: x.start)

        # Perform note-by-note matching
        note_matches, unmatched_generated, unmatched_reference = \
            ComparisonService._match_notes(generated_notes, reference_notes)

        # Calculate various accuracy metrics
        metrics = {}

        if ComparisonType.NOTE_ACCURACY in comparison_types:
            metrics['note_accuracy'] = ComparisonService._calculate_note_accuracy(
                note_matches, len(generated_notes), len(reference_notes)
            )

        if ComparisonType.TIMING_ACCURACY in comparison_types:
            metrics['timing_accuracy'] = ComparisonService._calculate_timing_accuracy(
                note_matches
            )

        if ComparisonType.RHYTHM_ACCURACY in comparison_types:
            metrics['rhythm_accuracy'] = ComparisonService._calculate_rhythm_accuracy(
                note_matches, generated_midi, reference_midi
            )

        if ComparisonType.VELOCITY_ACCURACY in comparison_types:
            metrics['velocity_accuracy'] = ComparisonService._calculate_velocity_accuracy(
                note_matches
            )

        # Calculate overall quality score
        overall_score = ComparisonService._calculate_overall_score(metrics)

        return ComparisonResult(
            overall_score=overall_score,
            note_accuracy=metrics.get('note_accuracy', 0.0),
            timing_accuracy=metrics.get('timing_accuracy', 0.0),
            rhythm_accuracy=metrics.get('rhythm_accuracy', 0.0),
            velocity_accuracy=metrics.get('velocity_accuracy', 0.0),
            note_matches=note_matches,
            unmatched_generated=unmatched_generated,
            unmatched_reference=unmatched_reference,
            detailed_metrics=metrics
        )

    @staticmethod
    def _match_notes(
        generated_notes: List[pretty_midi.Note],
        reference_notes: List[pretty_midi.Note]
    ) -> Tuple[List[NoteMatch], List[pretty_midi.Note], List[pretty_midi.Note]]:
        """
        Match notes between generated and reference MIDI files.

        Args:
            generated_notes: Notes from generated MIDI
            reference_notes: Notes from reference MIDI

        Returns:
            Tuple of (matched notes, unmatched generated, unmatched reference)
        """
        note_matches = []
        unmatched_generated = generated_notes.copy()
        unmatched_reference = reference_notes.copy()

        # Create a matrix of distances between all notes
        for gen_note in generated_notes:
            best_match = None
            best_distance = float('inf')

            for ref_note in unmatched_reference:
                # Calculate distance based on timing and pitch
                timing_distance = abs(gen_note.start - ref_note.start)
                pitch_distance = abs(gen_note.pitch - ref_note.pitch)

                # Combined distance (weighted)
                distance = timing_distance * 2.0 + pitch_distance * 0.1

                if distance < best_distance and \
                   timing_distance <= ComparisonService.TIMING_TOLERANCE and \
                   pitch_distance <= ComparisonService.PITCH_TOLERANCE:
                    best_distance = distance
                    best_match = ref_note

            if best_match:
                # Create note match
                timing_error = abs(gen_note.start - best_match.start)
                pitch_error = abs(gen_note.pitch - best_match.pitch)
                velocity_error = abs(gen_note.velocity - best_match.velocity)

                # Calculate match quality (0.0 to 1.0)
                timing_quality = max(0, 1 - timing_error /
                                     ComparisonService.TIMING_TOLERANCE)
                pitch_quality = 1.0 if pitch_error == 0 else 0.0
                velocity_quality = max(0, 1 - velocity_error / 127)

                match_quality = (timing_quality * 0.6 + pitch_quality *
                                 0.3 + velocity_quality * 0.1)

                note_match = NoteMatch(
                    generated_note=gen_note,
                    reference_note=best_match,
                    timing_error=timing_error,
                    pitch_error=pitch_error,
                    velocity_error=velocity_error,
                    match_quality=match_quality
                )

                note_matches.append(note_match)
                unmatched_generated.remove(gen_note)
                unmatched_reference.remove(best_match)

        return note_matches, unmatched_generated, unmatched_reference

    @staticmethod
    def _calculate_note_accuracy(
        note_matches: List[NoteMatch],
        total_generated: int,
        total_reference: int
    ) -> float:
        """Calculate note accuracy score."""
        if total_generated == 0 and total_reference == 0:
            return 1.0

        if total_generated == 0 or total_reference == 0:
            return 0.0

        # Precision: correctly identified notes / total generated notes
        precision = len(note_matches) / total_generated

        # Recall: correctly identified notes / total reference notes
        recall = len(note_matches) / total_reference

        # F1 score
        if precision + recall == 0:
            return 0.0

        return 2 * (precision * recall) / (precision + recall)

    @staticmethod
    def _calculate_timing_accuracy(note_matches: List[NoteMatch]) -> float:
        """Calculate timing accuracy score."""
        if not note_matches:
            return 0.0

        # Calculate average timing error
        total_error = sum(match.timing_error for match in note_matches)
        avg_error = total_error / len(note_matches)

        # Convert to accuracy score (0.0 to 1.0)
        # Perfect timing = 1.0, error > tolerance = 0.0
        accuracy = max(0, 1 - avg_error / ComparisonService.TIMING_TOLERANCE)
        return accuracy

    @staticmethod
    def _calculate_rhythm_accuracy(
        note_matches: List[NoteMatch],
        generated_midi: pretty_midi.PrettyMIDI,
        reference_midi: pretty_midi.PrettyMIDI
    ) -> float:
        """Calculate rhythm accuracy score."""
        if not note_matches:
            return 0.0

        # Extract onset times
        generated_onsets = [match.generated_note.start for match in note_matches]
        reference_onsets = [match.reference_note.start for match in note_matches]

        # Calculate inter-onset intervals
        generated_ioi = np.diff(generated_onsets)
        reference_ioi = np.diff(reference_onsets)

        if len(generated_ioi) == 0 or len(reference_ioi) == 0:
            return 0.0

        # Calculate correlation between IOI patterns
        min_length = min(len(generated_ioi), len(reference_ioi))
        if min_length < 2:
            return 0.0

        generated_ioi = generated_ioi[:min_length]
        reference_ioi = reference_ioi[:min_length]

        # Normalize IOI patterns
        generated_ioi_norm = (generated_ioi - np.mean(generated_ioi)
                              ) / (np.std(generated_ioi) + 1e-8)
        reference_ioi_norm = (reference_ioi - np.mean(reference_ioi)
                              ) / (np.std(reference_ioi) + 1e-8)

        # Calculate correlation
        correlation = np.corrcoef(generated_ioi_norm, reference_ioi_norm)[0, 1]

        # Convert correlation to accuracy score
        return max(0, correlation) if not np.isnan(correlation) else 0.0

    @staticmethod
    def _calculate_velocity_accuracy(note_matches: List[NoteMatch]) -> float:
        """Calculate velocity accuracy score."""
        if not note_matches:
            return 0.0

        # Calculate average velocity error
        total_error = sum(match.velocity_error for match in note_matches)
        avg_error = total_error / len(note_matches)

        # Convert to accuracy score (0.0 to 1.0)
        # Perfect velocity = 1.0, max error = 0.0
        accuracy = max(0, 1 - avg_error / 127)
        return accuracy

    @staticmethod
    def _calculate_overall_score(metrics: Dict[str, float]) -> float:
        """Calculate overall quality score."""
        if not metrics:
            return 0.0

        # Weighted average of all metrics
        weights = {
            'note_accuracy': 0.4,
            'timing_accuracy': 0.3,
            'rhythm_accuracy': 0.2,
            'velocity_accuracy': 0.1
        }

        total_score = 0.0
        total_weight = 0.0

        for metric, weight in weights.items():
            if metric in metrics:
                total_score += metrics[metric] * weight
                total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    @staticmethod
    def analyze_note_distribution(midi_path: str) -> Dict[str, Any]:
        """
        Analyze note distribution in a MIDI file.

        Args:
            midi_path: Path to MIDI file

        Returns:
            Note distribution analysis
        """
        midi = pretty_midi.PrettyMIDI(midi_path)

        all_notes = []
        for instrument in midi.instruments:
            all_notes.extend(instrument.notes)

        if not all_notes:
            return {"error": "No notes found in MIDI file"}

        # Extract note properties
        pitches = [note.pitch for note in all_notes]
        velocities = [note.velocity for note in all_notes]
        durations = [note.end - note.start for note in all_notes]
        start_times = [note.start for note in all_notes]

        # Calculate statistics
        analysis = {
            "total_notes": len(all_notes),
            "duration": midi.get_end_time(),
            "pitch_range": {
                "min": min(pitches),
                "max": max(pitches),
                "mean": np.mean(pitches),
                "std": np.std(pitches)
            },
            "velocity_stats": {
                "min": min(velocities),
                "max": max(velocities),
                "mean": np.mean(velocities),
                "std": np.std(velocities)
            },
            "duration_stats": {
                "min": min(durations),
                "max": max(durations),
                "mean": np.mean(durations),
                "std": np.std(durations)
            },
            "note_density": len(all_notes) / midi.get_end_time() if midi.get_end_time() > 0 else 0,
            "pitch_histogram": np.histogram(pitches, bins=12, range=(0, 127))[0].tolist(),
            "velocity_histogram": np.histogram(velocities, bins=10, range=(0, 127))[0].tolist()
        }

        return analysis

    @staticmethod
    def generate_comparison_report(
        comparison_result: ComparisonResult,
        generated_midi_path: str,
        reference_midi_path: str
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive comparison report.

        Args:
            comparison_result: Result of MIDI comparison
            generated_midi_path: Path to generated MIDI
            reference_midi_path: Path to reference MIDI

        Returns:
            Detailed comparison report
        """
        # Analyze individual files
        generated_analysis = ComparisonService.analyze_note_distribution(
            generated_midi_path)
        reference_analysis = ComparisonService.analyze_note_distribution(
            reference_midi_path)

        # Calculate additional metrics
        total_generated = len(comparison_result.note_matches) + \
            len(comparison_result.unmatched_generated)
        total_reference = len(comparison_result.note_matches) + \
            len(comparison_result.unmatched_reference)

        precision = len(comparison_result.note_matches) / \
            total_generated if total_generated > 0 else 0
        recall = len(comparison_result.note_matches) / \
            total_reference if total_reference > 0 else 0

        report = {
            "comparison_summary": {
                "overall_score": round(comparison_result.overall_score, 3),
                "note_accuracy": round(comparison_result.note_accuracy, 3),
                "timing_accuracy": round(comparison_result.timing_accuracy, 3),
                "rhythm_accuracy": round(comparison_result.rhythm_accuracy, 3),
                "velocity_accuracy": round(comparison_result.velocity_accuracy, 3)
            },
            "detailed_metrics": {
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1_score": round(comparison_result.note_accuracy, 3),
                "matched_notes": len(comparison_result.note_matches),
                "unmatched_generated": len(comparison_result.unmatched_generated),
                "unmatched_reference": len(comparison_result.unmatched_reference),
                "total_generated": total_generated,
                "total_reference": total_reference
            },
            "file_analysis": {
                "generated": generated_analysis,
                "reference": reference_analysis
            },
            "note_matches": [
                {
                    "generated_note": {
                        "pitch": match.generated_note.pitch,
                        "start": match.generated_note.start,
                        "end": match.generated_note.end,
                        "velocity": match.generated_note.velocity
                    },
                    "reference_note": {
                        "pitch": match.reference_note.pitch,
                        "start": match.reference_note.start,
                        "end": match.reference_note.end,
                        "velocity": match.reference_note.velocity
                    },
                    "errors": {
                        "timing_error": round(match.timing_error, 3),
                        "pitch_error": match.pitch_error,
                        "velocity_error": match.velocity_error
                    },
                    "match_quality": round(match.match_quality, 3)
                }
                for match in comparison_result.note_matches
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

        return report
