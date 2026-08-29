from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from uuid import UUID

from agas_domain import (
    AssessmentReviewDecision,
    CompetencyFloorReview,
    PriorityPolicyReview,
    WeeklySchedulingPolicyReview,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.database import database_session


def record_competency_floor_review(
    session: Session,
    *,
    competency_floor_id: UUID,
    decision: AssessmentReviewDecision,
    evidence_claim_ids: tuple[UUID, ...],
    reviewed_at: datetime,
    reviewed_by: str,
    applicability_rationale: str,
    uncertainty: str,
    review_version: str,
) -> CompetencyFloorReview:
    """Append one operator-reviewed governance decision for a competency floor."""

    repository = DomainRepository(session)
    current = repository.get_current_competency_floor_review(competency_floor_id)
    review = CompetencyFloorReview(
        competency_floor_id=competency_floor_id,
        decision=decision,
        sequence_number=1 if current is None else current.sequence_number + 1,
        supersedes_review_id=None if current is None else current.id,
        evidence_claim_ids=evidence_claim_ids,
        reviewed_at=reviewed_at,
        reviewed_by=reviewed_by,
        applicability_rationale=applicability_rationale,
        uncertainty=uncertainty,
        review_version=review_version,
    )
    repository.add_competency_floor_review(review)
    _commit_review(session, "competency floor")
    return review


def record_priority_policy_review(
    session: Session,
    *,
    priority_policy_id: UUID,
    decision: AssessmentReviewDecision,
    evidence_claim_ids: tuple[UUID, ...],
    reviewed_at: datetime,
    reviewed_by: str,
    applicability_rationale: str,
    uncertainty: str,
    review_version: str,
) -> PriorityPolicyReview:
    """Append one operator-reviewed governance decision for a priority policy."""

    repository = DomainRepository(session)
    current = repository.get_current_priority_policy_review(priority_policy_id)
    review = PriorityPolicyReview(
        priority_policy_id=priority_policy_id,
        decision=decision,
        sequence_number=1 if current is None else current.sequence_number + 1,
        supersedes_review_id=None if current is None else current.id,
        evidence_claim_ids=evidence_claim_ids,
        reviewed_at=reviewed_at,
        reviewed_by=reviewed_by,
        applicability_rationale=applicability_rationale,
        uncertainty=uncertainty,
        review_version=review_version,
    )
    repository.add_priority_policy_review(review)
    _commit_review(session, "priority policy")
    return review


def record_weekly_scheduling_policy_review(
    session: Session,
    *,
    weekly_scheduling_policy_id: UUID,
    decision: AssessmentReviewDecision,
    evidence_claim_ids: tuple[UUID, ...],
    reviewed_at: datetime,
    reviewed_by: str,
    applicability_rationale: str,
    uncertainty: str,
    review_version: str,
) -> WeeklySchedulingPolicyReview:
    """Append one operator-reviewed governance decision for a scheduling policy."""

    repository = DomainRepository(session)
    current = repository.get_current_weekly_scheduling_policy_review(weekly_scheduling_policy_id)
    review = WeeklySchedulingPolicyReview(
        weekly_scheduling_policy_id=weekly_scheduling_policy_id,
        decision=decision,
        sequence_number=1 if current is None else current.sequence_number + 1,
        supersedes_review_id=None if current is None else current.id,
        evidence_claim_ids=evidence_claim_ids,
        reviewed_at=reviewed_at,
        reviewed_by=reviewed_by,
        applicability_rationale=applicability_rationale,
        uncertainty=uncertainty,
        review_version=review_version,
    )
    repository.add_weekly_scheduling_policy_review(review)
    _commit_review(session, "weekly scheduling policy")
    return review


def _commit_review(session: Session, authority_label: str) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DomainIntegrityError(
            f"the review conflicts with the current {authority_label} review chain"
        ) from error


def _add_review_arguments(parser: argparse.ArgumentParser, authority_option: str) -> None:
    parser.add_argument(authority_option, type=UUID, required=True)
    parser.add_argument(
        "--decision",
        type=AssessmentReviewDecision,
        choices=tuple(AssessmentReviewDecision),
        required=True,
    )
    parser.add_argument("--evidence-claim-id", type=UUID, action="append", required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--applicability-rationale", required=True)
    parser.add_argument("--uncertainty", required=True)
    parser.add_argument("--review-version", required=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Append reviewed competency-floor, priority-policy, and weekly-scheduling-policy "
            "governance decisions."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    floor_parser = subparsers.add_parser("review-floor")
    _add_review_arguments(floor_parser, "--competency-floor-id")
    policy_parser = subparsers.add_parser("review-priority-policy")
    _add_review_arguments(policy_parser, "--priority-policy-id")
    scheduling_parser = subparsers.add_parser("review-weekly-scheduling-policy")
    _add_review_arguments(scheduling_parser, "--weekly-scheduling-policy-id")
    arguments = parser.parse_args()

    try:
        with database_session() as session:
            common = {
                "decision": arguments.decision,
                "evidence_claim_ids": tuple(arguments.evidence_claim_id),
                "reviewed_at": datetime.now(UTC),
                "reviewed_by": arguments.reviewed_by,
                "applicability_rationale": arguments.applicability_rationale,
                "uncertainty": arguments.uncertainty,
                "review_version": arguments.review_version,
            }
            if arguments.command == "review-floor":
                review = record_competency_floor_review(
                    session,
                    competency_floor_id=arguments.competency_floor_id,
                    **common,
                )
                authority_type = "competency_floor"
                authority_id = review.competency_floor_id
                review_id = review.id
                review_decision = review.decision
                sequence_number = review.sequence_number
            elif arguments.command == "review-priority-policy":
                policy_review = record_priority_policy_review(
                    session,
                    priority_policy_id=arguments.priority_policy_id,
                    **common,
                )
                authority_type = "priority_policy"
                authority_id = policy_review.priority_policy_id
                review_id = policy_review.id
                review_decision = policy_review.decision
                sequence_number = policy_review.sequence_number
            elif arguments.command == "review-weekly-scheduling-policy":
                scheduling_review = record_weekly_scheduling_policy_review(
                    session,
                    weekly_scheduling_policy_id=(arguments.weekly_scheduling_policy_id),
                    **common,
                )
                authority_type = "weekly_scheduling_policy"
                authority_id = scheduling_review.weekly_scheduling_policy_id
                review_id = scheduling_review.id
                review_decision = scheduling_review.decision
                sequence_number = scheduling_review.sequence_number
            else:
                parser.error("unsupported planning-governance administration command")
    except ValueError as error:
        parser.error(str(error))

    print(
        json.dumps(
            {
                "authority_id": str(authority_id),
                "authority_type": authority_type,
                "decision": review_decision.value,
                "review_id": str(review_id),
                "sequence_number": sequence_number,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
