from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import agas_api.training_construction_candidates as construction_candidates
import pytest
from agas_api.assessment_governance_candidates import (
    RatifyAssessmentGovernanceCandidateCommand,
    list_assessment_governance_candidates,
    ratify_assessment_governance_candidate,
)
from agas_api.database import database_session_dependency
from agas_api.identity import AuthorizedRole, authenticated_principal_dependency
from agas_api.identity_admin import set_account_role
from agas_api.main import app
from agas_api.planning_governance_candidates import (
    CANDIDATE_VERSION as PLANNING_CANDIDATE_VERSION,
)
from agas_api.planning_governance_candidates import (
    RatifyPlanningGovernanceCandidateCommand,
    list_planning_governance_candidates,
    ratify_planning_governance_candidate,
)
from agas_api.resource_governance_candidates import (
    AEROBIC_CANDIDATE_ID as AEROBIC_RESOURCE_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    CANDIDATE_ID as RESOURCE_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    CANDIDATE_VERSION as RESOURCE_CANDIDATE_VERSION,
)
from agas_api.resource_governance_candidates import (
    JUMP_CANDIDATE_ID as JUMP_RESOURCE_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    JUMP_MAINTENANCE_CANDIDATE_ID as JUMP_MAINTENANCE_RESOURCE_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    PUSHUP_CANDIDATE_ID as PUSHUP_RESOURCE_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    RatifyResourceGovernanceCandidateCommand,
    list_resource_governance_candidates,
    ratify_resource_governance_candidate,
)
from agas_api.training_construction_candidates import (
    AEROBIC_CANDIDATE_ID,
    CANDIDATE_ID,
    CANDIDATE_VERSION,
    JUMP_EXPOSURE_CANDIDATE_ID,
    JUMP_MAINTENANCE_CANDIDATE_ID,
    JUMP_TRAINING_CANDIDATE_ID,
    PUSHUP_CANDIDATE_ID,
    RatifyTrainingConstructionCandidateCommand,
    TrainingConstructionCandidateConflictError,
    list_operational_response_evaluation_authorities,
    list_training_construction_candidates,
    prepared_training_construction_candidate,
    prepared_training_construction_candidate_for_scope,
    ratify_training_construction_candidate,
)
from agas_domain import (
    AccountRole,
    AccountRoleStatus,
    FixedDurationDosePolicy,
    FixedRepetitionDosePolicy,
    TrainingPriorityState,
)
from agas_domain.persistence.repository import DomainRepository
from agas_seed_data import SeedCatalogImporter, load_seed_catalog
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)
JUMP_NOW = datetime(2026, 9, 21, 13, 0, tzinfo=UTC)
JUMP_TRAINING_NOW = datetime(2026, 9, 23, 17, 0, tzinfo=UTC)
JUMP_MAINTENANCE_NOW = datetime(2026, 9, 24, 20, 0, tzinfo=UTC)
AEROBIC_NOW = datetime(2026, 9, 25, 17, 0, tzinfo=UTC)


def _authority() -> AuthorizedRole:
    return AuthorizedRole(
        account_id=UUID("10000000-0000-4000-8000-000000000007"),
        assignment_id=UUID("20000000-0000-4000-8000-000000000007"),
        role=AccountRole.PLANNING_REVIEWER,
        assigned_at=NOW - timedelta(days=2),
    )


