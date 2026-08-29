from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from agas_api.database import database_session
from agas_api.initial_planning import (
    CreateInitialStrategyCommand,
    InitialPlanningUseCaseError,
    InitialStrategyCreationResult,
    PersistedInitialPlanningService,
)


def load_initial_planning_command(path: Path) -> CreateInitialStrategyCommand:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"could not read initial-planning input: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"initial-planning input is not valid JSON: {error}") from error
    try:
        return CreateInitialStrategyCommand.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"initial-planning input is invalid: {error}") from error


def create_reviewed_initial_strategy(
    session: Session,
    *,
    athlete_id: UUID,
    command: CreateInitialStrategyCommand,
) -> InitialStrategyCreationResult:
    """Execute reviewed initial planning outside the athlete-facing transport boundary."""

    return PersistedInitialPlanningService(session).execute(athlete_id, command)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create one reviewed initial strategy from an operator-approved JSON input file."
        )
    )
    parser.add_argument("--athlete-id", type=UUID, required=True)
    parser.add_argument("--input-file", type=Path, required=True)
    arguments = parser.parse_args()

    try:
        command = load_initial_planning_command(arguments.input_file)
        with database_session() as session:
            result = create_reviewed_initial_strategy(
                session,
                athlete_id=arguments.athlete_id,
                command=command,
            )
    except (ValueError, InitialPlanningUseCaseError) as error:
        parser.error(str(error))

    print(
        json.dumps(
            {
                "athlete_id": str(result.strategy.athlete_id),
                "strategy_id": str(result.strategy.id),
                "decision_record_id": str(result.decision_record.id),
                "capability_need_ids": [str(item.id) for item in result.capability_needs],
                "reviewed_by": command.reviewed_by,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
