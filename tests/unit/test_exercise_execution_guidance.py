from uuid import uuid4

import pytest
from agas_api.exercise_execution_guidance import (
    STANDARD_PUSHUP_EXERCISE_ID,
    execution_guidance_for,
)
from agas_domain import ExerciseExecutionGuidance
from pydantic import ValidationError


def test_reviewed_pushup_guidance_is_explicit_and_versioned() -> None:
    guidance = execution_guidance_for(STANDARD_PUSHUP_EXERCISE_ID)

    assert guidance is not None
    assert guidance.guidance_version == "owner-alpha-standard-pushup-execution-guidance@1.0.0"
    assert guidance.setup_instructions
    assert guidance.execution_instructions
    assert guidance.technique_cues
    assert guidance.stop_conditions
    assert "universally optimal" in guidance.uncertainty


def test_unknown_exercise_does_not_receive_invented_guidance() -> None:
    assert execution_guidance_for(uuid4()) is None


def test_guidance_rejects_duplicate_steps() -> None:
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        ExerciseExecutionGuidance(
            guidance_version="fixture@1.0.0",
            setup_instructions=("Repeated step.", "Repeated step."),
            execution_instructions=("Perform the movement.",),
            technique_cues=("Maintain control.",),
            stop_conditions=("Stop when directed.",),
            authority="Fixture authority.",
            uncertainty="Fixture uncertainty.",
        )
