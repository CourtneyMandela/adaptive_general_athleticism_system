"""Cross-candidate identity checks for immutable governance artifacts."""

from collections import defaultdict
from typing import Any
from uuid import UUID

from agas_api.assessment_governance_candidates import _candidate_registry as assessments
from agas_api.competency_floor_candidates import _candidate_registry as floors
from agas_api.planning_governance_candidates import _candidate_registry as planning
from agas_api.resource_governance_candidates import (
    _evidence_review_id,
    prepared_resource_governance_candidates,
)
from agas_api.training_construction_candidates import prepared_training_construction_candidates


def test_prepared_governance_records_never_reuse_an_identity_for_different_content() -> None:
    """A shared immutable record may recur, but conflicting content may not share its UUID."""

    records: defaultdict[tuple[str, UUID], list[tuple[str, Any]]] = defaultdict(list)

    for assessment_candidate in assessments().values():
        owner = f"assessment:{assessment_candidate.presentation.slug}"
        records[("decision_record", assessment_candidate.release.release_id)].append(
            (owner, owner)
        )
        for source in assessment_candidate.release.sources:
            records[("evidence_source", source.id)].append((owner, source))
        for claim in assessment_candidate.release.claims:
            records[("evidence_claim", claim.id)].append((owner, claim))

    for planning_candidate in planning().values():
        owner = f"planning:{planning_candidate.presentation.slug}"
        records[("decision_record", planning_candidate.release.release_id)].append((owner, owner))
        records[("evidence_source", planning_candidate.release.source.id)].append(
            (owner, planning_candidate.release.source)
        )
        records[("evidence_claim", planning_candidate.release.claim.id)].append(
            (owner, planning_candidate.release.claim)
        )
        records[("evidence_claim_review", planning_candidate.release.evidence_review_id)].append(
            (owner, owner)
        )

    for floor_candidate in floors().values():
        owner = f"competency_floor:{floor_candidate.presentation.slug}"
        records[("decision_record", floor_candidate.release.release_id)].append((owner, owner))
        records[("evidence_source", floor_candidate.release.source.id)].append(
            (owner, floor_candidate.release.source)
        )
        records[("evidence_claim", floor_candidate.release.claim.id)].append(
            (owner, floor_candidate.release.claim)
        )
        records[("evidence_claim_review", floor_candidate.release.evidence_review_id)].append(
            (owner, owner)
        )

    for resource_candidate in prepared_resource_governance_candidates():
        owner = f"resource:{resource_candidate.presentation.release_label}"
        records[("decision_record", resource_candidate.presentation.candidate_id)].append(
            (owner, owner)
        )
        records[("evidence_claim", resource_candidate.release.claim.id)].append(
            (owner, resource_candidate.release.claim)
        )
        records[("evidence_claim_review", _evidence_review_id(resource_candidate))].append(
            (owner, owner)
        )

    for construction_candidate in prepared_training_construction_candidates():
        owner = f"training_construction:{construction_candidate.presentation.slug}"
        records[("decision_record", construction_candidate.presentation.candidate_id)].append(
            (owner, owner)
        )

    conflicts = []
    for (record_type, record_id), uses in records.items():
        first_value = uses[0][1]
        if any(value != first_value for _, value in uses[1:]):
            conflicts.append(
                f"{record_type} {record_id} is assigned to "
                + ", ".join(owner for owner, _ in uses)
            )

    assert conflicts == [], "conflicting governance identities:\n" + "\n".join(conflicts)


def test_prepared_evidence_review_identities_are_globally_unique() -> None:
    """Review rows include reviewer/time at ratification, so their IDs cannot be shared."""

    uses: defaultdict[UUID, list[str]] = defaultdict(list)
    for assessment_candidate in assessments().values():
        for review in assessment_candidate.release.evidence_reviews:
            uses[review.id].append(f"assessment:{assessment_candidate.presentation.slug}")
    for planning_candidate in planning().values():
        uses[planning_candidate.release.evidence_review_id].append(
            f"planning:{planning_candidate.presentation.slug}"
        )
    for floor_candidate in floors().values():
        uses[floor_candidate.release.evidence_review_id].append(
            f"competency_floor:{floor_candidate.presentation.slug}"
        )
    for resource_candidate in prepared_resource_governance_candidates():
        uses[_evidence_review_id(resource_candidate)].append(
            f"resource:{resource_candidate.presentation.release_label}"
        )

    duplicates = {
        str(review_id): owners for review_id, owners in uses.items() if len(owners) > 1
    }
    assert duplicates == {}
