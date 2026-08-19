from datetime import UTC, datetime
from uuid import uuid4

import pytest
from agas_domain import CostLevel, SessionPrescription
from pydantic import ValidationError

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def test_session_prescription_requires_one_explicit_dose_form() -> None:
    with pytest.raises(ValidationError, match="exactly one of repetitions or duration"):
        SessionPrescription(
            athlete_id=uuid4(),
            block_plan_id=uuid4(),
            resource_allocation_id=uuid4(),
            exercise_resolution_id=uuid4(),
            exercise_id=uuid4(),
            adaptation_id=uuid4(),
            reason_for_inclusion="Synthetic contract fixture",
            sets=3,
            repetitions_per_set=5,
            duration_seconds=30,
            intensity_target="fixture target",
            rest_seconds=60,
            progression_rule_reference="fixture:manual-review@1.0.0",
            substitution_class="fixture",
            planned_duration_minutes=30,
            fatigue_cost=CostLevel.MODERATE,
            source_observation_ids=(uuid4(),),
            evidence_claim_ids=(uuid4(),),
            prescribed_at=NOW,
            rule_version="fixture@1.0.0",
        )
