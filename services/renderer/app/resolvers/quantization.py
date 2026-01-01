"""Quantization resolver for converting continuous time to discrete note durations."""

from typing import Any, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class QuantizationResolver:
    """
    Resolve timing ambiguities and quantize to standard note values.

    The IR preserves continuous time, but MusicXML requires discrete durations.
    This resolver commits to specific rhythmic interpretations.
    """

    def __init__(self, tolerance: float = 0.05, min_duration: float = 0.0625):
        """
        Args:
            tolerance: Tolerance in beats for quantization (e.g., 0.05 = 1/20 beat)
            min_duration: Minimum note duration in beats (e.g., 0.0625 = 1/16)
        """
        self.tolerance = tolerance
        self.min_duration = min_duration

        # Standard note durations (in beats, assuming quarter = 1 beat)
        self.standard_durations = [
            4.0,  # whole
            3.0,  # dotted half
            2.0,  # half
            1.5,  # dotted quarter
            1.0,  # quarter
            0.75,  # dotted eighth
            0.5,  # eighth
            0.375,  # dotted sixteenth
            0.25,  # sixteenth
            0.125,  # thirty-second
            0.0625,  # sixty-fourth
        ]

    def quantize_notes(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Quantize note durations and onset times to standard values.

        Args:
            notes: List of notes with continuous time values

        Returns:
            List of notes with quantized times
        """
        logger.info(f"Quantizing {len(notes)} notes")

        quantized_notes = []

        for note in notes:
            quantized_note = note.copy()

            # Quantize onset time
            onset_beats = note["time"]["absolute_beat"]
            quantized_onset = self._quantize_value(onset_beats)

            # Quantize duration
            duration_beats = note["duration"]["duration_beats"]
            quantized_duration = self._quantize_duration(duration_beats)

            # Update note
            quantized_note["quantized_onset_beats"] = quantized_onset
            quantized_note["quantized_duration_beats"] = quantized_duration
            quantized_note["quantized_note_type"] = self._duration_to_note_type(quantized_duration)

            # Calculate quantization error for quality metrics
            onset_error = abs(onset_beats - quantized_onset)
            duration_error = abs(duration_beats - quantized_duration)
            quantized_note["quantization_error"] = {
                "onset": onset_error,
                "duration": duration_error,
                "total": onset_error + duration_error,
            }

            quantized_notes.append(quantized_note)

        total_error = sum(n["quantization_error"]["total"] for n in quantized_notes)
        avg_error = total_error / len(quantized_notes) if quantized_notes else 0.0

        logger.info(f"Quantization complete. Average error: {avg_error:.4f} beats")

        return quantized_notes

    def _quantize_value(self, value: float) -> float:
        """
        Quantize a time value to the nearest standard grid point.

        Uses a grid based on the smallest standard duration.
        """
        grid_size = self.min_duration
        return round(value / grid_size) * grid_size

    def _quantize_duration(self, duration: float) -> float:
        """
        Quantize duration to nearest standard note value.
        """
        if duration < self.min_duration:
            return self.min_duration

        # Find closest standard duration
        closest = min(self.standard_durations, key=lambda x: abs(x - duration))

        # If within tolerance, use standard duration
        if abs(closest - duration) <= self.tolerance:
            return closest

        # Otherwise, quantize to grid
        return self._quantize_value(duration)

    def _duration_to_note_type(self, duration: float) -> Tuple[str, int]:
        """
        Convert duration in beats to MusicXML note type and dots.

        Returns:
            (note_type, dots) e.g., ("quarter", 0) or ("eighth", 1)
        """
        # Check for dotted notes
        for base_duration in [4.0, 2.0, 1.0, 0.5, 0.25, 0.125, 0.0625]:
            dotted = base_duration * 1.5
            if abs(duration - dotted) < 0.001:
                note_type = self._duration_to_type_name(base_duration)
                return (note_type, 1)

        # Check for regular notes
        note_type = self._duration_to_type_name(duration)
        return (note_type, 0)

    def _duration_to_type_name(self, duration: float) -> str:
        """Map duration to note type name."""
        mapping = {
            4.0: "whole",
            2.0: "half",
            1.0: "quarter",
            0.5: "eighth",
            0.25: "16th",
            0.125: "32nd",
            0.0625: "64th",
        }
        return mapping.get(duration, "quarter")

