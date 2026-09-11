# ruff: noqa: E501 -- governance boundaries remain explicit and reviewable.
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid5

from agas_domain import (
    AssessmentReviewDecision,
    BlockPlanStatus,
    ResolutionStatus,
    TrainingPriorityState,
)
from agas_domain.persistence.repository import DomainRepository
from agas_planner import BlockPlanner, BlockPlanningError
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from agas_api.block_creation import (
    BlockCreationIdentities,
    BlockPlanCreationResult,
    CreateBlockPlanCommand,
    PersistedBlockCreationService,
)
from agas_api.block_preparation import (
    BlockPreparationNotFoundError,
    BlockPreparationProjector,
)
from agas_api.evidence_governance import (
    EvidenceAuthorityEvaluationError,
    EvidenceAuthorityEvaluator,
    EvidenceAuthorityNotReadyError,
)
from agas_api.identity import AuthorizedRole
from agas_api.resource_governance_candidates import (
    CANDIDATE_ID as RESOURCE_AUTHORITY_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import prepared_resource_governance_candidate
from agas_api.training_construction_candidates import (
    CANDIDATE_ID as TRAINING_CONSTRUCTION_CANDIDATE_ID,
)
from agas_api.training_construction_candidates import prepared_training_construction_candidate

CANDIDATE_VERSION = "prepared-first-block@1.0.0"
CANDIDATE_NAMESPACE = UUID("eb9952ad-f7d8-47af-b203-b6a5fa64aa1c")
DURATION_WEEKS = 4
NonEmptyText = Annotated[str, Field(min_length=1)]


class PreparedFirstBlockIdentities(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block_plan_id: UUID
    resource_allocation_ids: tuple[UUID, ...]
    decision_record_id: UUID

    def service_identities(self) -> BlockCreationIdentities:
        return BlockCreationIdentities(**self.model_dump())


class PreparedFirstBlockAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    adaptation_id: UUID
    priority_state: TrainingPriorityState
    allocated_weekly_minutes: int
    sessions_per_week: int
    status: BlockPlanStatus


class PreparedFirstBlockCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["prepared-first-block@1.0.0"]
    candidate_id: UUID
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    prepared_at: datetime
    status: Literal["available", "accepted"]
    athlete_id: UUID
    strategy_id: UUID
    starts_on: date
    ends_on: date
    duration_weeks: int
    weekly_budget_minutes: int
    resource_demand_ids: tuple[UUID, ...]
    resource_allocation_policy_id: UUID
    expected_status: BlockPlanStatus
    expected_allocations: tuple[PreparedFirstBlockAllocation, ...]
    construction_basis: NonEmptyText
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText
    safety_boundary: NonEmptyText
    identities: PreparedFirstBlockIdentities
    accepted_result: BlockPlanCreationResult | None = None


class PreparedFirstBlockProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: UUID
    athlete_id: UUID | None = None
    starts_on: date
    projected_at: datetime
    status: Literal["available", "blocked", "accepted"]
    message: NonEmptyText
    candidate: PreparedFirstBlockCandidate | None = None
    blockers: tuple[str, ...] = ()
    projection_version: str = "prepared-first-block-projection@1.0.0"


class RatifyPreparedFirstBlockCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["prepared-first-block@1.0.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    starts_on: date
    approval_attestation: Literal[True]


class PreparedFirstBlockRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    candidate_content_digest: str
    created: bool
    result: BlockPlanCreationResult
    ratification_version: str = "prepared-first-block-ratification@1.0.0"


class PreparedFirstBlockConflictError(RuntimeError):
    pass


class PreparedFirstBlockValidationError(RuntimeError):
    pass


class PreparedFirstBlockProjector:
    """Derive the first block from exact ratified owner-alpha state."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def project(
        self,
        strategy_id: UUID,
        starts_on: date,
        authority: AuthorizedRole,
        projected_at: datetime | None = None,
    ) -> PreparedFirstBlockProjection:
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("prepared first-block time must include a timezone")
        preparation = BlockPreparationProjector(self.session).project(strategy_id, instant)
        strategy = preparation.strategy
        blockers = self._authority_blockers(instant)
        if starts_on.weekday() != 0:
            blockers.append("Choose a Monday so every training week has an unambiguous boundary.")

        selected_demands = []
        selected_resolutions = []
        for option in preparation.priorities:
            if len(option.demand_history) != 1:
                blockers.append(
                    f"{option.adaptation.name} must have exactly one governed resource-demand record."
                )
                continue
            history = option.demand_history[0]
            if history.exercise_resolution is None:
                blockers.append(f"{option.adaptation.name} has no exercise resolution.")
                continue
            if history.exercise_resolution.status is not ResolutionStatus.FULL:
                blockers.append(
                    f"{option.adaptation.name} requires a full exercise resolution before block preparation."
                )
                continue
            selected_demands.append(history.resource_demand)
            selected_resolutions.append(history.exercise_resolution)

        resource_release = prepared_resource_governance_candidate().release
        matching_policies = tuple(
            policy
            for policy in preparation.resource_allocation_policies
            if policy == resource_release.allocation_policy
        )
        if len(matching_policies) != 1:
            blockers.append("The exact ratified owner-alpha allocation policy is unavailable.")

        if (
            blockers
            or len(selected_demands) != len(preparation.priorities)
            or not matching_policies
        ):
            return self._blocked(strategy.id, strategy.athlete_id, starts_on, instant, blockers)

        policy = matching_policies[0]
        weekly_budget = sum(item.target_weekly_minutes for item in selected_demands)
        construction_basis = (
            "Use the target minutes already ratified for every strategy priority, allocate them "
            "with the exact owner-alpha policy, and hold that envelope for four weeks. Four weeks "
            "is a provisional engineering horizon for the first usable alpha, not a scientific "
            "claim that four weeks is universally optimal."
        )
        applicability = (
            "This block is derived only for this athlete, this strategy, and the immutable resource "
            "demands whose exercise resolutions were full against the recorded environment."
        )
        uncertainty = (
            "The block reserves time and frequency but does not establish session dates, repetitions, "
            "sets, effort, rest, readiness, technique, or response. Those remain governed downstream."
        )
        safety_boundary = (
            "Accepting this block does not authorize exercise. A dated week, current availability, "
            "governed prescription, and pre-session safety gate are still required before training."
        )
        constraints = (
            "Use only fully resolved exercises from the selected immutable resource demands.",
            "Do not exceed the ratified target weekly minutes during this first block.",
            "Require current readiness and session-safety evaluation before each training session.",
        )
        stable_content = {
            "candidate_version": CANDIDATE_VERSION,
            "strategy": strategy.model_dump(mode="json"),
            "starts_on": starts_on.isoformat(),
            "duration_weeks": DURATION_WEEKS,
            "weekly_budget_minutes": weekly_budget,
            "resource_demands": [item.model_dump(mode="json") for item in selected_demands],
            "exercise_resolutions": [item.model_dump(mode="json") for item in selected_resolutions],
            "resource_allocation_policy": policy.model_dump(mode="json"),
            "review_authority_assignment_id": str(authority.assignment_id),
            "resource_authority_candidate_id": str(RESOURCE_AUTHORITY_CANDIDATE_ID),
            "resource_authority_digest": prepared_resource_governance_candidate().presentation.content_digest,
            "training_construction_candidate_id": str(TRAINING_CONSTRUCTION_CANDIDATE_ID),
            "training_construction_digest": prepared_training_construction_candidate().presentation.content_digest,
            "constraints": constraints,
            "construction_basis": construction_basis,
            "applicability_rationale": applicability,
            "uncertainty": uncertainty,
            "safety_boundary": safety_boundary,
        }
        canonical = json.dumps(stable_content, sort_keys=True, separators=(",", ":"))
        content_digest = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        candidate_id = uuid5(CANDIDATE_NAMESPACE, content_digest)
        identities = PreparedFirstBlockIdentities(
            block_plan_id=uuid5(candidate_id, "block-plan"),
            resource_allocation_ids=tuple(
                uuid5(candidate_id, f"resource-allocation:{index}")
                for index in range(len(selected_demands))
            ),
            decision_record_id=uuid5(candidate_id, "decision-record"),
        )
        existing = self._existing_result(
            identities,
            content_digest,
            strategy_id=strategy.id,
            starts_on=starts_on,
            weekly_budget=weekly_budget,
            demand_ids=tuple(item.id for item in selected_demands),
            policy_id=policy.id,
        )
        unrelated = tuple(
            block for block in preparation.existing_blocks if block.id != identities.block_plan_id
        )
        if unrelated:
            return self._blocked(
                strategy.id,
                strategy.athlete_id,
                starts_on,
                instant,
                [
                    "A different block already exists for this strategy; inspect immutable history before preparing another."
                ],
            )
        if existing is None and starts_on < instant.date():
            return self._blocked(
                strategy.id,
                strategy.athlete_id,
                starts_on,
                instant,
                ["The first block cannot begin in the past."],
            )

        try:
            preview = BlockPlanner().build(
                strategy=strategy,
                demands=selected_demands,
                resolutions=selected_resolutions,
                policy=policy,
                weekly_budget_minutes=weekly_budget,
                starts_on=starts_on,
                duration_weeks=DURATION_WEEKS,
                constraints=constraints,
                generated_at=instant if existing is None else existing.block_plan.generated_at,
            )
        except BlockPlanningError as error:
            return self._blocked(strategy.id, strategy.athlete_id, starts_on, instant, [str(error)])
        if preview.status is not BlockPlanStatus.FULL:
            return self._blocked(
                strategy.id,
                strategy.athlete_id,
                starts_on,
                instant,
                ["The exact resource envelope did not produce a full block."],
            )

        candidate = PreparedFirstBlockCandidate(
            candidate_version=CANDIDATE_VERSION,
            candidate_id=candidate_id,
            content_digest=content_digest,
            prepared_at=instant,
            status="accepted" if existing is not None else "available",
            athlete_id=strategy.athlete_id,
            strategy_id=strategy.id,
            starts_on=preview.starts_on,
            ends_on=preview.ends_on,
            duration_weeks=preview.duration_weeks,
            weekly_budget_minutes=preview.weekly_budget_minutes,
            resource_demand_ids=tuple(item.id for item in selected_demands),
            resource_allocation_policy_id=policy.id,
            expected_status=preview.status,
            expected_allocations=tuple(
                PreparedFirstBlockAllocation(
                    adaptation_id=item.adaptation_id,
                    priority_state=item.priority_state,
                    allocated_weekly_minutes=item.allocated_weekly_minutes,
                    sessions_per_week=item.sessions_per_week,
                    status=item.status,
                )
                for item in preview.allocations
            ),
            construction_basis=construction_basis,
            applicability_rationale=applicability,
            uncertainty=uncertainty,
            safety_boundary=safety_boundary,
            identities=identities,
            accepted_result=existing,
        )
        return PreparedFirstBlockProjection(
            strategy_id=strategy.id,
            athlete_id=strategy.athlete_id,
            starts_on=starts_on,
            projected_at=instant,
            status="accepted" if existing is not None else "available",
            message=(
                "The exact first block is already stored with immutable provenance."
                if existing is not None
                else "Review and accept the prepared four-week resource envelope."
            ),
            candidate=candidate,
        )

    def _authority_blockers(self, instant: datetime) -> list[str]:
        repository = self.repository
        resource = prepared_resource_governance_candidate()
        resource_decision = repository.get_decision_record(RESOURCE_AUTHORITY_CANDIDATE_ID)
        resource_exact = (
            resource_decision is not None
            and f"candidate_content_digest:{resource.presentation.content_digest}"
            in resource_decision.evidence
            and repository.get_resource_allocation_policy(resource.release.allocation_policy.id)
            == resource.release.allocation_policy
        )
        training = prepared_training_construction_candidate()
        training_decision = repository.get_decision_record(TRAINING_CONSTRUCTION_CANDIDATE_ID)
        release = training.release
        scheduling_review = repository.get_weekly_scheduling_policy_review(
            release.weekly_scheduling_policy_review_id
        )
        training_exact = (
            training_decision is not None
            and f"candidate_content_digest:{training.presentation.content_digest}"
            in training_decision.evidence
            and repository.get_weekly_scheduling_policy(release.weekly_scheduling_policy.id)
            == release.weekly_scheduling_policy
            and scheduling_review is not None
            and scheduling_review.weekly_scheduling_policy_id == release.weekly_scheduling_policy.id
            and scheduling_review.decision is AssessmentReviewDecision.APPROVED
            and scheduling_review.sequence_number == 1
            and scheduling_review.supersedes_review_id is None
            and scheduling_review.evidence_claim_ids
            == release.progression_policy.evidence_claim_ids
            and all(
                getattr(scheduling_review, field_name) == expected
                for field_name, expected in release.weekly_scheduling_policy_review_content.items()
            )
            and repository.get_progression_policy(release.progression_policy.id)
            == release.progression_policy
            and repository.get_repetition_dose_policy(release.repetition_dose_policy.id)
            == release.repetition_dose_policy
            and repository.get_session_safety_policy(release.session_safety_policy.id)
            == release.session_safety_policy
        )
        blockers = []
        if not resource_exact:
            blockers.append("Ratify the exact owner-alpha resource authority bundle first.")
        if not training_exact:
            blockers.append("Ratify the exact owner-alpha training-construction bundle first.")
        if not blockers:
            claim_ids = tuple(
                dict.fromkeys(
                    (
                        resource.release.claim.id,
                        *release.progression_policy.evidence_claim_ids,
                        *release.repetition_dose_policy.evidence_claim_ids,
                        *release.session_safety_policy.evidence_claim_ids,
                    )
                )
            )
            try:
                EvidenceAuthorityEvaluator(self.session).require_ready(claim_ids, instant)
            except (EvidenceAuthorityEvaluationError, EvidenceAuthorityNotReadyError) as error:
                blockers.append(f"The governing evidence authority is not current: {error}")
        return blockers

    def _existing_result(
        self,
        identities: PreparedFirstBlockIdentities,
        content_digest: str,
        *,
        strategy_id: UUID,
        starts_on: date,
        weekly_budget: int,
        demand_ids: tuple[UUID, ...],
        policy_id: UUID,
    ) -> BlockPlanCreationResult | None:
        block = self.repository.get_block_plan(identities.block_plan_id)
        decision = self.repository.get_decision_record(identities.decision_record_id)
        if block is None and decision is None:
            return None
        if block is None or decision is None:
            raise PreparedFirstBlockConflictError(
                "prepared first-block identity is partially occupied"
            )
        if (
            block.long_range_strategy_id != strategy_id
            or block.starts_on != starts_on
            or block.duration_weeks != DURATION_WEEKS
            or block.weekly_budget_minutes != weekly_budget
            or block.resource_allocation_policy_id != policy_id
            or block.status is not BlockPlanStatus.FULL
            or tuple(item.resource_demand_id for item in block.allocations) != demand_ids
            or tuple(item.id for item in block.allocations) != identities.resource_allocation_ids
            or content_digest not in decision.reason
            or f"block_plan:{block.id}" not in decision.evidence
        ):
            raise PreparedFirstBlockConflictError(
                "prepared first-block identity is occupied by different or incomplete content"
            )
        return BlockPlanCreationResult(block_plan=block, decision_record=decision)

    @staticmethod
    def _blocked(
        strategy_id: UUID,
        athlete_id: UUID,
        starts_on: date,
        instant: datetime,
        blockers: list[str],
    ) -> PreparedFirstBlockProjection:
        return PreparedFirstBlockProjection(
            strategy_id=strategy_id,
            athlete_id=athlete_id,
            starts_on=starts_on,
            projected_at=instant,
            status="blocked",
            message="The exact first block is not ready yet.",
            blockers=tuple(dict.fromkeys(blockers)),
        )


def ratify_prepared_first_block(
    session: Session,
    strategy_id: UUID,
    candidate_id: UUID,
    command: RatifyPreparedFirstBlockCommand,
    authority: AuthorizedRole,
) -> PreparedFirstBlockRatificationResult:
    projection = PreparedFirstBlockProjector(session).project(
        strategy_id, command.starts_on, authority
    )
    candidate = projection.candidate
    if candidate is None or candidate.candidate_id != candidate_id:
        raise BlockPreparationNotFoundError(
            "the prepared first block is unavailable or its governed inputs changed"
        )
    if command.candidate_version != candidate.candidate_version:
        raise PreparedFirstBlockConflictError(
            "candidate version does not match the current prepared first block"
        )
    if command.content_digest != candidate.content_digest:
        raise PreparedFirstBlockConflictError(
            "candidate content changed; refresh and inspect the exact current block"
        )
    if candidate.accepted_result is not None:
        return PreparedFirstBlockRatificationResult(
            candidate_id=candidate.candidate_id,
            candidate_content_digest=candidate.content_digest,
            created=False,
            result=candidate.accepted_result,
        )
    generated_at = datetime.now(UTC)
    constraints = (
        "Use only fully resolved exercises from the selected immutable resource demands.",
        "Do not exceed the ratified target weekly minutes during this first block.",
        "Require current readiness and session-safety evaluation before each training session.",
    )
    result = PersistedBlockCreationService(session).execute(
        strategy_id,
        CreateBlockPlanCommand(
            resource_demand_ids=candidate.resource_demand_ids,
            resource_allocation_policy_id=candidate.resource_allocation_policy_id,
            weekly_budget_minutes=candidate.weekly_budget_minutes,
            starts_on=candidate.starts_on,
            duration_weeks=candidate.duration_weeks,
            constraints=constraints,
            generated_at=generated_at,
            reviewed_by=f"account:{authority.account_id}",
            review_authority_assignment_id=authority.assignment_id,
            applicability_rationale=(
                f"{candidate.applicability_rationale} Prepared candidate digest: "
                f"{candidate.content_digest}. {candidate.construction_basis}"
            ),
            uncertainty=f"{candidate.uncertainty} {candidate.safety_boundary}",
        ),
        identities=candidate.identities.service_identities(),
    )
    return PreparedFirstBlockRatificationResult(
        candidate_id=candidate.candidate_id,
        candidate_content_digest=candidate.content_digest,
        created=True,
        result=result,
    )
