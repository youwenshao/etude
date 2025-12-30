"""Job state machine for managing valid state transitions."""

from enum import Enum

from app.models.job import JobStatus as ModelJobStatus, JobStage as ModelJobStage


# Re-export for convenience
JobStatus = ModelJobStatus
JobStage = ModelJobStage


# Valid state transition matrix
VALID_TRANSITIONS: dict[str, set[str]] = {
    JobStatus.PENDING.value: {JobStatus.OMR_PROCESSING.value, JobStatus.FAILED.value},
    JobStatus.OMR_PROCESSING.value: {
        JobStatus.OMR_COMPLETED.value,
        JobStatus.OMR_FAILED.value,
        JobStatus.FAILED.value,
    },
    JobStatus.OMR_COMPLETED.value: {
        JobStatus.FINGERING_PROCESSING.value,
        JobStatus.FAILED.value,
    },
    JobStatus.OMR_FAILED.value: {
        JobStatus.OMR_PROCESSING.value,  # Allow retry
        JobStatus.FAILED.value,
    },
    JobStatus.FINGERING_PROCESSING.value: {
        JobStatus.FINGERING_COMPLETED.value,
        JobStatus.FINGERING_FAILED.value,
        JobStatus.FAILED.value,
    },
    JobStatus.FINGERING_COMPLETED.value: {
        JobStatus.RENDERING_PROCESSING.value,
        JobStatus.FAILED.value,
    },
    JobStatus.FINGERING_FAILED.value: {
        JobStatus.FINGERING_PROCESSING.value,  # Allow retry
        JobStatus.FAILED.value,
    },
    JobStatus.RENDERING_PROCESSING.value: {
        JobStatus.COMPLETED.value,
        JobStatus.FAILED.value,
    },
    JobStatus.COMPLETED.value: set(),  # Terminal state
    JobStatus.FAILED.value: set(),  # Terminal state
}


def validate_transition(current_status: str, next_status: str) -> tuple[bool, str | None]:
    """
    Validate if a state transition is allowed.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if current_status not in VALID_TRANSITIONS:
        return False, f"Unknown current status: {current_status}"

    if next_status not in VALID_TRANSITIONS:
        return False, f"Unknown next status: {next_status}"

    allowed_next = VALID_TRANSITIONS[current_status]
    if next_status not in allowed_next:
        return (
            False,
            f"Invalid transition from {current_status} to {next_status}. "
            f"Allowed transitions: {', '.join(allowed_next)}",
        )

    return True, None

