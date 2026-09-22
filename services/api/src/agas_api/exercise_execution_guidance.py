"""Reviewed execution guidance available for immutable prescription snapshots.

This registry is deliberately small. Missing guidance stays missing and visible instead of
being synthesized from an exercise name. Adding or changing an entry requires a new version;
existing prescriptions retain the exact guidance object they were created with.
"""

from uuid import UUID

from agas_domain import ExerciseExecutionGuidance

STANDARD_PUSHUP_EXERCISE_ID = UUID("b1000000-0000-4000-8000-000000000002")

_GUIDANCE_BY_EXERCISE_ID: dict[UUID, ExerciseExecutionGuidance] = {
    STANDARD_PUSHUP_EXERCISE_ID: ExerciseExecutionGuidance(
        guidance_version="owner-alpha-standard-pushup-execution-guidance@1.0.0",
        setup_instructions=(
            "Use a level, nonslip floor with clear space for a full plank.",
            "Place a clean folded towel or similarly thin, repeatable target beneath the chin.",
            "Start with fingers pointing forward under the shoulders, toes as the pivot, "
            "head neutral, and the body held in one straight line.",
        ),
        execution_instructions=(
            "Press to straight arms, then lower under control until the chin lightly touches "
            "the target while the abdomen stays off the floor.",
            "Complete only the repetitions and effort range shown in this session; this is "
            "not a maximum-repetition test.",
            "Rest for the prescribed interval before beginning the next set.",
        ),
        technique_cues=(
            "Keep the head, trunk, hips, and legs moving as one controlled unit.",
            "Use the same hand position and chin-depth target for every repetition.",
            "Count a repetition only after returning to straight arms with the required "
            "alignment and depth maintained.",
        ),
        stop_conditions=(
            "End the set when the prescribed repetitions are complete or the reviewed technique "
            "can no longer be maintained.",
            "Stop immediately for pain or any symptom or loss of control that triggers the "
            "session safety instructions.",
            "Do not exceed the prescribed effort cap to finish a repetition or set.",
        ),
        authority=(
            "AGAS operational guidance derived from the approved standard-push-up assessment "
            "protocol and the ratified owner-alpha push-up construction authority."
        ),
        uncertainty=(
            "These cues standardize execution for this owner-alpha pathway. They do not establish "
            "that push-ups are universally optimal, replace safety screening, or independently "
            "validate the prescribed dose."
        ),
    ),
}


def execution_guidance_for(exercise_id: UUID) -> ExerciseExecutionGuidance | None:
    """Return the exact reviewed guidance object for an exercise, if one exists."""

    return _GUIDANCE_BY_EXERCISE_ID.get(exercise_id)
