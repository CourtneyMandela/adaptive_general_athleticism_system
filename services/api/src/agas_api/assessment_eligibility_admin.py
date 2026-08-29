from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from uuid import UUID

from agas_domain import AssessmentEligibilityOutcome, AssessmentEligibilityReview
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.database import database_session

ELIGIBILITY_RULE_VERSION = "assessment-eligibility-review@1.0.0"


def record_assessment_eligibility_review(
    session: Session,
    *,
    athlete_id: UUID,
    outcome: AssessmentEligibilityOutcome,
    source_observation_ids: tuple[UUID, ...],
    reviewed_at: datetime,
    valid_until: datetime,
    reviewed_by: str,
    screening_process_reference: str,
    rationale: str,
    uncertainty: str,
) -> tuple[AssessmentEligibilityReview, bool]:
    """Append one operator-reviewed eligibility decision or return the identical current review."""

    repository = DomainRepository(session)
    current = repository.get_current_assessment_eligibility_review(athlete_id)
    if current is not None and (
        current.outcome == outcome
        and current.source_observation_ids == source_observation_ids
        and current.valid_until == valid_until
        and current.reviewed_by == reviewed_by
        and current.screening_process_reference == screening_process_reference
        and current.rationale == rationale
        and current.uncertainty == uncertainty
        and current.rule_version == ELIGIBILITY_RULE_VERSION
    ):
        return current, False

    review = AssessmentEligibilityReview(
        athlete_id=athlete_id,
        outcome=outcome,
        sequence_number=1 if current is None else current.sequence_number + 1,
        supersedes_review_id=None if current is None else current.id,
        source_observation_ids=source_observation_ids,
        reviewed_at=reviewed_at,
        valid_until=valid_until,
        reviewed_by=reviewed_by,
        screening_process_reference=screening_process_reference,
        rationale=rationale,
        uncertainty=uncertainty,
        rule_version=ELIGIBILITY_RULE_VERSION,
    )
    repository.add_assessment_eligibility_review(review)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DomainIntegrityError(
            "the review conflicts with the current assessment eligibility chain"
        ) from error
    return review, True


def _aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must include a timezone")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record assessment eligibility without exposing athlete self-authorization."
    )
    parser.add_argument("--athlete-id", type=UUID, required=True)
    parser.add_argument(
        "--outcome", type=AssessmentEligibilityOutcome, choices=AssessmentEligibilityOutcome
    )
    parser.add_argument("--source-observation-id", type=UUID, action="append", required=True)
    parser.add_argument("--valid-until", type=_aware_datetime, required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--screening-process-reference", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--uncertainty", required=True)
    arguments = parser.parse_args()

    try:
        with database_session() as session:
            review, created = record_assessment_eligibility_review(
                session,
                athlete_id=arguments.athlete_id,
                outcome=arguments.outcome,
                source_observation_ids=tuple(arguments.source_observation_id),
                reviewed_at=datetime.now(UTC),
                valid_until=arguments.valid_until,
                reviewed_by=arguments.reviewed_by,
                screening_process_reference=arguments.screening_process_reference,
                rationale=arguments.rationale,
                uncertainty=arguments.uncertainty,
            )
    except ValueError as error:
        parser.error(str(error))

    print(
        json.dumps(
            {
                "review_created": created,
                "review_id": str(review.id),
                "athlete_id": str(review.athlete_id),
                "outcome": review.outcome.value,
                "sequence_number": review.sequence_number,
                "valid_until": review.valid_until.isoformat(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
