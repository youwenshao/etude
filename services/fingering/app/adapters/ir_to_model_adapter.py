"""Adapter to convert Symbolic IR v1 to PRamoneda model input format."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
import torch

from app.policies.uncertainty_policy import get_policy

logger = logging.getLogger(__name__)


@dataclass
class NoteFeatures:
    """Features for a single note."""

    pitch: int  # MIDI note number
    duration: float  # Duration in beats
    ioi: float  # Inter-onset interval (time to next note)
    metric_position: float  # Position within measure
    is_chord: bool  # Is part of a chord
    chord_position: int  # Position in chord (0=lowest, 1=middle, 2=highest, etc.)


class IRToModelAdapter:
    """
    Adapter to convert Symbolic IR v1 to PRamoneda model input format.

    This is a versioned, first-class component of the pipeline.

    Responsibilities:
    - Extract ordered note sequences from IR
    - Apply uncertainty policies (MLE, sampling, etc.)
    - Generate model-required features
    - Handle hand/voice separation
    - Create PyTorch tensors
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        uncertainty_policy: str = "mle",
        include_ioi: bool = True,
        include_duration: bool = True,
        include_metric_position: bool = True,
        include_chord_info: bool = True,
    ):
        self.uncertainty_policy = uncertainty_policy
        self.include_ioi = include_ioi
        self.include_duration = include_duration
        self.include_metric_position = include_metric_position
        self.include_chord_info = include_chord_info

        logger.info(f"IR-to-Model Adapter v{self.VERSION} initialized")
        logger.info(f"Uncertainty policy: {uncertainty_policy}")

    def convert(self, ir_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert complete IR v1 to model input format.

        Args:
            ir_data: Symbolic IR v1 as dictionary

        Returns:
            Dictionary containing:
                - features_by_hand: Dict[str, torch.Tensor]
                - note_sequences_by_hand: Dict[str, List[Dict]]
                - metadata: Dict with conversion info
        """
        logger.info("Converting IR v1 to model input format")

        # Extract notes and apply uncertainty policy
        notes = ir_data["notes"]
        resolved_notes = self._apply_uncertainty_policy(notes)

        # Separate by hand
        left_hand_notes, right_hand_notes = self._separate_by_hand(resolved_notes)

        logger.info(
            f"Separated into {len(left_hand_notes)} left-hand "
            f"and {len(right_hand_notes)} right-hand notes"
        )

        # Sort by time
        left_hand_notes = sorted(
            left_hand_notes, key=lambda n: n["time"]["onset_seconds"]
        )
        right_hand_notes = sorted(
            right_hand_notes, key=lambda n: n["time"]["onset_seconds"]
        )

        # Extract features for each hand
        left_features, left_sequence = self._extract_features(left_hand_notes)
        right_features, right_sequence = self._extract_features(right_hand_notes)

        result = {
            "features_by_hand": {
                "left": left_features,
                "right": right_features,
            },
            "note_sequences_by_hand": {
                "left": left_sequence,
                "right": right_sequence,
            },
            "metadata": {
                "adapter_version": self.VERSION,
                "uncertainty_policy": self.uncertainty_policy,
                "feature_dim": left_features.shape[1] if len(left_hand_notes) > 0 else 0,
                "left_hand_count": len(left_hand_notes),
                "right_hand_count": len(right_hand_notes),
            },
        }

        logger.info(
            f"Conversion complete. Feature dimension: {result['metadata']['feature_dim']}"
        )

        return result

    def _apply_uncertainty_policy(self, notes: List[Dict]) -> List[Dict]:
        """
        Apply uncertainty policy to resolve probabilistic assignments.

        For MLE policy: select most likely hand, voice, etc.
        For sampling policy: sample from distributions (future work)
        """
        policy = get_policy(self.uncertainty_policy)
        return policy.apply(notes)

    def _separate_by_hand(
        self, notes: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Separate notes into left and right hand groups."""
        left_hand = []
        right_hand = []

        for note in notes:
            hand = note.get("resolved_hand", "right")
            if hand == "left":
                left_hand.append(note)
            else:
                right_hand.append(note)

        return left_hand, right_hand

    def _extract_features(
        self, notes: List[Dict]
    ) -> Tuple[torch.Tensor, List[Dict]]:
        """
        Extract feature vectors for a sequence of notes.

        Returns:
            (features_tensor, note_sequence_info)
            features_tensor: (seq_len, feature_dim)
            note_sequence_info: List of dicts with note metadata
        """
        if len(notes) == 0:
            # Empty sequence
            return torch.zeros(0, self._get_feature_dim()), []

        features_list = []
        sequence_info = []

        for i, note in enumerate(notes):
            note_features = self._extract_note_features(note, notes, i)
            features_list.append(note_features)

            # Store metadata for later annotation
            sequence_info.append(
                {
                    "note_id": note["note_id"],
                    "pitch": note["pitch"]["midi_note"],
                    "onset_seconds": note["time"]["onset_seconds"],
                    "onset_beats": note["time"]["absolute_beat"],
                    "measure": note["time"]["measure"],
                    "is_chord_member": note.get("chord_membership") is not None,
                }
            )

        # Stack into tensor
        features_tensor = torch.tensor(features_list, dtype=torch.float32)

        return features_tensor, sequence_info

    def _extract_note_features(
        self, note: Dict, all_notes: List[Dict], index: int
    ) -> List[float]:
        """Extract feature vector for a single note."""
        features = []

        # 1. Pitch (normalized MIDI)
        midi = note["pitch"]["midi_note"]
        features.append(midi / 127.0)  # Normalize to [0, 1]

        # 2. Pitch class (one-hot would be better, but keep it simple)
        pitch_class = midi % 12
        features.append(pitch_class / 12.0)

        # 3. Octave
        octave = midi // 12
        features.append(octave / 10.0)  # Normalize

        # 4. Duration (optional)
        if self.include_duration:
            duration_beats = note["duration"]["duration_beats"]
            # Normalize by typical range (0-4 beats)
            features.append(min(duration_beats / 4.0, 1.0))

        # 5. Inter-onset interval to next note (optional)
        if self.include_ioi:
            if index < len(all_notes) - 1:
                next_note = all_notes[index + 1]
                ioi = (
                    next_note["time"]["onset_seconds"]
                    - note["time"]["onset_seconds"]
                )
                # Normalize by typical range (0-2 seconds)
                features.append(min(ioi / 2.0, 1.0))
            else:
                features.append(0.0)  # Last note

        # 6. Metric position within measure (optional)
        if self.include_metric_position:
            beat_in_measure = note["time"]["beat"]
            # Normalize by measure length (assume 4/4 = 4 beats)
            features.append(beat_in_measure / 4.0)

        # 7. Chord information (optional)
        if self.include_chord_info:
            is_chord = 1.0 if note.get("chord_membership") else 0.0
            features.append(is_chord)

            # Relative pitch in chord (if in chord)
            if note.get("chord_membership"):
                chord_id = note["chord_membership"]["chord_id"]
                # Find all notes in this chord
                chord_notes = [
                    n
                    for n in all_notes
                    if n.get("chord_membership")
                    and n["chord_membership"]["chord_id"] == chord_id
                ]
                chord_pitches = sorted(
                    [n["pitch"]["midi_note"] for n in chord_notes]
                )

                if midi in chord_pitches:
                    position = chord_pitches.index(midi)
                    # Normalize by typical chord size (3-4 notes)
                    features.append(position / 4.0)
                else:
                    features.append(0.0)
            else:
                features.append(0.0)

        return features

    def _get_feature_dim(self) -> int:
        """Calculate feature dimension based on configuration."""
        dim = 3  # pitch, pitch_class, octave (always included)
        if self.include_duration:
            dim += 1
        if self.include_ioi:
            dim += 1
        if self.include_metric_position:
            dim += 1
        if self.include_chord_info:
            dim += 2  # is_chord, chord_position
        return dim

