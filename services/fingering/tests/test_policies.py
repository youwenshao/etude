"""Tests for uncertainty policies."""

import pytest

from app.policies.uncertainty_policy import MLEPolicy, get_policy


def test_mle_policy():
    """Test MLE uncertainty policy."""
    policy = MLEPolicy()

    notes = [
        {
            "note_id": "note_1",
            "pitch": {"midi_note": 60},
            "spatial": {"staff_id": "staff_0"},
            "hand_assignment": {"hand": "right", "confidence": 0.9, "alternatives": []},
        },
        {
            "note_id": "note_2",
            "pitch": {"midi_note": 48},
            "spatial": {"staff_id": "staff_1"},
            "hand_assignment": {"hand": "left", "confidence": 0.8, "alternatives": []},
        },
    ]

    resolved = policy.apply(notes)

    assert len(resolved) == 2
    assert resolved[0]["resolved_hand"] == "right"
    assert resolved[1]["resolved_hand"] == "left"


def test_mle_policy_inference():
    """Test MLE policy hand inference when no assignment."""
    policy = MLEPolicy()

    notes = [
        {
            "note_id": "note_1",
            "pitch": {"midi_note": 60},
            "spatial": {"staff_id": "staff_0"},
        },
        {
            "note_id": "note_2",
            "pitch": {"midi_note": 48},
            "spatial": {"staff_id": "staff_1"},
        },
    ]

    resolved = policy.apply(notes)

    assert len(resolved) == 2
    # Should infer from staff ID
    assert resolved[0]["resolved_hand"] in ["left", "right"]
    assert resolved[1]["resolved_hand"] in ["left", "right"]


def test_get_policy():
    """Test policy factory function."""
    policy = get_policy("mle")
    assert isinstance(policy, MLEPolicy)
    assert policy.get_name() == "mle"

    with pytest.raises(ValueError):
        get_policy("unknown_policy")