def _persist_prerequisites(session: Session, authority: AuthorizedRole) -> None:
    SeedCatalogImporter(DomainRepository(session)).import_catalog(
        load_seed_catalog(), imported_at=NOW - timedelta(days=1)
    )
    session.commit()
    planning = next(
        item
        for item in list_planning_governance_candidates(session, projected_at=NOW).items
        if item.candidate.slug == "owner_alpha_deficit_only_initial_policy"
    )
    ratify_planning_governance_candidate(
        session,
        planning.candidate.candidate_id,
        RatifyPlanningGovernanceCandidateCommand(
            candidate_version=PLANNING_CANDIDATE_VERSION,
            content_digest=planning.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=NOW - timedelta(minutes=3),
    )
    resource = list_resource_governance_candidates(
        session, projected_at=NOW - timedelta(minutes=2)
    ).items[0]
    ratify_resource_governance_candidate(
        session,
        RESOURCE_CANDIDATE_ID,
        RatifyResourceGovernanceCandidateCommand(
            candidate_version=RESOURCE_CANDIDATE_VERSION,
            content_digest=resource.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=NOW - timedelta(minutes=2),
    )


def _command(session: Session) -> RatifyTrainingConstructionCandidateCommand:
    candidate = list_training_construction_candidates(session, projected_at=NOW).items[0].candidate
    return RatifyTrainingConstructionCandidateCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=candidate.content_digest,
        approval_attestation=True,
    )


def test_candidate_is_blocked_until_resource_bundle_is_ratified(session: Session) -> None:
    blocked = list_training_construction_candidates(session, projected_at=NOW)

    assert blocked.items[0].status == "blocked"
    assert "resource-governance" in blocked.items[0].issues[0]

    _persist_prerequisites(session, _authority())
    available = list_training_construction_candidates(session, projected_at=NOW)

    assert available.items[0].status == "available"
    assert "engineering prior" in (
        available.items[0].candidate.authority_basis.engineering_prior.casefold()
    )
    assert any(
        "does not validate" in item.unsupported_specifics
        for item in available.items[0].candidate.evidence
    )


def test_exact_construction_bundle_is_atomic_and_idempotent(session: Session) -> None:
    authority = _authority()
    _persist_prerequisites(session, authority)
    command = _command(session)

    first = ratify_training_construction_candidate(
        session, CANDIDATE_ID, command, authority, ratified_at=NOW
    )
    second = ratify_training_construction_candidate(
        session, CANDIDATE_ID, command, authority, ratified_at=NOW + timedelta(minutes=1)
    )
    repository = DomainRepository(session)

    assert first.created_weekly_scheduling_policy is True
    assert first.created_weekly_scheduling_policy_review is True
    assert first.created_progression_policy is True
    assert first.created_repetition_dose_policy is True
    assert first.created_session_safety_policy is True
    assert first.decision_record_created is True
    assert second.decision_record_created is False
    assert first.repetition_dose_policy is not None
    assert first.repetition_dose_policy.target_fraction_of_estimate == 0.5
    assert first.repetition_dose_policy.progression_policy_id == first.progression_policy.id
    assert first.weekly_scheduling_policy_review.decision.value == "approved"
    assert repository.get_repetition_dose_policy(first.repetition_dose_policy.id) == (
        first.repetition_dose_policy
    )
    assert (
        list_training_construction_candidates(session, projected_at=NOW + timedelta(minutes=2))
        .items[0]
        .status
        == "ratified"
    )


def test_aerobic_construction_bundle_has_bounded_duration_progression(
    session: Session,
) -> None:
    authority = _authority()
    SeedCatalogImporter(DomainRepository(session)).import_catalog(
        load_seed_catalog(), imported_at=AEROBIC_NOW - timedelta(hours=1)
    )
    session.commit()
    resource = next(
        item
        for item in list_resource_governance_candidates(
            session, projected_at=AEROBIC_NOW - timedelta(minutes=20)
        ).items
        if item.candidate.candidate_id == AEROBIC_RESOURCE_CANDIDATE_ID
    )
    ratify_resource_governance_candidate(
        session,
        AEROBIC_RESOURCE_CANDIDATE_ID,
        RatifyResourceGovernanceCandidateCommand(
            candidate_version=RESOURCE_CANDIDATE_VERSION,
            content_digest=resource.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=AEROBIC_NOW - timedelta(minutes=15),
    )
    candidate = next(
        item.candidate
        for item in list_training_construction_candidates(
            session, projected_at=AEROBIC_NOW - timedelta(minutes=5)
        ).items
        if item.candidate.candidate_id == AEROBIC_CANDIDATE_ID
    )

    result = ratify_training_construction_candidate(
        session,
        AEROBIC_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=CANDIDATE_VERSION,
            content_digest=candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=AEROBIC_NOW,
    )

    assert result.fixed_duration_dose_policy is not None
    assert result.fixed_duration_dose_policy.duration_seconds_per_set == 600
    assert result.fixed_duration_dose_policy.planned_duration_minutes == 12
    assert result.progression_policy.adjustment.dimension.value == "duration"
    assert result.progression_policy.adjustment.amount == 60
    assert result.progression_policy.maximum_prescription_value == 720
    assert result.response_evaluation_authority is not None
    assert result.response_evaluation_authority.minimum_meaningful_change == 50


def test_pushup_construction_bundle_uses_matching_resource_and_scope(session: Session) -> None:
    authority = _authority()
    _persist_prerequisites(session, authority)
    resource = next(
        item
        for item in list_resource_governance_candidates(
            session, projected_at=datetime(2026, 9, 17, 12, 5, tzinfo=UTC)
        ).items
        if item.candidate.candidate_id == PUSHUP_RESOURCE_CANDIDATE_ID
    )
    ratify_resource_governance_candidate(
        session,
        PUSHUP_RESOURCE_CANDIDATE_ID,
        RatifyResourceGovernanceCandidateCommand(
            candidate_version=RESOURCE_CANDIDATE_VERSION,
            content_digest=resource.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=datetime(2026, 9, 17, 12, 10, tzinfo=UTC),
    )
    candidate = next(
        item.candidate
        for item in list_training_construction_candidates(
            session, projected_at=datetime(2026, 9, 17, 12, 35, tzinfo=UTC)
        ).items
        if item.candidate.candidate_id == PUSHUP_CANDIDATE_ID
    )

    result = ratify_training_construction_candidate(
        session,
        PUSHUP_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=CANDIDATE_VERSION,
            content_digest=candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=datetime(2026, 9, 17, 12, 40, tzinfo=UTC),
    )

    assert result.repetition_dose_policy is not None
    assert result.repetition_dose_policy.estimate_scope == (
        "assessment_specific:maximum_consecutive_standard_pushup_repetitions"
    )
    assert result.repetition_dose_policy.target_fraction_of_estimate == 0.4
    assert result.repetition_dose_policy.maximum_repetitions_per_set == 10
    assert result.repetition_dose_policy.rest_seconds == 120


def test_introductory_jump_bundle_is_blocked_until_assessment_evidence_is_reviewed(
    session: Session,
) -> None:
    SeedCatalogImporter(DomainRepository(session)).import_catalog(
        load_seed_catalog(), imported_at=JUMP_NOW - timedelta(days=1)
    )
    session.commit()

    item = next(
        item
        for item in list_training_construction_candidates(session, projected_at=JUMP_NOW).items
        if item.candidate.candidate_id == JUMP_EXPOSURE_CANDIDATE_ID
    )

    assert item.status == "blocked"
    assert any("evidence claim" in issue for issue in item.issues)


def test_introductory_jump_bundle_persists_typed_engineering_authorities(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    SeedCatalogImporter(repository).import_catalog(
        load_seed_catalog(), imported_at=JUMP_NOW - timedelta(days=1)
    )
    session.commit()
    assessment = next(
        item.candidate
        for item in list_assessment_governance_candidates(
            session, projected_at=JUMP_NOW - timedelta(minutes=20)
        ).items
        if item.candidate.slug == "countermovement_vertical_jump"
    )
    assessment_authority = AuthorizedRole(
        account_id=UUID("10000000-0000-4000-8000-000000000020"),
        assignment_id=UUID("20000000-0000-4000-8000-000000000020"),
        role=AccountRole.ASSESSMENT_REVIEWER,
        assigned_at=JUMP_NOW - timedelta(days=1),
    )
    ratify_assessment_governance_candidate(
        session,
        assessment.candidate_id,
        RatifyAssessmentGovernanceCandidateCommand(
            candidate_version=assessment.candidate_version,
            content_digest=assessment.content_digest,
            approval_attestation=True,
        ),
        assessment_authority,
        ratified_at=JUMP_NOW - timedelta(minutes=15),
    )
    candidate = next(
        item
        for item in list_training_construction_candidates(session, projected_at=JUMP_NOW).items
        if item.candidate.candidate_id == JUMP_EXPOSURE_CANDIDATE_ID
    )
    authority = AuthorizedRole(
        account_id=UUID("10000000-0000-4000-8000-000000000021"),
        assignment_id=UUID("20000000-0000-4000-8000-000000000021"),
        role=AccountRole.PLANNING_REVIEWER,
        assigned_at=JUMP_NOW - timedelta(days=1),
    )

    first = ratify_training_construction_candidate(
        session,
        JUMP_EXPOSURE_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=candidate.candidate.candidate_version,
            content_digest=candidate.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=JUMP_NOW,
    )
    second = ratify_training_construction_candidate(
        session,
        JUMP_EXPOSURE_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=candidate.candidate.candidate_version,
            content_digest=candidate.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=JUMP_NOW + timedelta(minutes=1),
    )

    assert first.repetition_dose_policy is None
    assert first.introductory_exposure_dose_policy is not None
    assert first.introductory_exposure_dose_policy.numeric_value_origin == "engineering_judgment"
    assert (
        first.introductory_exposure_dose_policy.sets
        * first.introductory_exposure_dose_policy.dose_per_set
        == 6
    )
    assert first.introductory_exposure_dose_policy.evidence_claim_ids == ()
    assert first.exposure_definition is not None
    assert first.exposure_definition.exercise_id == UUID("b0000000-0000-4000-8000-000000000012")
    assert first.exposure_progression_policy is not None
    assert first.exposure_progression_policy.maximum_initial_dose == 6
    assert (
        repository.get_introductory_exposure_dose_policy(first.introductory_exposure_dose_policy.id)
        == first.introductory_exposure_dose_policy
    )
    assert first.created_introductory_exposure_dose_policy is True
    assert first.created_exposure_definition is True
    assert first.created_exposure_progression_policy is True
    assert second.decision_record_created is False


def test_explosive_power_bundle_requires_resource_review_and_persists_fixed_dose(
    session: Session,
) -> None:
    authority = _authority()
    repository = DomainRepository(session)
    _persist_prerequisites(session, authority)
    blocked = next(
        item
        for item in list_training_construction_candidates(
            session, projected_at=JUMP_TRAINING_NOW
        ).items
        if item.candidate.candidate_id == JUMP_TRAINING_CANDIDATE_ID
    )
    assert blocked.status == "blocked"
    assert any("resource-governance" in issue for issue in blocked.issues)

    resource = next(
        item
        for item in list_resource_governance_candidates(
            session, projected_at=JUMP_TRAINING_NOW - timedelta(minutes=20)
        ).items
        if item.candidate.candidate_id == JUMP_RESOURCE_CANDIDATE_ID
    )
    ratify_resource_governance_candidate(
        session,
        JUMP_RESOURCE_CANDIDATE_ID,
        RatifyResourceGovernanceCandidateCommand(
            candidate_version=RESOURCE_CANDIDATE_VERSION,
            content_digest=resource.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=JUMP_TRAINING_NOW - timedelta(minutes=15),
    )
    available = next(
        item
        for item in list_training_construction_candidates(
            session, projected_at=JUMP_TRAINING_NOW - timedelta(minutes=10)
        ).items
        if item.candidate.candidate_id == JUMP_TRAINING_CANDIDATE_ID
    )

    first = ratify_training_construction_candidate(
        session,
        JUMP_TRAINING_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=CANDIDATE_VERSION,
            content_digest=available.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=JUMP_TRAINING_NOW,
    )
    second = ratify_training_construction_candidate(
        session,
        JUMP_TRAINING_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=CANDIDATE_VERSION,
            content_digest=available.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=JUMP_TRAINING_NOW + timedelta(minutes=1),
    )

    assert available.status == "available"
    assert first.fixed_repetition_dose_policy is not None
    assert first.fixed_repetition_dose_policy.estimate_scope == (
        "assessment_specific:countermovement_vertical_jump_height_cm"
    )
    assert first.fixed_repetition_dose_policy.sets == 3
    assert first.fixed_repetition_dose_policy.repetitions_per_set == 3
    assert first.fixed_repetition_dose_policy.numeric_value_origin == "engineering_judgment"
    assert first.progression_policy.exposure_type is not None
    assert first.exposure_definition is not None
    assert first.exposure_progression_policy is not None
    assert first.exposure_progression_policy.maximum_initial_dose == 9
    assert first.block_review_policy is not None
    assert first.block_review_policy.minimum_adherence_ratio == 0.8
    assert first.response_evaluation_authority is not None
    assert first.response_evaluation_authority.minimum_meaningful_change == 2
    assert first.response_evaluation_authority.numeric_value_origin == "engineering_judgment"
    assert first.response_evaluation_authority.estimate_scope == (
        "assessment_specific:countermovement_vertical_jump_height_cm"
    )
    assert first.created_fixed_repetition_dose_policy is True
    assert first.created_exposure_definition is True
    assert first.created_exposure_progression_policy is True
    assert first.created_block_review_policy is True
    assert (
        repository.get_block_review_policy(first.block_review_policy.id)
        == first.block_review_policy
    )
    operational = list_operational_response_evaluation_authorities(session)
    assert len(operational) == 1
    assert operational[0].authority == first.response_evaluation_authority
    assert operational[0].block_review_policy == first.block_review_policy
    assert second.decision_record_created is False


def test_jump_maintenance_bundle_is_separate_and_scoped_to_maintain(
    session: Session,
) -> None:
    authority = _authority()
    repository = DomainRepository(session)
    _persist_prerequisites(session, authority)
    resource = next(
        item
        for item in list_resource_governance_candidates(
            session, projected_at=JUMP_MAINTENANCE_NOW - timedelta(minutes=20)
        ).items
        if item.candidate.candidate_id == JUMP_MAINTENANCE_RESOURCE_CANDIDATE_ID
    )
    ratify_resource_governance_candidate(
        session,
        JUMP_MAINTENANCE_RESOURCE_CANDIDATE_ID,
        RatifyResourceGovernanceCandidateCommand(
            candidate_version=RESOURCE_CANDIDATE_VERSION,
            content_digest=resource.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=JUMP_MAINTENANCE_NOW - timedelta(minutes=15),
    )
    available = next(
        item
        for item in list_training_construction_candidates(
            session, projected_at=JUMP_MAINTENANCE_NOW - timedelta(minutes=10)
        ).items
        if item.candidate.candidate_id == JUMP_MAINTENANCE_CANDIDATE_ID
    )

    result = ratify_training_construction_candidate(
        session,
        JUMP_MAINTENANCE_CANDIDATE_ID,
        RatifyTrainingConstructionCandidateCommand(
            candidate_version=CANDIDATE_VERSION,
            content_digest=available.candidate.content_digest,
            approval_attestation=True,
        ),
        authority,
        ratified_at=JUMP_MAINTENANCE_NOW,
    )

    assert available.status == "available"
    assert result.fixed_repetition_dose_policy is not None
    assert result.fixed_repetition_dose_policy.priority_state is TrainingPriorityState.MAINTAIN
    assert result.fixed_repetition_dose_policy.sets == 2
    assert result.fixed_repetition_dose_policy.repetitions_per_set == 3
    assert result.fixed_repetition_dose_policy.planned_duration_minutes == 6
    assert result.fixed_repetition_dose_policy.numeric_value_origin == "engineering_judgment"
    assert result.progression_policy.maximum_session_rpe == 5
    assert result.block_review_policy is not None
    assert result.block_review_policy.minimum_adherence_ratio == 0.8
    assert result.response_evaluation_authority is not None
    assert result.response_evaluation_authority.minimum_meaningful_change == 0
    assert result.response_evaluation_authority.numeric_value_origin == "engineering_judgment"
    assert result.response_evaluation_authority.estimate_scope == (
        "assessment_specific:countermovement_vertical_jump_height_cm"
    )
    assert (
        repository.get_fixed_repetition_dose_policy(result.fixed_repetition_dose_policy.id)
        == result.fixed_repetition_dose_policy
    )
    develop = prepared_training_construction_candidate_for_scope(
        result.fixed_repetition_dose_policy.estimate_scope,
        TrainingPriorityState.DEVELOP,
    )
    assert develop.presentation.candidate_id == JUMP_TRAINING_CANDIDATE_ID
    assert develop.release.fixed_repetition_dose_policy is not None
    assert develop.release.fixed_repetition_dose_policy.sets == 3
    operational = list_operational_response_evaluation_authorities(session)
    assert len(operational) == 1
    assert operational[0].authority == result.response_evaluation_authority
    assert operational[0].block_review_policy == result.block_review_policy


def test_stale_digest_persists_none_of_the_construction_bundle(session: Session) -> None:
    authority = _authority()
    _persist_prerequisites(session, authority)
    command = _command(session).model_copy(update={"content_digest": f"sha256:{'0' * 64}"})

    with pytest.raises(TrainingConstructionCandidateConflictError, match="refresh and review"):
        ratify_training_construction_candidate(
            session, CANDIDATE_ID, command, authority, ratified_at=NOW
        )

    repository = DomainRepository(session)
    assert repository.get_decision_record(CANDIDATE_ID) is None
    assert (
        repository.get_repetition_dose_policy(UUID("98940000-0000-4000-8000-000000000001")) is None
    )


def test_ratification_persists_one_fixed_repetition_dose_authority(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = _authority()
    _persist_prerequisites(session, authority)
    base = prepared_training_construction_candidate()
    repetition_policy = base.release.repetition_dose_policy
    assert repetition_policy is not None
    fixed_policy = FixedRepetitionDosePolicy(
        created_at=base.release.prepared_at,
        adaptation_id=repetition_policy.adaptation_id,
        estimate_scope=repetition_policy.estimate_scope,
        sets=2,
        repetitions_per_set=3,
        maximum_initial_total_repetitions=6,
        rest_seconds=repetition_policy.rest_seconds,
        effort_rpe_minimum=repetition_policy.effort_rpe_minimum,
        effort_rpe_maximum=repetition_policy.effort_rpe_maximum,
        technique_constraints=repetition_policy.technique_constraints,
        planned_duration_minutes=repetition_policy.planned_duration_minutes,
        progression_policy_id=repetition_policy.progression_policy_id,
        evidence_claim_ids=repetition_policy.evidence_claim_ids,
        numeric_value_origin="engineering_judgment",
        authority_reference="synthetic-fixed-dose-ratification@1.0.0",
        rationale="Exercise the fixed-dose candidate persistence boundary.",
        uncertainty="Synthetic constants are not operational training guidance.",
        policy_version="synthetic-fixed-dose@1.0.0",
    )
    candidate_id = uuid4()
    prepared = base.model_copy(
        update={
            "presentation": base.presentation.model_copy(
                update={
                    "candidate_id": candidate_id,
                    "content_digest": f"sha256:{'a' * 64}",
                    "slug": "synthetic_fixed_repetition_dose",
                }
            ),
            "release": base.release.model_copy(
                update={
                    "repetition_dose_policy": None,
                    "fixed_repetition_dose_policy": fixed_policy,
                }
            ),
        }
    )
    monkeypatch.setattr(
        construction_candidates,
        "prepared_training_construction_candidates",
        lambda: (prepared,),
    )
    command = RatifyTrainingConstructionCandidateCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=prepared.presentation.content_digest,
        approval_attestation=True,
    )

    first = ratify_training_construction_candidate(
        session, candidate_id, command, authority, ratified_at=NOW
    )
    second = ratify_training_construction_candidate(
        session, candidate_id, command, authority, ratified_at=NOW + timedelta(minutes=1)
    )

    assert first.repetition_dose_policy is None
    assert first.fixed_repetition_dose_policy == fixed_policy
    assert first.created_fixed_repetition_dose_policy is True
    assert (
        DomainRepository(session).get_fixed_repetition_dose_policy(fixed_policy.id) == fixed_policy
    )
    assert second.created_fixed_repetition_dose_policy is False
    assert second.decision_record_created is False


def test_ratification_persists_one_fixed_duration_dose_authority(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = _authority()
    _persist_prerequisites(session, authority)
    base = prepared_training_construction_candidate()
    repetition_policy = base.release.repetition_dose_policy
    assert repetition_policy is not None
    duration_policy = FixedDurationDosePolicy(
        created_at=base.release.prepared_at,
        adaptation_id=repetition_policy.adaptation_id,
        estimate_scope=repetition_policy.estimate_scope,
        sets=1,
        duration_seconds_per_set=600,
        maximum_initial_total_duration_seconds=600,
        rest_seconds=0,
        effort_rpe_minimum=3,
        effort_rpe_maximum=5,
        technique_constraints=("Maintain continuous controlled cyclic work.",),
        planned_duration_minutes=10,
        progression_policy_id=repetition_policy.progression_policy_id,
        evidence_claim_ids=repetition_policy.evidence_claim_ids,
        numeric_value_origin="engineering_judgment",
        authority_reference="synthetic-fixed-duration-ratification@1.0.0",
        rationale="Exercise the fixed-duration candidate persistence boundary.",
        uncertainty="Synthetic constants are not operational training guidance.",
        policy_version="synthetic-fixed-duration@1.0.0",
    )
    candidate_id = uuid4()
    prepared = base.model_copy(
        update={
            "presentation": base.presentation.model_copy(
                update={
                    "candidate_id": candidate_id,
                    "content_digest": f"sha256:{'c' * 64}",
                    "slug": "synthetic_fixed_duration_dose",
                }
            ),
            "release": base.release.model_copy(
                update={
                    "repetition_dose_policy": None,
                    "fixed_duration_dose_policy": duration_policy,
                }
            ),
        }
    )
    monkeypatch.setattr(
        construction_candidates,
        "prepared_training_construction_candidates",
        lambda: (prepared,),
    )
    command = RatifyTrainingConstructionCandidateCommand(
        candidate_version=CANDIDATE_VERSION,
        content_digest=prepared.presentation.content_digest,
        approval_attestation=True,
    )

    first = ratify_training_construction_candidate(
        session, candidate_id, command, authority, ratified_at=NOW
    )
    second = ratify_training_construction_candidate(
        session, candidate_id, command, authority, ratified_at=NOW + timedelta(minutes=1)
    )

    assert first.repetition_dose_policy is None
    assert first.fixed_duration_dose_policy == duration_policy
    assert first.created_fixed_duration_dose_policy is True
    assert (
        DomainRepository(session).get_fixed_duration_dose_policy(duration_policy.id)
        == duration_policy
    )
    assert second.created_fixed_duration_dose_policy is False
    assert second.decision_record_created is False


def test_endpoints_require_role_and_ratify_one_batch(session: Session) -> None:
    account, assignment, _, _ = set_account_role(
        session,
        issuer="urn:agas:development",
        subject="construction-reviewer",
        role=AccountRole.PLANNING_REVIEWER,
        status=AccountRoleStatus.ACTIVE,
        assigned_at=NOW - timedelta(days=2),
        rationale="Training-construction endpoint test.",
    )
    authority = AuthorizedRole(
        account_id=account.id,
        assignment_id=assignment.id,
        role=assignment.role,
        assigned_at=assignment.assigned_at,
    )
    _persist_prerequisites(session, authority)

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[database_session_dependency] = override_session
    app.dependency_overrides.pop(authenticated_principal_dependency, None)
    try:
        client = TestClient(app)
        unauthenticated = client.get("/v1/operator/training-construction-candidates")
        projected = client.get(
            "/v1/operator/training-construction-candidates",
            headers={"Authorization": "Bearer dev.construction-reviewer"},
        )
        candidate = projected.json()["items"][0]["candidate"]
        ratified = client.post(
            f"/v1/operator/training-construction-candidates/{candidate['candidate_id']}/ratifications",
            headers={"Authorization": "Bearer dev.construction-reviewer"},
            json={
                "candidate_version": candidate["candidate_version"],
                "content_digest": candidate["content_digest"],
                "approval_attestation": True,
            },
        )
    finally:
        app.dependency_overrides.pop(database_session_dependency, None)

    assert unauthenticated.status_code == 401
    assert projected.status_code == 200
    assert ratified.status_code == 201
    assert ratified.json()["repetition_dose_policy"]["sets"] == 2
