"""Fingering model wrapper for PRamoneda Automatic Piano Fingering model."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

from app.config import settings

# Add PRamoneda model to path
sys.path.insert(0, str(settings.get_pramoneda_base_path()))

logger = logging.getLogger(__name__)

# Try to import PRamoneda model components
try:
    from nns.seq2seq_model import AR_decoder, gnn_encoder, lstm_encoder
    from nns.GGCN import GatedGraph

    PRAMONEDA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PRamoneda model imports failed: {e} - using placeholder")
    PRAMONEDA_AVAILABLE = False
    AR_decoder = None
    gnn_encoder = None
    lstm_encoder = None
    GatedGraph = None


class PlaceholderFingeringModel(nn.Module):
    """Placeholder model for development when weights are not available."""

    def __init__(self, input_size: int = 10, output_size: int = 7):
        super().__init__()
        self.linear = nn.Linear(input_size, output_size)

    def forward(self, x):
        """Return placeholder predictions."""
        return self.linear(x)


class FingeringModel:
    """
    Wrapper for PRamoneda Automatic Piano Fingering model.

    Supports both ArLSTM and ArGNN architectures.
    Works conditionally: with or without pretrained weights.
    """

    def __init__(
        self,
        model_type: str = "arlstm",
        model_path: Optional[str] = None,
        device: str = "cpu",
    ):
        self.model_type = model_type
        self.device = torch.device(device if torch.cuda.is_available() and device == "cuda" else "cpu")

        logger.info(f"Initializing {model_type} fingering model")
        logger.info(f"Using device: {self.device}")

        self.model = self._load_model(model_path)
        if self.model:
            self.model.eval()

        # Fingering vocabulary: 0 = no finger, 1-5 = fingers, 6 = thumb crossing
        self.finger_vocab = list(range(7))

    def _load_model(self, model_path: Optional[str]) -> Optional[nn.Module]:
        """Load pretrained fingering model or create placeholder."""
        if model_path:
            model_path = Path(model_path)
            if not model_path.exists():
                logger.warning(
                    f"Model weights not found at {model_path}. Using placeholder model."
                )
                return self._create_placeholder_model()
        else:
            logger.warning("No model path provided. Using placeholder model.")
            return self._create_placeholder_model()

        if not PRAMONEDA_AVAILABLE:
            logger.warning("PRamoneda model code not available. Using placeholder.")
            return self._create_placeholder_model()

        logger.info(f"Loading model from {model_path}")

        try:
            # Load checkpoint
            checkpoint = torch.load(model_path, map_location=self.device)

            # Initialize model based on type
            if self.model_type == "arlstm":
                model = self._create_arlstm_model(checkpoint)
            elif self.model_type == "argnn":
                model = self._create_argnn_model(checkpoint)
            else:
                raise ValueError(f"Unknown model type: {self.model_type}")

            # Load state dict
            if "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"])
            elif "state_dict" in checkpoint:
                model.load_state_dict(checkpoint["state_dict"])
            else:
                # Assume checkpoint is the state dict itself
                model.load_state_dict(checkpoint)

            model.to(self.device)
            model.eval()

            logger.info("Model loaded successfully")
            return model

        except Exception as e:
            logger.error(f"Failed to load model: {e}. Using placeholder.")
            return self._create_placeholder_model()

    def _create_placeholder_model(self) -> nn.Module:
        """Create a placeholder model for development."""
        logger.info("Creating placeholder fingering model")
        model = PlaceholderFingeringModel(input_size=10, output_size=7)
        model.to(self.device)
        return model

    def _create_arlstm_model(self, checkpoint: Dict) -> nn.Module:
        """Create ArLSTM model instance."""
        if lstm_encoder is None or AR_decoder is None:
            raise ImportError("ArLSTM model components not available")

        # Extract hyperparameters from checkpoint or use defaults
        config = checkpoint.get("config", {})

        input_size = config.get("input_size", 10)
        encoder = lstm_encoder(input=input_size, dropout=config.get("dropout", 0.0))
        decoder = AR_decoder(in_size=64)  # LSTM output size is 64 (32*2 bidirectional)

        # Combine encoder and decoder
        class ArLSTMModel(nn.Module):
            def __init__(self, encoder, decoder):
                super().__init__()
                self.encoder = encoder
                self.decoder = decoder

            def forward(self, x, x_lengths=None, edge_list=None):
                encoded = self.encoder(x, x_lengths, edge_list)
                # Use encoded features for decoder
                output = self.decoder(encoded, x_lengths, edge_list)
                return output

        return ArLSTMModel(encoder, decoder)

    def _create_argnn_model(self, checkpoint: Dict) -> nn.Module:
        """Create ArGNN model instance."""
        if gnn_encoder is None or AR_decoder is None:
            raise ImportError("ArGNN model components not available")

        config = checkpoint.get("config", {})

        input_size = config.get("input_size", 10)
        encoder = gnn_encoder(input_size=input_size)
        decoder = AR_decoder(in_size=input_size)

        class ArGNNModel(nn.Module):
            def __init__(self, encoder, decoder):
                super().__init__()
                self.encoder = encoder
                self.decoder = decoder

            def forward(self, x, x_lengths=None, edge_list=None):
                encoded = self.encoder(x, x_lengths, edge_list)
                output = self.decoder(encoded, x_lengths, edge_list)
                return output

        return ArGNNModel(encoder, decoder)

    def predict(
        self,
        features: torch.Tensor,
        hand: str,
        return_alternatives: bool = True,
        top_k: int = 2,
    ) -> Dict[str, Any]:
        """
        Predict fingering for a sequence of notes.

        Args:
            features: Tensor of shape (seq_len, feature_dim)
            hand: "left" or "right"
            return_alternatives: Whether to return alternative fingerings
            top_k: Number of alternatives to return

        Returns:
            Dictionary with predictions and confidence scores
        """
        with torch.no_grad():
            # Add batch dimension
            features = features.unsqueeze(0).to(self.device)
            seq_len = features.shape[1]

            # Create length tensor
            x_lengths = torch.tensor([seq_len], device=self.device)

            # Forward pass
            if hasattr(self.model, "encoder") and hasattr(self.model, "decoder"):
                # Full model (encoder + decoder)
                logits = self.model(features, x_lengths, edge_list=None)
            else:
                # Placeholder model
                logits = self.model(features)

            # Handle different output shapes
            if len(logits.shape) == 3:
                # (batch, seq_len, num_classes)
                logits = logits.squeeze(0)  # Remove batch dimension
            elif len(logits.shape) == 2:
                # (seq_len, num_classes) - already correct
                pass
            else:
                # Reshape if needed
                logits = logits.view(seq_len, -1)

            # Get probabilities
            probs = torch.softmax(logits, dim=-1)  # (seq_len, num_classes)

            # Get top predictions
            top_probs, top_fingers = torch.topk(probs, k=min(top_k, probs.shape[-1]), dim=-1)

            # Convert to numpy
            top_probs = top_probs.cpu().numpy()
            top_fingers = top_fingers.cpu().numpy()

            # Build results
            results = {
                "hand": hand,
                "sequence_length": seq_len,
                "predictions": [],
            }

            for i in range(seq_len):
                prediction = {
                    "position": i,
                    "finger": int(top_fingers[i][0]),
                    "confidence": float(top_probs[i][0]),
                    "alternatives": [],
                }

                if return_alternatives and top_k > 1:
                    for j in range(1, min(top_k, len(top_fingers[i]))):
                        prediction["alternatives"].append(
                            {
                                "finger": int(top_fingers[i][j]),
                                "confidence": float(top_probs[i][j]),
                            }
                        )

                results["predictions"].append(prediction)

            return results

    def predict_batch(
        self, features_batch: List[torch.Tensor], hands: List[str]
    ) -> List[Dict[str, Any]]:
        """Predict fingering for multiple sequences."""
        results = []

        for features, hand in zip(features_batch, hands):
            result = self.predict(features, hand)
            results.append(result)

        return results


# Global model instances (loaded once at startup)
_model_instances: Dict[str, FingeringModel] = {}


def get_fingering_model(model_type: str = "arlstm") -> FingeringModel:
    """Get the global fingering model instance."""
    global _model_instances

    if model_type not in _model_instances:
        model_path = settings.get_model_path()

        _model_instances[model_type] = FingeringModel(
            model_type=model_type,
            model_path=str(model_path) if model_path.exists() else None,
            device=settings.device,
        )

    return _model_instances[model_type]

