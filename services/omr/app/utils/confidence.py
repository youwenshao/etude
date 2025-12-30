"""Confidence score utilities for OMR processing."""

from typing import Dict, List


def aggregate_confidence_scores(scores: List[float]) -> float:
    """
    Aggregate multiple confidence scores into a single value.

    Args:
        scores: List of confidence scores (0.0 to 1.0)

    Returns:
        Aggregated confidence score
    """
    if not scores:
        return 0.0

    # Use geometric mean for conservative aggregation
    product = 1.0
    for score in scores:
        product *= max(0.0, min(1.0, score))

    return product ** (1.0 / len(scores))


def calculate_overall_confidence(confidences: Dict[str, float]) -> float:
    """
    Calculate overall confidence from component confidences.

    Args:
        confidences: Dictionary of confidence scores by component

    Returns:
        Overall confidence score
    """
    if not confidences:
        return 0.0

    # Weighted average with detection and pitch having higher weight
    weights = {
        "detection": 0.3,
        "pitch": 0.25,
        "onset_time": 0.15,
        "duration": 0.15,
        "voice": 0.05,
        "hand": 0.05,
        "chord_membership": 0.05,
    }

    weighted_sum = 0.0
    total_weight = 0.0

    for component, weight in weights.items():
        if component in confidences:
            weighted_sum += confidences[component] * weight
            total_weight += weight

    if total_weight == 0.0:
        return 0.0

    return weighted_sum / total_weight

