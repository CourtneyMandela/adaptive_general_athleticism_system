from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from agas_api.database import database_session
from agas_api.environment_prescription_revision import (
    CreateEnvironmentPrescriptionRevisionsCommand,
    EnvironmentPrescriptionRevisionResult,
    EnvironmentPrescriptionRevisionUseCaseError,
    PersistedEnvironmentPrescriptionRevisionService,
)


def load_environment_prescription_revisions_command(
    path: Path,
) -> CreateEnvironmentPrescriptionRevisionsCommand:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"could not read environment-revision input: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"environment-revision input is not valid JSON: {error}") from error
    try:
        return CreateEnvironmentPrescriptionRevisionsCommand.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"environment-revision input is invalid: {error}") from error


def create_reviewed_environment_prescription_revisions(
    session: Session,
    *,
    source_weekly_plan_id: UUID,
    command: CreateEnvironmentPrescriptionRevisionsCommand,
) -> EnvironmentPrescriptionRevisionResult:
    return PersistedEnvironmentPrescriptionRevisionService(session).execute(
        source_weekly_plan_id,
        command,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Append reviewed environment-driven prescription revisions for a closed weekly plan."
        )
    )
    parser.add_argument("--source-weekly-plan-id", type=UUID, required=True)
    parser.add_argument("--input-file", type=Path, required=True)
    arguments = parser.parse_args()

    try:
        command = load_environment_prescription_revisions_command(arguments.input_file)
        with database_session() as session:
            result = create_reviewed_environment_prescription_revisions(
                session,
                source_weekly_plan_id=arguments.source_weekly_plan_id,
                command=command,
            )
    except (ValueError, EnvironmentPrescriptionRevisionUseCaseError) as error:
        parser.error(str(error))

    print(
        json.dumps(
            {
                "source_weekly_plan_id": str(arguments.source_weekly_plan_id),
                "decision_record_id": str(result.decision_record.id),
                "revised_prescription_ids": [str(item.id) for item in result.revised_prescriptions],
                "resolution_ids": [
                    str(item.exercise_resolution_id) for item in result.revised_prescriptions
                ],
                "reviewed_by": command.reviewed_by,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
