from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from agas_domain import LongRangeStrategy, TrainingPriorityState
from agas_domain.persistence.models import AthleteRecord, LongRangeStrategyRecord
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from agas_api.block_preparation import (
    BlockPreparationNotFoundError,
    BlockPreparationProjectionError,
    BlockPreparationProjector,
)
from agas_api.first_week_preparation import (
    FirstWeekPreparationNotFoundError,
    FirstWeekPreparationProjection,
    FirstWeekPreparationProjectionError,
    FirstWeekPreparationProjector,
)
from agas_api.initial_planning_preparation import (
    InitialPlanningPreparationNotFoundError,
    InitialPlanningPreparationProjectionError,
    InitialPlanningPreparationProjector,
)
from agas_api.resource_demand_preparation import (
    ResourceDemandPreparationNotFoundError,
    ResourceDemandPreparationProjection,
    ResourceDemandPreparationProjectionError,
    ResourceDemandPreparationProjector,
)

PlanningWorkflowStage = Literal[
    "initial_planning",
    "resource_demands",
    "block_creation",
    "first_week",
]
PlanningLifecycleStatus = Literal[
    "capability_estimate_required",
    "capability_estimate_stale",
    "planning_authorities_required",
    "planning_context_review_required",
    "ready_for_explicit_resource_demands",
    "ready_for_explicit_block",
    "ready_for_explicit_first_week",
]


class PlanningReviewQueueItemProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_stage: PlanningWorkflowStage
    status: PlanningLifecycleStatus
    readiness: Literal["ready", "blocked"]
    athlete_id: UUID
    athlete_display_name: str
    strategy_id: UUID | None = None
    block_id: UUID | None = None
    message: str
    issues: tuple[str, ...] = ()


class PlanningReviewQueueProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[PlanningReviewQueueItemProjection, ...]
    projection_version: str = "planning-review-queue@1.0.0"


class PlanningReviewQueueProjectionError(RuntimeError):
    pass


