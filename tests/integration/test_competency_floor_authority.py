import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from agas_domain import (
    AssessmentReviewDecision,
    CapabilityDomain,
    ComparisonDirection,
    CompetencyFloor,
    CompetencyFloorAuthority,
    CompetencyFloorAuthorityKind,
    CompetencyFloorAuthorityReview,
    CompetencyFloorReview,
    EvidenceSourceIdentifier,
)
from agas_domain.persistence.models import (
    CompetencyFloorAuthorityRecord,
    ImmutableHistoricalRecordError,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import ValidationError
from sqlalchemy.orm import Session

NOW = datetime(2026, 9, 12, 17, 0, tzinfo=UTC)
AUTHORITY_ID = UUID("98700000-0000-4000-8000-000000000001")
AUTHORITY_REVIEW_ID = UUID("98700000-0000-4000-8000-000000000002")
FLOOR_ID = UUID("98700000-0000-4000-8000-000000000003")
FLOOR_REVIEW_ID = UUID("98700000-0000-4000-8000-000000000004")


def _authority(*, content_digest: str | None = None) -> CompetencyFloorAuthority:
    values = {
        "id": AUTHORITY_ID,
        "schema_version": "1.0.0",
        "created_at": NOW,
        "authority_kind": CompetencyFloorAuthorityKind.PROFESSIONAL_JUDGMENT,
        "statement": "Use 100 metres as the test distance for this scoped carry floor.",
        "scope": "assessment_specific:loaded_carry_distance_at_relative_load",
        "population": "Owner-only alpha; recreationally trained adult doing physical work.",
        "rationale": "A bounded proposal requiring accountable professional review.",
        "applicability_notes": "This is not a population norm or safety clearance.",
        "uncertainty": "The value has not been validated as a general athletic competency.",
        "limitations": (
            "The threshold is professional judgment rather than a published population result.",
        ),
        "authored_by": "owner professional judgment candidate",
        "qualification_context": "Credential and adoption must be attested during review.",
        "supporting_evidence_claim_ids": (),
        "authority_version": "owner-alpha-loaded-carry-distance@1.0.0",
    }
    draft = CompetencyFloorAuthority.model_construct(
        **values, content_digest=f"sha256:{'0' * 64}"
    )
    canonical = json.dumps(
        draft.model_dump(mode="json", exclude={"content_digest"}),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = content_digest or f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
    return CompetencyFloorAuthority(**values, content_digest=digest)


def _authority_review(
    *, decision: AssessmentReviewDecision = AssessmentReviewDecision.APPROVED
) -> CompetencyFloorAuthorityReview:
    return CompetencyFloorAuthorityReview(
        id=AUTHORITY_REVIEW_ID,
        created_at=NOW + timedelta(minutes=1),
        authority_id=AUTHORITY_ID,
        decision=decision,
        sequence_number=1,
        reviewed_at=NOW + timedelta(minutes=1),
        reviewed_by="account:owner",
        attestation=(
            "I adopt this exact judgment as an owner-alpha planning authority and understand "
            "that it is not a scientific finding."
        ),
        uncertainty="Approval does not establish population validity or medical safety.",
        review_version="competency-floor-authority-review@1.0.0",
    )


def _floor() -> CompetencyFloor:
    return CompetencyFloor(
        id=FLOOR_ID,
        created_at=NOW + timedelta(minutes=2),
        domain=CapabilityDomain.LOADED_LOCOMOTION,
        estimate_scope="assessment_specific:loaded_carry_distance_at_relative_load",
        unit_or_scale="metres",
        threshold=100,
        comparison_direction=ComparisonDirection.HIGHER_IS_BETTER,
        population="Owner-only alpha.",
        minimum_age_years=30,
        maximum_age_years=39,
        applicability_notes="Only a matching governed assessment estimate may be compared.",
        uncertainty="Professional judgment, pending personal calibration.",
        judgment_authority_ids=(AUTHORITY_ID,),
        floor_version="owner-alpha-loaded-carry-floor@1.0.0",
    )


def _floor_review() -> CompetencyFloorReview:
    return CompetencyFloorReview(
        id=FLOOR_REVIEW_ID,
        created_at=NOW + timedelta(minutes=3),
        competency_floor_id=FLOOR_ID,
        decision=AssessmentReviewDecision.APPROVED,
        sequence_number=1,
        judgment_authority_ids=(AUTHORITY_ID,),
        reviewed_at=NOW + timedelta(minutes=3),
        reviewed_by="account:owner",
        applicability_rationale="Use only for this athlete and exact assessment scope.",
        uncertainty="The first personal results may require a replacement authority.",
        review_version="owner-alpha-loaded-carry-floor-review@1.0.0",
    )


def test_authority_digest_and_textbook_identifier_are_explicit() -> None:
    authority = _authority()

    assert authority.authority_kind is CompetencyFloorAuthorityKind.PROFESSIONAL_JUDGMENT
    assert authority.content_digest.startswith("sha256:")
    assert EvidenceSourceIdentifier(scheme="isbn", value="9781975219246").scheme == "isbn"
    with pytest.raises(ValidationError, match="content digest is stale"):
        _authority(content_digest=f"sha256:{'f' * 64}")


def test_professional_judgment_floor_round_trip_preserves_distinct_authority(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    authority = _authority()
    authority_review = _authority_review()
    floor = _floor()
    floor_review = _floor_review()

    repository.add_competency_floor_authority(authority)
    session.flush()
    repository.add_competency_floor_authority_review(authority_review)
    session.flush()
    repository.add_competency_floor(floor)
    session.flush()
    repository.add_competency_floor_review(floor_review)
    session.commit()

    assert repository.get_competency_floor_authority(AUTHORITY_ID) == authority
    assert (
        repository.get_current_competency_floor_authority_review(AUTHORITY_ID)
        == authority_review
    )
    assert repository.get_competency_floor(FLOOR_ID) == floor
    assert repository.get_competency_floor_review(FLOOR_REVIEW_ID) == floor_review
    assert repository.get_competency_floor(FLOOR_ID).evidence_claim_ids == ()  # type: ignore[union-attr]


def test_floor_review_requires_current_approved_authority_attestation(session: Session) -> None:
    repository = DomainRepository(session)
    repository.add_competency_floor_authority(_authority())
    session.flush()
    repository.add_competency_floor(_floor())
    session.flush()

    with pytest.raises(DomainIntegrityError, match="approved judgment authority review"):
        repository.add_competency_floor_review(_floor_review())


def test_authority_history_is_append_only(session: Session) -> None:
    repository = DomainRepository(session)
    repository.add_competency_floor_authority(_authority())
    session.commit()
    record = session.get(CompetencyFloorAuthorityRecord, AUTHORITY_ID)
    assert record is not None
    record.rationale = "Silently changed rationale."

    with pytest.raises(ImmutableHistoricalRecordError, match="append-only"):
        session.commit()


def test_floor_without_any_governing_basis_is_invalid() -> None:
    with pytest.raises(ValidationError, match="requires evidence or a judgment authority"):
        CompetencyFloor.model_validate(
            _floor().model_dump() | {"judgment_authority_ids": ()}
        )
