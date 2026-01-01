"""Voice resolver for assigning voices in polyphonic music."""

from typing import Any, Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class VoiceResolver:
    """
    Resolve voice assignments for polyphonic notation.

    Commits to specific voice assignments based on pitch, timing,
    and voice crossing penalties.
    """

    def __init__(self, max_voices: int = 4, crossing_penalty: float = 0.5):
        self.max_voices = max_voices
        self.crossing_penalty = crossing_penalty

    def resolve_voices(
        self,
        notes: List[Dict[str, Any]],
        staff_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Resolve voice assignments for notes on a single staff.

        Args:
            notes: Notes on this staff
            staff_id: Staff identifier

        Returns:
            Notes with resolved voice assignments
        """
        logger.info(f"Resolving voices for staff {staff_id} ({len(notes)} notes)")

        # Filter notes for this staff
        staff_notes = [n for n in notes if n["spatial"]["staff_id"] == staff_id]

        if len(staff_notes) == 0:
            return notes

        # Sort by onset time
        staff_notes.sort(key=lambda n: n["time"]["onset_seconds"])

        # Group simultaneous notes (chords)
        chord_groups = self._group_simultaneous_notes(staff_notes)

        # Assign voices to minimize crossings
        voice_assignments = self._assign_voices_optimally(chord_groups)

        # Update notes with resolved voices
        for note in notes:
            if note["note_id"] in voice_assignments:
                note["resolved_voice"] = voice_assignments[note["note_id"]]

        logger.info(f"Assigned {len(set(voice_assignments.values()))} voices")

        return notes

    def _group_simultaneous_notes(
        self,
        notes: List[Dict[str, Any]],
        tolerance: float = 0.01,
    ) -> List[List[Dict[str, Any]]]:
        """
        Group notes that occur simultaneously (within tolerance).
        """
        if not notes:
            return []

        groups = []
        current_group = [notes[0]]
        current_onset = notes[0]["time"]["onset_seconds"]

        for note in notes[1:]:
            onset = note["time"]["onset_seconds"]
            if abs(onset - current_onset) <= tolerance:
                # Same chord
                current_group.append(note)
            else:
                # New chord
                groups.append(current_group)
                current_group = [note]
                current_onset = onset

        # Add last group
        if current_group:
            groups.append(current_group)

        return groups

    def _assign_voices_optimally(
        self,
        chord_groups: List[List[Dict[str, Any]]],
    ) -> Dict[str, int]:
        """
        Assign voices to minimize voice crossings.

        Uses a greedy algorithm: assign voices based on pitch ordering.
        """
        assignments = {}

        for group in chord_groups:
            # Sort notes by pitch (highest to lowest)
            sorted_notes = sorted(
                group, key=lambda n: n["pitch"]["midi_note"], reverse=True
            )

            # Assign voices: voice 1 = highest, voice 2 = second highest, etc.
            for i, note in enumerate(sorted_notes):
                voice_num = min(i + 1, self.max_voices)
                assignments[note["note_id"]] = voice_num

        return assignments

