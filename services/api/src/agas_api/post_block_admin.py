from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from agas_api.block_review_application import (
    BlockReviewCreationResult,
    BlockReviewUseCaseError,
    CreateBlockReviewCommand,
    PersistedBlockReviewService,
)
from agas_api.database import database_session
from agas_api.replanning import (
    PersistedReplanningService,
    PostBlockReplanningCommand,
    PostBlockReplanningResult,
    ReplanningUseCaseError,
)


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"could not read {label} input: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} input is not valid JSON: {error}") from error


def load_block_review_command(path: Path) -> CreateBlockReviewCommand:
    try:
        return CreateBlockReviewCommand.model_validate(_load_json(path, "block-review"))
    except ValidationError as error:
        raise ValueError(f"block-review input is invalid: {error}") from error


def load_replanning_command(path: Path) -> PostBlockReplanningCommand:
    try:
        return PostBlockReplanningCommand.model_validate(_load_json(path, "replanning"))
    except ValidationError as error:
        raise ValueError(f"replanning input is invalid: {error}") from error


def create_reviewed_block_review(
    session: Session,
    *,
    block_id: UUID,
    command: CreateBlockReviewCommand,
) -> BlockReviewCreationResult:
    return PersistedBlockReviewService(session).execute(block_id, command)


def create_reviewed_replanning(
    session: Session,
    *,
    block_review_id: UUID,
    command: PostBlockReplanningCommand,
) -> PostBlockReplanningResult:
    return PersistedReplanningService(session).execute(block_review_id, command)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Complete reviewed block review and replanning outside the athlete API."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    review_parser = subparsers.add_parser("review-block")
    review_parser.add_argument("--block-id", type=UUID, required=True)
    review_parser.add_argument("--input-file", type=Path, required=True)

    replan_parser = subparsers.add_parser("replan")
    replan_parser.add_argument("--block-review-id", type=UUID, required=True)
    replan_parser.add_argument("--input-file", type=Path, required=True)
    arguments = parser.parse_args()

    try:
        with database_session() as session:
            if arguments.command == "review-block":
                review_command = load_block_review_command(arguments.input_file)
                review_result = create_reviewed_block_review(
                    session,
                    block_id=arguments.block_id,
                    command=review_command,
                )
                output = {
                    "athlete_id": str(review_result.block_review.athlete_id),
                    "block_id": str(review_result.block_review.block_plan_id),
                    "block_review_id": str(review_result.block_review.id),
                    "block_review_outcome": review_result.block_review.outcome.value,
                    "decision_record_id": str(review_result.decision_record.id),
                    "reviewed_by": review_command.reviewed_by,
                    "training_response_ids": [
                        str(item.id) for item in review_result.training_responses
                    ],
                }
            elif arguments.command == "replan":
                replanning_command = load_replanning_command(arguments.input_file)
                replanning_result = create_reviewed_replanning(
                    session,
                    block_review_id=arguments.block_review_id,
                    command=replanning_command,
                )
                output = {
                    "athlete_id": str(replanning_result.strategy.athlete_id),
                    "block_review_id": str(arguments.block_review_id),
                    "capability_need_ids": [
                        str(item.id) for item in replanning_result.capability_needs
                    ],
                    "decision_record_id": str(replanning_result.decision_record.id),
                    "reviewed_by": replanning_command.reviewed_by,
                    "strategy_id": str(replanning_result.strategy.id),
                    "supersedes_strategy_id": str(
                        replanning_result.strategy.supersedes_strategy_id
                    ),
                }
            else:
                parser.error("unsupported post-block administration command")
    except (ValueError, BlockReviewUseCaseError, ReplanningUseCaseError) as error:
        parser.error(str(error))

    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
