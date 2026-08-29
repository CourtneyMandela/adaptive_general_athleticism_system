from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from agas_api.database import database_session
from agas_api.weekly_planning import (
    CreateWeeklyPlanCommand,
    PersistedWeeklyPlanService,
    WeeklyPlanCreationResult,
    WeeklyPlanUseCaseError,
)


def load_weekly_plan_command(path: Path) -> CreateWeeklyPlanCommand:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"could not read weekly-planning input: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"weekly-planning input is not valid JSON: {error}") from error
    try:
        return CreateWeeklyPlanCommand.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"weekly-planning input is invalid: {error}") from error


def create_reviewed_weekly_plan(
    session: Session,
    *,
    block_id: UUID,
    command: CreateWeeklyPlanCommand,
) -> WeeklyPlanCreationResult:
    """Create an audited week outside the athlete-facing transport boundary."""

    return PersistedWeeklyPlanService(session).execute(block_id, command)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create one reviewed weekly plan from explicit prescriptions, session composition, "
            "availability, and an approved policy review in a JSON input file."
        )
    )
    parser.add_argument("--block-id", type=UUID, required=True)
    parser.add_argument("--input-file", type=Path, required=True)
    arguments = parser.parse_args()

    try:
        command = load_weekly_plan_command(arguments.input_file)
        with database_session() as session:
            result = create_reviewed_weekly_plan(
                session,
                block_id=arguments.block_id,
                command=command,
            )
    except (ValueError, WeeklyPlanUseCaseError) as error:
        parser.error(str(error))

    print(
        json.dumps(
            {
                "athlete_id": str(result.weekly_plan.athlete_id),
                "block_id": str(result.weekly_plan.block_plan_id),
                "weekly_plan_id": str(result.weekly_plan.id),
                "weekly_plan_status": result.weekly_plan.status.value,
                "decision_record_id": str(result.decision_record.id),
                "prescription_ids": [str(item.id) for item in result.prescriptions],
                "session_template_ids": [str(item.id) for item in result.session_templates],
                "weekly_availability_id": str(result.availability.id),
                "reviewed_by": command.reviewed_by,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
