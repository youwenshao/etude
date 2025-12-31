"""Uncertainty handling policies for resolving probabilistic assignments."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class UncertaintyPolicy(ABC):
    """Base class for uncertainty handling policies."""

    @abstractmethod
    def apply(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply uncertainty policy to resolve probabilistic assignments.

        Args:
            notes: List of notes with uncertain attributes

        Returns:
            List of notes with resolved attributes
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get policy name."""
        pass


class MLEPolicy(UncertaintyPolicy):
    """
    Maximum Likelihood Estimate Policy.

    Selects the single most probable value for each uncertain attribute.
    Fast and deterministic, suitable for production inference.
    """

    def get_name(self) -> str:
        return "mle"

    def apply(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Select most probable assignments."""
        logger.info("Applying MLE uncertainty policy")

        resolved_notes = []

        for note in notes:
            resolved_note = note.copy()

            # Resolve hand assignment
            if "hand_assignment" in note and note["hand_assignment"]:
                hand_assign = note["hand_assignment"]
                resolved_note["resolved_hand"] = hand_assign["hand"]
                resolved_note["resolved_hand_confidence"] = hand_assign["confidence"]

                # Check alternatives
                if hand_assign.get("alternatives"):
                    best_alt = max(
                        hand_assign["alternatives"],
                        key=lambda x: x["confidence"],
                        default=None,
                    )
                    if (
                        best_alt
                        and best_alt["confidence"] > hand_assign["confidence"]
                    ):
                        resolved_note["resolved_hand"] = best_alt["hand"]
                        resolved_note["resolved_hand_confidence"] = (
                            best_alt["confidence"]
                        )
            else:
                # Default inference
                resolved_note["resolved_hand"] = self._infer_hand(note)
                resolved_note["resolved_hand_confidence"] = 0.5

            # Resolve voice assignment
            if "voice_assignment" in note and note["voice_assignment"]:
                voice_assign = note["voice_assignment"]
                resolved_note["resolved_voice"] = voice_assign["voice_id"]
                resolved_note["resolved_voice_confidence"] = voice_assign["confidence"]
            else:
                resolved_note["resolved_voice"] = "unknown"
                resolved_note["resolved_voice_confidence"] = 0.3

            resolved_notes.append(resolved_note)

        return resolved_notes

    def _infer_hand(self, note: Dict[str, Any]) -> str:
        """Infer hand from staff or pitch when no explicit assignment."""
        # Use staff ID as primary indicator
        staff_id = note.get("spatial", {}).get("staff_id", "")
        if "1" in staff_id or "bass" in staff_id.lower():
            return "left"
        elif "0" in staff_id or "treble" in staff_id.lower():
            return "right"

        # Fall back to pitch
        midi = note.get("pitch", {}).get("midi_note", 60)
        return "left" if midi < 60 else "right"


class SamplingPolicy(UncertaintyPolicy):
    """
    Sampling-based Aggregation Policy (Future Implementation).

    Samples multiple realizations from probabilistic distributions,
    runs fingering inference on each, and aggregates results.

    More computationally expensive but can provide better uncertainty
    estimates and explore alternative interpretations.
    """

    def __init__(self, num_samples: int = 10):
        self.num_samples = num_samples

    def get_name(self) -> str:
        return "sampling"

    def apply(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sample multiple realizations (placeholder)."""
        raise NotImplementedError(
            "Sampling policy not yet implemented. "
            "This is reserved for future research extensions."
        )


def get_policy(policy_name: str, **kwargs) -> UncertaintyPolicy:
    """Factory function to get uncertainty policy by name."""
    policies = {
        "mle": MLEPolicy,
        "sampling": SamplingPolicy,
    }

    if policy_name not in policies:
        raise ValueError(f"Unknown policy: {policy_name}")

    return policies[policy_name](**kwargs)

