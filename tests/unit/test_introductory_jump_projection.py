from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

from agas_api.assessment_workflow import _introductory_jump_dose_projection
from agas_api.training_construction_candidates import (
    prepared_training_construction_candidate_for_scope,
)
from agas_domain import Confidence, ExposureNeed, ExposureNeedStatus, ExposureType
from agas_domain.persistence.repository import DomainRepository
from agas_seed_data import load_seed_catalog

NOW = datetime(2026, 9, 21, 14, 0, tzinfo=UTC)
SCOPE = "assessment:countermovement_vertical_jump:maximal"


def _need() -> ExposureNeed:
    return ExposureNeed(
        id=UUID("10000000-0000-4000-8000-000000000030"),
        created_at=NOW - timedelta(hours=1),
        athlete_id=UUID("20000000-0000-4000-8000-000000000030"),
        exposure_type=ExposureType.JUMPING,
        target_scope=SCOPE,
        status=ExposureNeedStatus.INTRODUCTORY_EXPOSURE_NEEDED,
        lookback_days=28,
        minimum_exposure_days=1,
        source_observation_ids=(UUID("30000000-0000-4000-8000-000000000030"),),
        confidence=Confidence.HIGH,
        rationale="No recent jumping exposure was reported.",
        uncertainty="Self-report cannot establish tissue readiness.",
        authority_reference="recent-impact-exposure-gate@1.0.0",
        identified_at=NOW - timedelta(hours=1),
        valid_until=NOW + timedelta(days=1),
        rule_version="exposure-need@1.0.0",
    )


def test_ratified_jump_authority_becomes_an_athlete_facing_dose_preview() -> None:
    prepared = prepared_training_construction_candidate_for_scope(SCOPE)
    policy = prepared.release.introductory_exposure_dose_policy
    definition = prepared.release.exposure_definition
    assert policy is not None
    assert definition is not None
    exercise = next(
        item for item in load_seed_catalog().exercises if item.id == definition.exercise_id
    )
    repository = Mock(spec=DomainRepository)
    repository.get_decision_record.return_value = SimpleNamespace(
        evidence=(f"candidate_content_digest:{prepared.presentation.content_digest}",)
    )
    repository.get_introductory_exposure_dose_policy.return_value = policy
    repository.get_exposure_definition.return_value = definition
    repository.get_exercise.return_value = exercise

    projection = _introductory_jump_dose_projection(repository, _need(), NOW)

    assert projection is not None
    assert projection.exercise_name == "Countermovement jump"
    assert projection.sets == 2
    assert projection.repetitions_per_set == 3
    assert projection.total_contacts == 6
    assert projection.numeric_value_origin == "engineering_judgment"


def test_unratified_jump_authority_stays_hidden() -> None:
    repository = Mock(spec=DomainRepository)
    repository.get_decision_record.return_value = None

    assert _introductory_jump_dose_projection(repository, _need(), NOW) is None
