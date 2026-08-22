from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from uuid import UUID

from agas_domain import AthleteSafetyPolicyAssignment
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.database import database_session

ASSIGNMENT_RULE_VERSION = "athlete-safety-policy-assignment@1.0.0"


def assign_session_safety_policy(
    session: Session,
    *,
    athlete_id: UUID,
    safety_policy_id: UUID,
    assigned_at: datetime,
    assigned_by: str,
    applicability_rationale: str,
) -> tuple[AthleteSafetyPolicyAssignment, bool]:
    """Append an explicitly reviewed athlete-policy assignment or return the existing match."""

    repository = DomainRepository(session)
    if repository.get_athlete(athlete_id) is None:
        raise DomainIntegrityError("athlete does not exist")
    if repository.get_session_safety_policy(safety_policy_id) is None:
        raise DomainIntegrityError("session safety policy does not exist")
    current = repository.get_current_athlete_safety_policy_assignment(athlete_id)
    if current is not None and current.safety_policy_id == safety_policy_id:
        return current, False
    assignment = AthleteSafetyPolicyAssignment(
        athlete_id=athlete_id,
        safety_policy_id=safety_policy_id,
        sequence_number=1 if current is None else current.sequence_number + 1,
        supersedes_assignment_id=None if current is None else current.id,
        assigned_at=assigned_at,
        assigned_by=assigned_by,
        applicability_rationale=applicability_rationale,
        rule_version=ASSIGNMENT_RULE_VERSION,
    )
    repository.add_athlete_safety_policy_assignment(assignment)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DomainIntegrityError(
            "the assignment conflicts with the current athlete safety-policy chain"
        ) from error
    return assignment, True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assign reviewed safety policies without exposing athlete self-selection."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    assign_parser = subparsers.add_parser("assign", help="Assign a policy to one athlete")
    assign_parser.add_argument("--athlete-id", type=UUID, required=True)
    assign_parser.add_argument("--safety-policy-id", type=UUID, required=True)
    assign_parser.add_argument("--assigned-by", required=True)
    assign_parser.add_argument("--applicability-rationale", required=True)
    arguments = parser.parse_args()

    if arguments.command != "assign":
        parser.error("unsupported safety-policy administration command")
    try:
        with database_session() as session:
            assignment, created = assign_session_safety_policy(
                session,
                athlete_id=arguments.athlete_id,
                safety_policy_id=arguments.safety_policy_id,
                assigned_at=datetime.now(UTC),
                assigned_by=arguments.assigned_by,
                applicability_rationale=arguments.applicability_rationale,
            )
    except ValueError as error:
        parser.error(str(error))
    print(
        json.dumps(
            {
                "assignment_created": created,
                "assignment_id": str(assignment.id),
                "athlete_id": str(assignment.athlete_id),
                "safety_policy_id": str(assignment.safety_policy_id),
                "sequence_number": assignment.sequence_number,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
