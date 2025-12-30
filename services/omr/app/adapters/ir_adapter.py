"""Adapter to convert OMR model predictions into Symbolic Score IR v1."""

import logging
from datetime import datetime
from fractions import Fraction
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class OMRToIRAdapter:
    """
    Adapter to convert OMR model predictions into Symbolic Score IR v1.

    This is a critical component that bridges perception (OMR) and
    symbolic reasoning (IR).

    Responsibilities:
    - Map OMR detections to IR note events
    - Create dual time representation (seconds + beats)
    - Preserve confidence scores
    - Handle uncertainty in voice/hand assignment
    - Generate chord groupings
    """

    def __init__(
        self,
        source_pdf_artifact_id: str,
        model_name: str,
        model_version: str,
    ):
        self.source_pdf_artifact_id = source_pdf_artifact_id
        self.model_name = model_name
        self.model_version = model_version

    def convert(
        self,
        omr_predictions: List[Dict[str, Any]],
        pdf_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert multi-page OMR predictions to complete Symbolic IR v1.

        Args:
            omr_predictions: List of per-page predictions from OMR model
            pdf_filename: Original PDF filename (for metadata)

        Returns:
            Complete Symbolic IR v1 as dictionary (ready for Pydantic validation)
        """
        logger.info(f"Converting {len(omr_predictions)} pages to IR v1")

        # Extract global musical context from first page
        first_page = omr_predictions[0]
        time_signature = self._extract_time_signature(first_page)
        key_signature = self._extract_key_signature(first_page)
        tempo = self._extract_tempo(first_page)

        # Extract staves configuration
        staves = self._extract_staves(omr_predictions)

        # Convert all notes from all pages
        all_notes = []
        all_chords = []
        current_time_offset = 0.0
        current_measure = 1

        for page_idx, page_pred in enumerate(omr_predictions):
            page_notes, page_chords, time_advance, measure_advance = (
                self._convert_page(
                    page_pred,
                    page_idx + 1,
                    current_time_offset,
                    current_measure,
                    time_signature,
                    tempo,
                )
            )

            all_notes.extend(page_notes)
            all_chords.extend(page_chords)
            current_time_offset += time_advance
            current_measure += measure_advance

        # Extract voices from notes
        voices = self._extract_voices(all_notes, staves)

        # Build metadata
        metadata = self._build_metadata(
            pdf_filename, len(omr_predictions), all_notes, len(all_chords)
        )

        # Assemble complete IR
        ir_data = {
            "version": "1.0.0",
            "schema_type": "symbolic_score_ir",
            "metadata": metadata,
            "time_signature": time_signature,
            "key_signature": key_signature,
            "tempo": tempo,
            "staves": staves,
            "notes": all_notes,
            "chords": all_chords,
            "voices": voices,
        }

        logger.info(
            f"IR conversion complete: {len(all_notes)} notes, "
            f"{len(all_chords)} chords, {len(voices)} voices"
        )

        return ir_data

    def _extract_time_signature(self, page_pred: Dict) -> Dict[str, Any]:
        """Extract time signature from OMR predictions."""
        ts = page_pred.get("time_signature", {"numerator": 4, "denominator": 4})
        return {
            "numerator": ts["numerator"],
            "denominator": ts["denominator"],
            "changes": [],
        }

    def _extract_key_signature(self, page_pred: Dict) -> Dict[str, Any]:
        """Extract key signature from OMR predictions."""
        ks = page_pred.get("key_signature", {"fifths": 0, "mode": "major"})
        return {
            "fifths": ks.get("fifths", 0),
            "mode": ks.get("mode", "major"),
        }

    def _extract_tempo(self, page_pred: Dict) -> Dict[str, Any]:
        """Extract tempo from OMR predictions."""
        tempo = page_pred.get("tempo", {"bpm": 120})
        return {
            "bpm": tempo.get("bpm", 120),
            "beat_unit": "quarter",
            "changes": [],
        }

    def _extract_staves(self, omr_predictions: List[Dict]) -> List[Dict[str, Any]]:
        """Extract staff configuration."""
        # Use first page's staves as template
        omr_staves = omr_predictions[0].get("staves", [])

        staves = []
        for omr_staff in omr_staves:
            staff = {
                "staff_id": f"staff_{omr_staff['staff_id']}",
                "clef": omr_staff.get("clef", "treble"),
                "part_name": omr_staff.get("part_name", None),
            }
            staves.append(staff)

        # Default to piano staves if none found
        if not staves:
            staves = [
                {
                    "staff_id": "staff_0",
                    "clef": "treble",
                    "part_name": "Piano Right Hand",
                },
                {"staff_id": "staff_1", "clef": "bass", "part_name": "Piano Left Hand"},
            ]

        return staves

    def _convert_page(
        self,
        page_pred: Dict,
        page_number: int,
        time_offset: float,
        measure_offset: int,
        time_signature: Dict,
        tempo: Dict,
    ) -> tuple:
        """
        Convert a single page's predictions to IR notes and chords.

        Returns:
            (notes, chords, time_advance, measure_advance)
        """
        omr_notes = page_pred.get("notes", [])

        notes = []
        chord_groups = {}  # Group simultaneous notes

        for omr_note in omr_notes:
            # Generate unique note ID
            note_id = f"note_{uuid4().hex[:12]}"

            # Convert to IR note event
            ir_note = self._convert_note(
                omr_note,
                note_id,
                page_number,
                time_offset,
                measure_offset,
                time_signature,
                tempo,
            )

            notes.append(ir_note)

            # Group by onset time for chord detection
            onset_key = round(ir_note["time"]["onset_seconds"], 3)
            if onset_key not in chord_groups:
                chord_groups[onset_key] = []
            chord_groups[onset_key].append(note_id)

        # Create chord groupings for simultaneous notes
        chords = []
        for onset_time, note_ids in chord_groups.items():
            if len(note_ids) > 1:  # Only create chord if multiple notes
                chord_id = f"chord_{uuid4().hex[:12]}"
                # Find representative note for timing
                rep_note = next(n for n in notes if n["note_id"] in note_ids)

                chord = {
                    "chord_id": chord_id,
                    "note_ids": note_ids,
                    "time": rep_note["time"],
                    "root": None,  # To be filled by future analysis
                    "chord_type": None,
                    "confidence": min(
                        n["confidence"]["overall"]
                        for n in notes
                        if n["note_id"] in note_ids
                    ),
                }
                chords.append(chord)

                # Update note chord memberships
                for note in notes:
                    if note["note_id"] in note_ids:
                        note["chord_membership"] = {
                            "chord_id": chord_id,
                            "confidence": 0.9,  # High confidence for simultaneous notes
                            "chord_position": None,
                        }

        # Calculate page duration (for next page's offset)
        max_time = (
            max(
                (n["time"]["onset_seconds"] + n["duration"]["duration_seconds"])
                for n in notes
            )
            if notes
            else 0.0
        )
        time_advance = max_time

        # Calculate measure advance
        max_measure = max(n["time"]["measure"] for n in notes) if notes else 0
        measure_advance = max_measure - measure_offset

        return notes, chords, time_advance, measure_advance

    def _convert_note(
        self,
        omr_note: Dict,
        note_id: str,
        page_number: int,
        time_offset: float,
        measure_offset: int,
        time_signature: Dict,
        tempo: Dict,
    ) -> Dict[str, Any]:
        """Convert a single OMR note detection to IR note event."""
        # Extract pitch
        pitch_data = omr_note["pitch"]
        midi_note = pitch_data.get("midi", 60)
        pitch_name = pitch_data.get("name", "C4")

        # Parse pitch name (e.g., "C4", "F#5")
        pitch_class = pitch_name[0] if len(pitch_name) > 0 else "C"
        if len(pitch_name) > 1 and pitch_name[1] in ["#", "b"]:
            pitch_class = pitch_name[:2]
            octave_str = pitch_name[2:] if len(pitch_name) > 2 else "4"
        else:
            octave_str = pitch_name[1:] if len(pitch_name) > 1 else "4"

        octave = int(octave_str) if octave_str.isdigit() else 4

        pitch = {
            "midi_note": midi_note,
            "pitch_class": pitch_class,
            "octave": octave,
            "scientific_notation": pitch_name,
            "frequency_hz": self._midi_to_freq(midi_note),
            "accidental": None,  # OMR should provide this if available
        }

        # Extract temporal information
        onset_seconds = time_offset + omr_note.get("onset_time", 0.0)
        duration_seconds = omr_note.get("duration", 0.5)

        # Calculate metric time
        beats_per_second = tempo["bpm"] / 60.0
        onset_beats = onset_seconds * beats_per_second
        duration_beats = duration_seconds * beats_per_second

        # Calculate measure and beat
        beats_per_measure = time_signature["numerator"] * (
            4 / time_signature["denominator"]
        )
        measure = measure_offset + int(onset_beats // beats_per_measure)
        beat_in_measure = onset_beats % beats_per_measure

        time = {
            "onset_seconds": onset_seconds,
            "measure": measure,
            "beat": beat_in_measure,
            "beat_fraction": f"{int(beat_in_measure * 1000)}/1000",
            "absolute_beat": onset_beats,
            "quantization_confidence": omr_note.get("confidence", 0.8),
        }

        duration = {
            "duration_seconds": duration_seconds,
            "duration_beats": duration_beats,
            "duration_fraction": f"{int(duration_beats * 1000)}/1000",
            "note_type": self._infer_note_type(duration_beats),
            "dots": 0,
            "is_tuplet": False,
            "tuplet_ratio": None,
        }

        # Extract spatial information
        pos = omr_note.get("position", {"x": 0, "y": 0})
        staff_id = omr_note.get("staff", 0)

        spatial = {
            "staff_id": f"staff_{staff_id}",
            "staff_position": self._calculate_staff_position(pos.get("y", 0)),
            "page_number": page_number,
            "bounding_box": {
                "x": pos.get("x", 0),
                "y": pos.get("y", 0),
                "width": 20,  # Placeholder - OMR should provide actual bbox
                "height": 20,
                "coordinate_system": "pixels",
            },
            "staff_assignment_confidence": omr_note.get("confidence", 0.8),
        }

        # Voice and hand assignment (probabilistic)
        # OMR may not provide this - use heuristics or leave uncertain
        voice_assignment = self._infer_voice_assignment(pitch, staff_id)
        hand_assignment = self._infer_hand_assignment(pitch, staff_id)

        # Confidence scores
        base_confidence = omr_note.get("confidence", 0.8)
        confidence = {
            "detection": base_confidence,
            "pitch": base_confidence * 0.95,
            "onset_time": base_confidence * 0.9,
            "duration": base_confidence * 0.85,
            "voice": 0.6,  # Lower confidence for inferred attributes
            "hand": 0.7,
            "chord_membership": 0.8,
            "overall": base_confidence * 0.9,
        }

        return {
            "note_id": note_id,
            "pitch": pitch,
            "time": time,
            "duration": duration,
            "spatial": spatial,
            "articulation": None,
            "dynamics": None,
            "chord_membership": None,  # Filled later during chord grouping
            "voice_assignment": voice_assignment,
            "hand_assignment": hand_assignment,
            "is_grace_note": False,
            "is_tied_from_previous": False,
            "is_tied_to_next": False,
            "confidence": confidence,
        }

    def _midi_to_freq(self, midi_note: int) -> float:
        """Convert MIDI note number to frequency in Hz."""
        return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

    def _infer_note_type(self, duration_beats: float) -> str:
        """Infer note type from beat duration."""
        # Simple quantization - can be improved
        if duration_beats >= 3.5:
            return "whole"
        elif duration_beats >= 1.5:
            return "half"
        elif duration_beats >= 0.75:
            return "quarter"
        elif duration_beats >= 0.375:
            return "eighth"
        elif duration_beats >= 0.1875:
            return "16th"
        else:
            return "32nd"

    def _calculate_staff_position(self, y_pixel: float) -> float:
        """Calculate staff-relative position from pixel y-coordinate."""
        # Placeholder - actual calculation depends on staff detection
        # Middle line of staff = 0, each line/space = 1 unit
        return 0.0  # Simplified

    def _infer_voice_assignment(self, pitch: Dict, staff_id: int) -> Dict[str, Any]:
        """Infer voice assignment with low confidence (OMR typically doesn't provide this)."""
        # Simple heuristic: use pitch register
        midi = pitch["midi_note"]
        voice_id = f"voice_{staff_id}_{'high' if midi >= 60 else 'low'}"

        return {
            "voice_id": voice_id,
            "confidence": 0.5,  # Low confidence for inferred voice
            "alternatives": [],
        }

    def _infer_hand_assignment(self, pitch: Dict, staff_id: int) -> Dict[str, Any]:
        """Infer hand assignment based on staff and pitch."""
        # For piano: staff 0 = right hand, staff 1 = left hand
        hand = "right" if staff_id == 0 else "left"

        # But allow crossover based on pitch
        midi = pitch["midi_note"]
        confidence = 0.8

        # Lower confidence if pitch suggests crossover
        alternatives = []
        if staff_id == 0 and midi < 60:  # Right hand staff, low pitch
            alternatives.append({"hand": "left", "confidence": 0.3})
            confidence = 0.6
        elif staff_id == 1 and midi > 60:  # Left hand staff, high pitch
            alternatives.append({"hand": "right", "confidence": 0.3})
            confidence = 0.6

        return {
            "hand": hand,
            "confidence": confidence,
            "alternatives": alternatives,
        }

    def _extract_voices(
        self, notes: List[Dict], staves: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Extract voice structure from notes."""
        voice_notes = {}

        for note in notes:
            if note.get("voice_assignment"):
                voice_id = note["voice_assignment"]["voice_id"]
                if voice_id not in voice_notes:
                    voice_notes[voice_id] = []
                voice_notes[voice_id].append(note["note_id"])

        voices = []
        for voice_id, note_ids in voice_notes.items():
            # Determine staff for this voice
            staff_id = "staff_0"  # Default
            for note in notes:
                if note["note_id"] in note_ids:
                    staff_id = note["spatial"]["staff_id"]
                    break

            voices.append(
                {
                    "voice_id": voice_id,
                    "staff_id": staff_id,
                    "note_ids": sorted(note_ids),  # Sort by appearance
                }
            )

        return voices

    def _build_metadata(
        self,
        pdf_filename: Optional[str],
        page_count: int,
        notes: List[Dict],
        chord_count: int,
    ) -> Dict[str, Any]:
        """Build IR metadata."""
        # Calculate statistics
        note_count = len(notes)
        confidences = [n["confidence"]["overall"] for n in notes]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Find low confidence regions
        low_conf_regions = []
        # Group by measure and find low-confidence measures
        measure_confidences = {}
        for note in notes:
            measure = note["time"]["measure"]
            if measure not in measure_confidences:
                measure_confidences[measure] = []
            measure_confidences[measure].append(note["confidence"]["overall"])

        for measure, confs in measure_confidences.items():
            avg_measure_conf = sum(confs) / len(confs)
            if avg_measure_conf < 0.6:
                low_conf_regions.append(
                    {
                        "start_measure": measure,
                        "end_measure": measure,
                        "average_confidence": avg_measure_conf,
                        "reason": "Low OMR detection confidence",
                    }
                )

        # Estimate duration
        if notes:
            last_note = max(
                notes,
                key=lambda n: n["time"]["onset_seconds"]
                + n["duration"]["duration_seconds"],
            )
            estimated_duration = (
                last_note["time"]["onset_seconds"]
                + last_note["duration"]["duration_seconds"]
            )
        else:
            estimated_duration = 0.0

        # Count unique voices
        voice_ids = set()
        for note in notes:
            if note.get("voice_assignment"):
                voice_ids.add(note["voice_assignment"]["voice_id"])
        voice_count = len(voice_ids) if voice_ids else 1

        return {
            "title": None,
            "composer": None,
            "opus": None,
            "movement": None,
            "copyright": None,
            "source_pdf_artifact_id": self.source_pdf_artifact_id,
            "source_filename": pdf_filename,
            "generated_by": {
                "service": "omr-service",
                "model": self.model_name,
                "model_version": self.model_version,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "processing_time_seconds": None,  # Set by caller
                "config": {},
            },
            "page_count": page_count,
            "estimated_duration_seconds": estimated_duration,
            "total_measures": max((n["time"]["measure"] for n in notes), default=0),
            "note_count": note_count,
            "chord_count": chord_count,
            "voice_count": voice_count,
            "average_detection_confidence": avg_confidence,
            "low_confidence_regions": low_conf_regions,
        }