class PlanningReviewQueueProjector:
    """Derive each athlete's next reviewer-owned planning step from persisted history."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)
        self.initial_projector = InitialPlanningPreparationProjector(session)
        self.resource_projector = ResourceDemandPreparationProjector(session)
        self.block_projector = BlockPreparationProjector(session)
        self.first_week_projector = FirstWeekPreparationProjector(session)

    def project(self, projected_at: datetime | None = None) -> PlanningReviewQueueProjection:
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("queue projection time must include a timezone")
        athlete_ids = self.session.scalars(
            select(AthleteRecord.id).order_by(AthleteRecord.display_name, AthleteRecord.id)
        ).all()
        items = []
        try:
            for athlete_id in athlete_ids:
                athlete = self.repository.get_athlete(athlete_id)
                if athlete is None:
                    raise PlanningReviewQueueProjectionError(
                        "athlete disappeared during planning queue projection"
                    )
                strategy = self._current_strategy(athlete.id)
                if strategy is None:
                    initial = self.initial_projector.project(athlete.id, instant)
                    if initial.status == "initial_strategy_exists":
                        raise PlanningReviewQueueProjectionError(
                            "initial strategy state changed during planning queue projection"
                        )
                    ready = initial.status == "planning_context_review_required"
                    items.append(
                        PlanningReviewQueueItemProjection(
                            workflow_stage="initial_planning",
                            status=initial.status,
                            readiness="ready" if ready else "blocked",
                            athlete_id=athlete.id,
                            athlete_display_name=athlete.display_name,
                            message=initial.message,
                            issues=() if ready else (initial.message,),
                        )
                    )
                    continue

                resource = self.resource_projector.project(strategy.id, instant)
                if any(not option.demand_history for option in resource.priorities):
                    issues = self._resource_issues(resource)
                    items.append(
                        PlanningReviewQueueItemProjection(
                            workflow_stage="resource_demands",
                            status="ready_for_explicit_resource_demands",
                            readiness="blocked" if issues else "ready",
                            athlete_id=athlete.id,
                            athlete_display_name=athlete.display_name,
                            strategy_id=strategy.id,
                            message=(
                                "Review explicit stimulus, environment, exercise-resolution, and "
                                "resource-demand inputs for every strategy priority."
                            ),
                            issues=issues,
                        )
                    )
                    continue

                block = self.block_projector.project(strategy.id, instant)
                if not block.existing_blocks:
                    issues = (
                        ()
                        if block.resource_allocation_policies
                        else ("no resource-allocation policy is available",)
                    )
                    items.append(
                        PlanningReviewQueueItemProjection(
                            workflow_stage="block_creation",
                            status="ready_for_explicit_block",
                            readiness="blocked" if issues else "ready",
                            athlete_id=athlete.id,
                            athlete_display_name=athlete.display_name,
                            strategy_id=strategy.id,
                            message=(
                                "Review resource history, allocation policy, budget, dates, and "
                                "constraints before creating the next block."
                            ),
                            issues=issues,
                        )
                    )
                    continue

                for existing_block in sorted(
                    block.existing_blocks,
                    key=lambda item: (item.generated_at, str(item.id)),
                ):
                    first_week = self.first_week_projector.project(existing_block.id, instant)
                    if first_week.existing_first_week_plans:
                        continue
                    issues = self._first_week_issues(first_week)
                    items.append(
                        PlanningReviewQueueItemProjection(
                            workflow_stage="first_week",
                            status="ready_for_explicit_first_week",
                            readiness="blocked" if issues else "ready",
                            athlete_id=athlete.id,
                            athlete_display_name=athlete.display_name,
                            strategy_id=strategy.id,
                            block_id=existing_block.id,
                            message=(
                                "Review exact allocation lineage, prescriptions, session "
                                "structure, availability, and scheduling policy for Week 1."
                            ),
                            issues=issues,
                        )
                    )
                    break
        except (
            BlockPreparationNotFoundError,
            BlockPreparationProjectionError,
            DomainIntegrityError,
            FirstWeekPreparationNotFoundError,
            FirstWeekPreparationProjectionError,
            InitialPlanningPreparationNotFoundError,
            InitialPlanningPreparationProjectionError,
            ResourceDemandPreparationNotFoundError,
            ResourceDemandPreparationProjectionError,
            ValueError,
        ) as error:
            raise PlanningReviewQueueProjectionError(str(error)) from error
        return PlanningReviewQueueProjection(projected_at=instant, items=tuple(items))

    def _current_strategy(self, athlete_id: UUID) -> LongRangeStrategy | None:
        records = self.session.scalars(
            select(LongRangeStrategyRecord)
            .where(LongRangeStrategyRecord.athlete_id == athlete_id)
            .order_by(LongRangeStrategyRecord.generated_at, LongRangeStrategyRecord.id)
        ).all()
        if not records:
            return None
        superseded_ids = {
            record.supersedes_strategy_id
            for record in records
            if record.supersedes_strategy_id is not None
        }
        leaves = [record for record in records if record.id not in superseded_ids]
        if len(leaves) != 1:
            raise PlanningReviewQueueProjectionError(
                "athlete strategy lineage must have exactly one current leaf"
            )
        strategy = self.repository.get_long_range_strategy(leaves[0].id)
        if strategy is None:
            raise PlanningReviewQueueProjectionError(
                "current strategy disappeared during planning queue projection"
            )
        return strategy

    @staticmethod
    def _resource_issues(
        projection: ResourceDemandPreparationProjection,
    ) -> tuple[str, ...]:
        requires_active_resolution = any(
            option.priority.state is not TrainingPriorityState.DEFER and not option.demand_history
            for option in projection.priorities
        )
        if not requires_active_resolution:
            return ()
        issues = []
        if not projection.environments:
            issues.append("no athlete environment is available")
        if not projection.exercise_resolver_policies:
            issues.append("no exercise-resolver policy is available")
        if not projection.exercise_catalog:
            issues.append("no exercise catalog entries are available")
        return tuple(issues)

    @staticmethod
    def _first_week_issues(projection: FirstWeekPreparationProjection) -> tuple[str, ...]:
        issues = []
        if not projection.environments:
            issues.append("no athlete environment is available")
        if not any(option.is_currently_approved for option in projection.scheduling_policy_options):
            issues.append("no currently approved weekly-scheduling policy is available")
        return tuple(issues)
