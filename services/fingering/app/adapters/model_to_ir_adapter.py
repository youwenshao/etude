"""Adapter to convert fingering model predictions back to IR v2 format."""

import copy
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ModelToIRAdapter:
    """
    Adapter to convert fingering model predictions back to IR v2 format.

    Takes model predictions and annotates IR v1 notes to create IR v2.
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        model_name: str,
        model_version: str,
        adapter_version: str,
        uncertainty_policy: str,
    ):
        self.model_name = model_name
        self.model_version = model_version
        self.adapter_version = adapter_version
        self.uncertainty_policy = uncertainty_policy

    def annotate_ir(
        self,
        ir_v1: Dict[str, Any],
        predictions_by_hand: Dict[str, Dict[str, Any]],
        note_sequences_by_hand: Dict[str, List[Dict]],
    ) -> Dict[str, Any]:
        """
        Annotate IR v1 with fingering predictions to create IR v2.

        Args:
            ir_v1: Original Symbolic IR v1
            predictions_by_hand: Fingering predictions per hand
            note_sequences_by_hand: Note sequence metadata per hand

        Returns:
            Symbolic IR v2 with fingering annotations
        """
        logger.info("Annotating IR v1 with fingering predictions")

        # Deep copy IR v1
        ir_v2 = copy.deepcopy(ir_v1)

        # Update version
        ir_v2["version"] = "2.0.0"

        # Create note_id to fingering mapping
        fingering_map = self._create_fingering_map(
            predictions_by_hand, note_sequences_by_hand
        )

        # Annotate each note
        annotated_count = 0
        for note in ir_v2["notes"]:
            note_id = note["note_id"]
            if note_id in fingering_map:
                note["fingering"] = fingering_map[note_id]
                annotated_count += 1

        # Add fingering metadata
        total_notes = len(ir_v2["notes"])
        coverage = annotated_count / total_notes if total_notes > 0 else 0.0

        ir_v2["fingering_metadata"] = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "ir_to_model_adapter_version": self.adapter_version,
            "model_to_ir_adapter_version": self.VERSION,
            "uncertainty_policy": self.uncertainty_policy,
            "notes_annotated": annotated_count,
            "total_notes": total_notes,
            "coverage": coverage,
        }

        logger.info(
            f"Annotated {annotated_count}/{total_notes} notes "
            f"({coverage:.1%} coverage)"
        )

        return ir_v2

    def _create_fingering_map(
        self,
        predictions_by_hand: Dict[str, Dict],
        note_sequences_by_hand: Dict[str, List[Dict]],
    ) -> Dict[str, Dict[str, Any]]:
        """Create mapping from note_id to fingering annotation."""
        fingering_map = {}

        for hand in ["left", "right"]:
            if hand not in predictions_by_hand:
                continue

            predictions = predictions_by_hand[hand]["predictions"]
            note_sequence = note_sequences_by_hand[hand]

            # Ensure lengths match
            if len(predictions) != len(note_sequence):
                logger.warning(
                    f"Length mismatch for {hand} hand: "
                    f"{len(predictions)} predictions vs {len(note_sequence)} notes"
                )
                continue

            # Map predictions to notes
            for pred, note_info in zip(predictions, note_sequence):
                note_id = note_info["note_id"]

                # Convert alternatives to proper format
                alternatives = []
                for alt in pred.get("alternatives", []):
                    alternatives.append(
                        {
                            "finger": alt["finger"],
                            "confidence": alt["confidence"],
                        }
                    )

                fingering_annotation = {
                    "finger": pred["finger"],
                    "hand": hand,
                    "confidence": pred["confidence"],
                    "alternatives": alternatives,
                    "model_name": self.model_name,
                    "model_version": self.model_version,
                    "adapter_version": self.adapter_version,
                    "uncertainty_policy": self.uncertainty_policy,
                }

                fingering_map[note_id] = fingering_annotation

        return fingering_map

