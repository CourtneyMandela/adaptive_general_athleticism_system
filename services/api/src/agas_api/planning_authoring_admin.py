from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from agas_api.block_creation import (
    BlockCreationUseCaseError,
    BlockPlanCreationResult,
    CreateBlockPlanCommand,
    PersistedBlockCreationService,
)
from agas_api.database import database_session
from agas_api.exercise_reresolution import (
    ExerciseReResolutionResult,
    ExerciseReResolutionUseCaseError,
    PersistedExerciseReResolutionService,
    ReResolveExerciseCommand,
)
from agas_api.resource_preparation import (
    PersistedResourcePreparationService,
    ResourceDemandPreparationCommand,
    ResourceDemandPreparationResult,
    ResourcePreparationUseCaseError,
)

_RESOURCE_COMMAND_ADAPTER: TypeAdapter[ResourceDemandPreparationCommand] = TypeAdapter(
    ResourceDemandPreparationCommand
)


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"could not read {label} input: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} input is not valid JSON: {error}") from error


def load_resource_demand_command(path: Path) -> ResourceDemandPreparationCommand:
    try:
        return _RESOURCE_COMMAND_ADAPTER.validate_python(_load_json(path, "resource-demand"))
    except ValidationError as error:
        raise ValueError(f"resource-demand input is invalid: {error}") from error


def load_block_plan_command(path: Path) -> CreateBlockPlanCommand:
    try:
        return CreateBlockPlanCommand.model_validate(_load_json(path, "block-plan"))
    except ValidationError as error:
        raise ValueError(f"block-plan input is invalid: {error}") from error


def load_exercise_reresolution_command(path: Path) -> ReResolveExerciseCommand:
    try:
        return ReResolveExerciseCommand.model_validate(_load_json(path, "exercise-reresolution"))
    except ValidationError as error:
        raise ValueError(f"exercise-reresolution input is invalid: {error}") from error


def create_reviewed_resource_demand(
    session: Session,
    *,
    strategy_id: UUID,
    priority_id: UUID,
    command: ResourceDemandPreparationCommand,
) -> ResourceDemandPreparationResult:
    return PersistedResourcePreparationService(session).execute(
        strategy_id,
        priority_id,
        command,
    )


def create_reviewed_block_plan(
    session: Session,
    *,
    strategy_id: UUID,
    command: CreateBlockPlanCommand,
) -> BlockPlanCreationResult:
    return PersistedBlockCreationService(session).execute(strategy_id, command)


def create_reviewed_exercise_reresolution(
    session: Session,
    *,
    stimulus_requirement_id: UUID,
    command: ReResolveExerciseCommand,
) -> ExerciseReResolutionResult:
    return PersistedExerciseReResolutionService(session).execute(
        stimulus_requirement_id,
        command,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create reviewed resource demands, exercise re-resolutions, and block plans outside "
            "the athlete API."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demand_parser = subparsers.add_parser("prepare-demand")
    demand_parser.add_argument("--strategy-id", type=UUID, required=True)
    demand_parser.add_argument("--priority-id", type=UUID, required=True)
    demand_parser.add_argument("--input-file", type=Path, required=True)

    block_parser = subparsers.add_parser("create-block")
    block_parser.add_argument("--strategy-id", type=UUID, required=True)
    block_parser.add_argument("--input-file", type=Path, required=True)

    reresolution_parser = subparsers.add_parser("reresolve-exercise")
    reresolution_parser.add_argument("--stimulus-requirement-id", type=UUID, required=True)
    reresolution_parser.add_argument("--input-file", type=Path, required=True)
    arguments = parser.parse_args()

    try:
        with database_session() as session:
            if arguments.command == "prepare-demand":
                demand_command = load_resource_demand_command(arguments.input_file)
                demand_result = create_reviewed_resource_demand(
                    session,
                    strategy_id=arguments.strategy_id,
                    priority_id=arguments.priority_id,
                    command=demand_command,
                )
                output = {
                    "strategy_id": str(demand_result.resource_demand.long_range_strategy_id),
                    "priority_id": str(demand_result.resource_demand.adaptation_priority_id),
                    "resource_demand_id": str(demand_result.resource_demand.id),
                    "stimulus_requirement_id": (
                        str(demand_result.stimulus_requirement.id)
                        if demand_result.stimulus_requirement is not None
                        else None
                    ),
                    "exercise_resolution_id": (
                        str(demand_result.exercise_resolution.id)
                        if demand_result.exercise_resolution is not None
                        else None
                    ),
                    "decision_record_id": str(demand_result.decision_record.id),
                    "reviewed_by": demand_command.reviewed_by,
                }
            elif arguments.command == "create-block":
                block_command = load_block_plan_command(arguments.input_file)
                block_result = create_reviewed_block_plan(
                    session,
                    strategy_id=arguments.strategy_id,
                    command=block_command,
                )
                output = {
                    "strategy_id": str(block_result.block_plan.long_range_strategy_id),
                    "block_plan_id": str(block_result.block_plan.id),
                    "block_status": block_result.block_plan.status.value,
                    "decision_record_id": str(block_result.decision_record.id),
                    "reviewed_by": block_command.reviewed_by,
                }
            elif arguments.command == "reresolve-exercise":
                reresolution_command = load_exercise_reresolution_command(arguments.input_file)
                reresolution_result = create_reviewed_exercise_reresolution(
                    session,
                    stimulus_requirement_id=arguments.stimulus_requirement_id,
                    command=reresolution_command,
                )
                output = {
                    "stimulus_requirement_id": str(
                        reresolution_result.exercise_resolution.stimulus_requirement_id
                    ),
                    "exercise_resolution_id": str(reresolution_result.exercise_resolution.id),
                    "resolution_status": (reresolution_result.exercise_resolution.status.value),
                    "selected_exercise_id": (
                        str(reresolution_result.exercise_resolution.selected_exercise_id)
                        if reresolution_result.exercise_resolution.selected_exercise_id is not None
                        else None
                    ),
                    "decision_record_id": str(reresolution_result.decision_record.id),
                    "reviewed_by": reresolution_command.reviewed_by,
                }
            else:
                parser.error("unsupported planning-authoring command")
    except (
        ValueError,
        ResourcePreparationUseCaseError,
        ExerciseReResolutionUseCaseError,
        BlockCreationUseCaseError,
    ) as error:
        parser.error(str(error))

    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
