"""OMR Model Wrapper for Polyphonic-TrOMR."""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import structlog
import torch

# Add Polyphonic-TrOMR to Python path
from app.config import settings

_tromr_path = settings.get_tromr_base_path()
if str(_tromr_path) not in sys.path:
    sys.path.insert(0, str(_tromr_path))

# Import Polyphonic-TrOMR components
from tromr.configs import getconfig
from tromr.staff2score import StaffToScore

logger = structlog.get_logger(__name__)


class OMRModel:
    """
    Wrapper for Polyphonic-TrOMR model.

    This class handles:
    - Model loading and initialization
    - Inference on sheet music images
    - Post-processing of raw predictions
    - Confidence score generation
    """

    def __init__(
        self,
        device: Optional[str] = None,
        confidence_threshold: float = 0.5,
        temperature: float = 0.2,
    ):
        """
        Initialize OMR model.

        Args:
            device: Device to use ('mps', 'cuda', 'cpu'). If None, auto-detect.
            confidence_threshold: Minimum confidence for detections
            temperature: Temperature for model generation
        """
        # Device configuration with MPS priority
        if device is None:
            device = settings.device
        self.device = torch.device(device)
        self.confidence_threshold = confidence_threshold
        self.temperature = temperature

        logger.info(
            "Initializing OMR model",
            device=str(self.device),
            model_name=settings.model_name,
            model_version=settings.model_version,
        )

        # Load Polyphonic-TrOMR model
        self.staff_to_score = self._load_model()

    def _load_model(self) -> StaffToScore:
        """
        Load the pretrained Polyphonic-TrOMR model.

        Returns:
            StaffToScore instance

        Raises:
            FileNotFoundError: If model files are not found
            RuntimeError: If model loading fails
        """
        try:
            config_path = settings.get_tromr_config_path()
            checkpoint_path = settings.get_tromr_checkpoint_path()

            if not config_path.exists():
                raise FileNotFoundError(
                    f"TrOMR config file not found at {config_path}. "
                    "Please ensure Polyphonic-TrOMR repository is cloned correctly."
                )

            if not checkpoint_path.exists():
                raise FileNotFoundError(
                    f"TrOMR checkpoint file not found at {checkpoint_path}. "
                    "Please download the model weights."
                )

            logger.info(
                "Loading TrOMR model",
                config_path=str(config_path),
                checkpoint_path=str(checkpoint_path),
            )

            # Load configuration
            args = getconfig(str(config_path))

            # Override device in args if needed (StaffToScore uses cuda/cpu detection)
            # We'll handle device placement manually if needed

            # Initialize StaffToScore handler
            handler = StaffToScore(args)

            # Move model to correct device
            if self.device.type == "mps":
                # MPS support - move model to MPS device
                try:
                    handler.model.to(self.device)
                    logger.info("Model moved to MPS device")
                except Exception as e:
                    logger.warning(
                        "Failed to move model to MPS, falling back to CPU",
                        error=str(e),
                    )
                    self.device = torch.device("cpu")
                    handler.model.to(self.device)
            else:
                handler.model.to(self.device)

            logger.info("TrOMR model loaded successfully", device=str(self.device))

            return handler

        except FileNotFoundError as e:
            logger.error("Model files not found", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to load TrOMR model", error=str(e), exc_info=True)
            raise RuntimeError(f"Model loading failed: {str(e)}") from e

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess sheet music image for model input.

        Args:
            image: numpy array of shape (H, W, C) in RGB format

        Returns:
            Preprocessed image ready for model (RGB format)
        """
        # Ensure RGB format
        if len(image.shape) == 2:
            # Grayscale to RGB
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            # RGBA to RGB - handle alpha channel like TrOMR does
            image = 255 - image[:, :, 3]
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 3:
            # Already RGB, ensure it's in the right format (BGR to RGB if needed)
            # Assume input is already RGB
            pass
        else:
            raise ValueError(f"Unsupported image shape: {image.shape}")

        return image

    def _preprocess_for_model(self, rgb_image: np.ndarray) -> torch.Tensor:
        """
        Preprocess RGB image using TrOMR's preprocessing pipeline.

        Args:
            rgb_image: RGB image as numpy array (H, W, 3)

        Returns:
            Preprocessed tensor ready for model
        """
        # Use the same preprocessing as StaffToScore
        args = self.staff_to_score.args
        h, w, c = rgb_image.shape
        new_h = args.max_height
        new_w = int(args.max_height / h * w)
        new_w = new_w // args.patch_size * args.patch_size
        resized = cv2.resize(rgb_image, (new_w, new_h))

        # Apply TrOMR's transform (grayscale, normalize, to tensor)
        transformed = self.staff_to_score.transform(image=resized)["image"][:1]
        return transformed

    def predict(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Run OMR inference on a single page image.

        Args:
            image: Sheet music page as numpy array (H, W, C) in RGB format

        Returns:
            Dictionary containing detected musical elements with confidence scores
        """
        try:
            # Preprocess image to RGB
            rgb_image = self.preprocess_image(image)

            # Preprocess using TrOMR's pipeline
            img_tensor = self._preprocess_for_model(rgb_image)

            # Run model inference
            with torch.no_grad():
                imgs = img_tensor.unsqueeze(0).float().unsqueeze(1).to(self.device)
                output = self.staff_to_score.model.generate(
                    imgs, temperature=self.temperature
                )
                rhythm_tokens, pitch_tokens, lift_tokens = output

            # Detokenize to get string representations
            predrhythm = self.staff_to_score.detokenize(
                rhythm_tokens, self.staff_to_score.rhythmtokenizer
            )
            predpitch = self.staff_to_score.detokenize(
                pitch_tokens, self.staff_to_score.pitchtokenizer
            )
            predlift = self.staff_to_score.detokenize(
                lift_tokens, self.staff_to_score.lifttokenizer
            )

            # Convert tokenized predictions to structured format
            predictions = self._parse_predictions(
                predrhythm, predpitch, predlift, image.shape
            )

            logger.info(
                "OMR inference completed",
                notes_detected=len(predictions.get("notes", [])),
                image_shape=image.shape,
            )

            return predictions
        except Exception as e:
            logger.error(
                "OMR inference failed",
                error=str(e),
                image_shape=image.shape,
                exc_info=True,
            )
            raise RuntimeError(f"Inference failed: {str(e)}") from e

    def _parse_predictions(
        self,
        predrhythm: List[List[str]],
        predpitch: List[List[str]],
        predlift: List[List[str]],
        image_shape: tuple,
    ) -> Dict[str, Any]:
        """
        Parse tokenized predictions into structured format.

        TrOMR outputs token sequences in format like:
        "clef-G2+keySignature-CM+note-C4_eighth|note-E4_eighth+..."

        Args:
            predrhythm: List of rhythm token sequences (list of lists of strings)
            predpitch: List of pitch token sequences
            predlift: List of lift (accidental) token sequences
            image_shape: Original image shape (H, W, C)

        Returns:
            Dictionary with notes, time signature, key signature, tempo, staves
        """
        notes = []
        time_signature = {"numerator": 4, "denominator": 4}
        key_signature = {"fifths": 0, "mode": "major"}
        tempo = {"bpm": 120}
        staves = []  # Start with empty list, build as we go
        current_time = 0.0
        staff_id = 0

        # Parse each staff/system (each element in the lists)
        for staff_idx, (rhythm_seq, pitch_seq, lift_seq) in enumerate(
            zip(predrhythm, predpitch, predlift)
        ):
            # TrOMR tokens are strings that may contain multiple elements
            # Join tokens and parse the sequence
            rhythm_str = " ".join(rhythm_seq) if isinstance(rhythm_seq, list) else str(rhythm_seq)
            pitch_str = " ".join(pitch_seq) if isinstance(pitch_seq, list) else str(pitch_seq)
            lift_str = " ".join(lift_seq) if isinstance(lift_seq, list) else str(lift_seq)

            # Parse metadata (clef, key signature, time signature)
            clef_info = None
            if "clef" in rhythm_str.lower():
                clef_info = self._extract_clef(rhythm_str)

            # Create or update staff entry
            if staff_id < len(staves):
                # Update existing staff
                if clef_info:
                    staves[staff_id]["clef"] = clef_info
            else:
                # Create new staff entry
                staves.append({
                    "staff_id": f"staff_{staff_id}",
                    "clef": clef_info or "treble",  # Default to treble if not found
                    "part_name": None,
                })

            if "keysignature" in rhythm_str.lower():
                key_info = self._extract_key_signature(rhythm_str)
                if key_info:
                    key_signature = key_info

            # Parse notes from the sequence
            # Notes are separated by "+" or "|" (barline)
            # Format: "note-C4_eighth", "note-E4_quarter", etc.
            note_tokens = self._extract_note_tokens(rhythm_str, pitch_str, lift_str)

            for note_token_info in note_tokens:
                note_info = self._parse_note_token(
                    note_token_info["rhythm"],
                    note_token_info["pitch"],
                    note_token_info.get("lift", ""),
                )
                if note_info:
                    note_info["onset_time"] = current_time
                    note_info["staff"] = staff_id
                    note_info["position"] = {"x": 0, "y": 0}  # Placeholder
                    note_info["confidence"] = 0.9  # Default confidence
                    notes.append(note_info)

                    # Advance time based on duration
                    duration = note_info.get("duration", 0.5)
                    current_time += duration

            staff_id += 1

        # Ensure at least one staff
        if not staves:
            staves = [{"staff_id": "staff_0", "clef": "treble", "part_name": None}]

        return {
            "notes": notes,
            "time_signature": time_signature,
            "key_signature": key_signature,
            "tempo": tempo,
            "staves": staves,
            "metadata": {
                "page_number": 1,
                "image_width": image_shape[1] if len(image_shape) > 1 else 0,
                "image_height": image_shape[0] if len(image_shape) > 0 else 0,
            },
        }

    def _extract_clef(self, rhythm_str: str) -> Optional[str]:
        """Extract clef from token string (e.g., 'clef-G2' -> 'treble')."""
        match = re.search(r"clef-([A-Z]\d+)", rhythm_str, re.IGNORECASE)
        if match:
            clef_code = match.group(1)
            # G2 = treble, F4 = bass
            if "G2" in clef_code or "G" in clef_code:
                return "treble"
            elif "F4" in clef_code or "F" in clef_code:
                return "bass"
        return None

    def _extract_key_signature(self, rhythm_str: str) -> Optional[Dict[str, Any]]:
        """Extract key signature from token string (e.g., 'keySignature-CM' -> C major)."""
        match = re.search(r"keysignature-([A-Z][#b]?[Mm]?)", rhythm_str, re.IGNORECASE)
        if match:
            key_code = match.group(1)
            # Simple mapping - can be enhanced
            if "M" in key_code or "maj" in key_code.lower():
                mode = "major"
            else:
                mode = "minor"
            # Extract fifths (simplified)
            fifths = 0  # Default, can be enhanced with proper key detection
            return {"fifths": fifths, "mode": mode}
        return None

    def _extract_note_tokens(
        self, rhythm_str: str, pitch_str: str, lift_str: str
    ) -> List[Dict[str, str]]:
        """Extract note tokens from token strings."""
        notes = []
        # Find all note patterns in rhythm string
        # Format: "note-C4_eighth" or similar
        rhythm_matches = re.finditer(r"note-([^+|]+)", rhythm_str, re.IGNORECASE)
        pitch_matches = list(re.finditer(r"([A-Z][#b]?\d+)", pitch_str))
        lift_matches = list(re.finditer(r"([#bN])", lift_str))

        rhythm_list = list(rhythm_matches)
        for i, rhythm_match in enumerate(rhythm_list):
            note_info = {"rhythm": rhythm_match.group(0), "pitch": "", "lift": ""}
            if i < len(pitch_matches):
                note_info["pitch"] = pitch_matches[i].group(1)
            if i < len(lift_matches):
                note_info["lift"] = lift_matches[i].group(1)
            notes.append(note_info)

        return notes

    def _parse_note_token(
        self, rhythm_token: str, pitch_token: str, lift_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Parse individual note tokens into structured format.

        Args:
            rhythm_token: Rhythm token (e.g., "note-C4_eighth")
            pitch_token: Pitch token
            lift_token: Accidental/lift token

        Returns:
            Dictionary with pitch and duration info, or None if invalid
        """
        try:
            # Parse rhythm token: "note-C4_eighth" -> pitch="C4", duration="eighth"
            if "note-" not in rhythm_token.lower():
                return None

            # Extract pitch and duration
            parts = rhythm_token.split("_")
            if len(parts) < 2:
                return None

            # Get pitch from pitch_token or rhythm_token
            pitch_name = pitch_token if pitch_token else "C4"
            duration_type = parts[-1]  # e.g., "eighth", "quarter"

            # Convert duration type to seconds (assuming 120 BPM)
            duration_map = {
                "whole": 4.0,
                "half": 2.0,
                "quarter": 1.0,
                "eighth": 0.5,
                "sixteenth": 0.25,
                "32nd": 0.125,
            }
            duration = duration_map.get(duration_type, 0.5)

            # Parse pitch to MIDI
            midi_note = self._pitch_to_midi(pitch_name)

            return {
                "pitch": {"midi": midi_note, "name": pitch_name},
                "duration": duration,
            }

        except Exception as e:
            logger.warning("Failed to parse note token", token=rhythm_token, error=str(e))
            return None

    def _pitch_to_midi(self, pitch_name: str) -> int:
        """
        Convert pitch name (e.g., "C4") to MIDI note number.

        Args:
            pitch_name: Pitch in scientific notation (e.g., "C4", "F#5")

        Returns:
            MIDI note number (60 = C4)
        """
        # Simple pitch to MIDI conversion
        # C4 = 60, C#4 = 61, D4 = 62, etc.
        pitch_classes = {
            "C": 0,
            "C#": 1,
            "D": 2,
            "D#": 3,
            "E": 4,
            "F": 5,
            "F#": 6,
            "G": 7,
            "G#": 8,
            "A": 9,
            "A#": 10,
            "B": 11,
        }

        # Handle flats
        pitch_name = pitch_name.replace("b", "#").replace("Bb", "A#").replace("Eb", "D#").replace("Ab", "G#")

        # Extract pitch class and octave
        if len(pitch_name) >= 2 and pitch_name[1] == "#":
            pitch_class = pitch_name[:2]
            octave_str = pitch_name[2:]
        else:
            pitch_class = pitch_name[0]
            octave_str = pitch_name[1:]

        try:
            octave = int(octave_str) if octave_str.isdigit() else 4
            pitch_value = pitch_classes.get(pitch_class, 0)
            midi = 12 * (octave + 1) + pitch_value
            return max(0, min(127, midi))  # Clamp to valid MIDI range
        except Exception:
            return 60  # Default to C4

    def predict_multi_page(self, images: List[np.ndarray]) -> List[Dict[str, Any]]:
        """
        Run OMR on multiple pages.

        Args:
            images: List of page images

        Returns:
            List of predictions, one per page
        """
        predictions = []

        for i, image in enumerate(images):
            logger.info("Processing page", page=i + 1, total_pages=len(images))
            page_predictions = self.predict(image)
            page_predictions["page_number"] = i + 1
            predictions.append(page_predictions)

        return predictions


# Global model instance (loaded once at startup)
_model_instance: Optional[OMRModel] = None


def get_omr_model() -> OMRModel:
    """Get the global OMR model instance."""
    global _model_instance

    if _model_instance is None:
        _model_instance = OMRModel(
            device=settings.device,
            confidence_threshold=settings.confidence_threshold,
            temperature=settings.temperature,
        )

    return _model_instance
