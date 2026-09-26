# ruff: noqa: E501 -- decision-boundary prose remains exact and reviewable.
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid5

from agas_domain import (
    EnvironmentSnapshot,
    Loadability,
    LongRangeStrategy,
    ResolutionStatus,
    StimulusSpecification,
    TrainingPriorityState,
)
from agas_domain.persistence.repository import DomainRepository
from agas_planner import ExerciseResolver, StimulusRequirementBuilder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from agas_api.evidence_governance import (
    EvidenceAuthorityEvaluationError,
    EvidenceAuthorityEvaluator,
    EvidenceAuthorityNotReadyError,
)
from agas_api.identity import AuthorizedRole
from agas_api.prepared_strategy_cycle import (
    PreparedStrategyCycleError,
    PreparedStrategyCycleLineage,
    prior_state_for_adaptation,
    resolve_strategy_cycle_lineage,
)
from agas_api.resource_demand_preparation import (
    ResourceDemandEnvironmentOption,
    ResourceDemandPreparationNotFoundError,
    ResourceDemandPreparationProjector,
    ResourceDemandPriorityOption,
)
from agas_api.resource_governance_candidates import (
    AEROBIC_CANDIDATE_ID as AEROBIC_RESOURCE_AUTHORITY_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    CANDIDATE_ID as CHAIR_RESOURCE_AUTHORITY_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    JUMP_CANDIDATE_ID as JUMP_RESOURCE_AUTHORITY_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    JUMP_MAINTENANCE_CANDIDATE_ID as JUMP_MAINTENANCE_RESOURCE_AUTHORITY_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    PUSHUP_CANDIDATE_ID as PUSHUP_RESOURCE_AUTHORITY_CANDIDATE_ID,
)
from agas_api.resource_governance_candidates import (
    PreparedResourceGovernanceCandidate,
    prepared_resource_governance_candidate_for_scope,
)
from agas_api.resource_preparation import (
    ActiveResourceDemandCommand,
    PersistedResourcePreparationService,
    ResourceDemandPreparationResult,
    ResourcePreparationIdentities,
)

CANDIDATE_VERSION: Literal["prepared-resource-demand@1.0.0"] = "prepared-resource-demand@1.0.0"
SUCCESSOR_CANDIDATE_VERSION: Literal["prepared-resource-demand@1.1.0"] = (
    "prepared-resource-demand@1.1.0"
)
CANDIDATE_NAMESPACE = UUID("78ca646d-31c2-4b7b-a074-11edcdd26443")
MINIMUM_WEEKLY_MINUTES = 10
TARGET_WEEKLY_MINUTES = 10
SESSIONS_PER_WEEK = 2
CHAIR_DEMAND_VERSION = "owner-alpha-chair-stand-resource-envelope@1.0.0"
PUSHUP_DEMAND_VERSION = "owner-alpha-standard-pushup-resource-envelope@1.0.0"
JUMP_DEMAND_VERSION = "owner-alpha-explosive-power-jump-resource-envelope@1.0.0"
JUMP_MAINTENANCE_DEMAND_VERSION = (
    "owner-alpha-explosive-power-jump-maintenance-resource-envelope@1.0.0"
)
AEROBIC_DEMAND_VERSION = "owner-alpha-aerobic-base-resource-envelope@1.0.0"
NonEmptyText = Annotated[str, Field(min_length=1)]


class PreparedResourceDemandIdentities(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stimulus_requirement_id: UUID
    exercise_resolution_id: UUID
    resource_demand_id: UUID
    decision_record_id: UUID

    def service_identities(self) -> ResourcePreparationIdentities:
        return ResourcePreparationIdentities(**self.model_dump())


class PreparedResourceDemandCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["prepared-resource-demand@1.0.0", "prepared-resource-demand@1.1.0"]
    candidate_id: UUID
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    prepared_at: datetime
    status: Literal["available", "accepted"]
    athlete_id: UUID
    strategy_id: UUID
    priority_id: UUID
    priority_state: TrainingPriorityState
    previous_priority_state: TrainingPriorityState | None = None
    adaptation_id: UUID
    adaptation_name: NonEmptyText
    environment_id: UUID
    environment_name: NonEmptyText
    environment_snapshot: EnvironmentSnapshot
    resource_authority_candidate_id: UUID
    resource_authority_content_digest: str
    stimulus_specification: StimulusSpecification
    exercise_candidate_id: UUID
    exercise_name: NonEmptyText
    exercise_resolver_policy_id: UUID
    expected_resolution_status: ResolutionStatus
    expected_selected_exercise_id: UUID
    minimum_weekly_minutes: int
    target_weekly_minutes: int
    sessions_per_week: int
    per_session_scheduling_minutes: int
    scheduling_basis: NonEmptyText
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText
    safety_boundary: NonEmptyText
    dose_boundary: NonEmptyText
    strategy_cycle: PreparedStrategyCycleLineage
    identities: PreparedResourceDemandIdentities
    accepted_result: ResourceDemandPreparationResult | None = None


class PreparedResourceDemandProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: UUID
    athlete_id: UUID | None = None
    projected_at: datetime
    status: Literal["available", "blocked", "accepted"]
    message: NonEmptyText
    candidates: tuple[PreparedResourceDemandCandidate, ...]
    blockers: tuple[str, ...]
    projection_version: str = "prepared-resource-demand-projection@1.1.0"


class RatifyPreparedResourceDemandCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["prepared-resource-demand@1.0.0", "prepared-resource-demand@1.1.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    approval_attestation: Literal[True]


class PreparedResourceDemandRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    candidate_content_digest: str
    created: bool
    result: ResourceDemandPreparationResult
    ratification_version: str = "prepared-resource-demand-ratification@1.0.0"


class PreparedResourceDemandConflictError(RuntimeError):
    pass


class PreparedResourceDemandValidationError(RuntimeError):
    pass


class PreparedResourceDemandProjector:
    """Prepare the one governed owner-alpha resource envelope against factual state."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def project(
        self,
        strategy_id: UUID,
        authority: AuthorizedRole,
        projected_at: datetime | None = None,
    ) -> PreparedResourceDemandProjection:
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("prepared resource-demand time must include a timezone")
        preparation = ResourceDemandPreparationProjector(self.session).project(strategy_id, instant)
        strategy = preparation.strategy
        try:
            strategy_cycle = resolve_strategy_cycle_lineage(self.repository, strategy)
        except PreparedStrategyCycleError as error:
            return PreparedResourceDemandProjection(
                strategy_id=strategy.id,
                athlete_id=strategy.athlete_id,
                projected_at=instant,
                status="blocked",
                message="The exact strategy resource demand is not ready yet.",
                candidates=(),
                blockers=(str(error),),
            )
        priority = self._eligible_priority(preparation.priorities)
        if priority is None:
            blockers: list[str] = []
            blockers.append(
                "The strategy must contain exactly one governed DEVELOP or MAINTAIN priority with an active resource policy."
            )
            prepared_authority = None
        else:
            prepared_authority = self._resource_authority(priority)
            blockers = self._authority_blockers(instant, prepared_authority)

        environment_blockers: list[str] = []
        eligible_environments: list[ResourceDemandEnvironmentOption] = []
        for option in preparation.environments:
            issues = (
                ()
                if prepared_authority is None
                else self._environment_issues(option, prepared_authority)
            )
            if issues:
                environment_blockers.extend(
                    f"{option.environment.name}: {issue}" for issue in issues
                )
            else:
                eligible_environments.append(option)
        if not eligible_environments:
            blockers.extend(environment_blockers or ["No training environment exists."])

        if blockers or priority is None or prepared_authority is None:
            return PreparedResourceDemandProjection(
                strategy_id=strategy.id,
                athlete_id=strategy.athlete_id,
                projected_at=instant,
                status="blocked",
                message="The exact strategy resource demand is not ready yet.",
                candidates=(),
                blockers=tuple(dict.fromkeys(blockers)),
            )

        candidates = tuple(
            candidate
            for environment in eligible_environments
            if (
                candidate := self._candidate(
                    strategy,
                    priority,
                    environment,
                    prepared_authority,
                    strategy_cycle,
                    authority,
                    instant,
                )
            )
            is not None
        )
        if not candidates:
            return PreparedResourceDemandProjection(
                strategy_id=strategy.id,
                athlete_id=strategy.athlete_id,
                projected_at=instant,
                status="blocked",
                message="Existing resource-demand history does not match this prepared candidate.",
                candidates=(),
                blockers=(
                    "Inspect the immutable demand history in the advanced section before preparing another demand.",
                ),
            )
        accepted = tuple(item for item in candidates if item.status == "accepted")
        return PreparedResourceDemandProjection(
            strategy_id=strategy.id,
            athlete_id=strategy.athlete_id,
            projected_at=instant,
            status="accepted" if accepted else "available",
            message=(
                "The exact resource demand is already stored with immutable provenance."
                if accepted
                else "Choose the factual training environment and accept one exact prepared resource demand."
            ),
            candidates=candidates,
            blockers=(),
        )

    def _authority_blockers(
        self,
        instant: datetime,
        prepared: PreparedResourceGovernanceCandidate,
    ) -> list[str]:
        release = prepared.release
        decision = self.repository.get_decision_record(prepared.presentation.candidate_id)
        equipment_exact = (
            release.equipment is None
            or self.repository.get_equipment(release.equipment.id) == release.equipment
        )
        exact = (
            decision is not None
            and f"candidate_content_digest:{prepared.presentation.content_digest}"
            in decision.evidence
            and self.repository.get_evidence_claim(release.claim.id) == release.claim
            and equipment_exact
            and self.repository.get_exercise(release.exercise.id) == release.exercise
            and self.repository.get_exercise_resolver_policy(release.resolver_policy.id)
            == release.resolver_policy
            and self.repository.get_resource_allocation_policy(release.allocation_policy.id)
            == release.allocation_policy
        )
        if not exact:
            return [
                "Ratify the exact first owner-alpha resource-authority bundle before preparing this demand."
            ]
        try:
            EvidenceAuthorityEvaluator(self.session).require_ready((release.claim.id,), instant)
        except (EvidenceAuthorityEvaluationError, EvidenceAuthorityNotReadyError) as error:
            return [f"The resource evidence authority is not current: {error}"]
        return []

    def _eligible_priority(
        self,
        options: tuple[ResourceDemandPriorityOption, ...],
    ) -> ResourceDemandPriorityOption | None:
        eligible = []
        for option in options:
            try:
                prepared = self._resource_authority(option)
            except (KeyError, PreparedResourceDemandValidationError):
                continue
            allocation = prepared.release.allocation_policy
            active_weight = {
                TrainingPriorityState.DEVELOP: allocation.develop_weight,
                TrainingPriorityState.MAINTAIN: allocation.maintain_weight,
                TrainingPriorityState.EXPOSE: allocation.expose_weight,
            }.get(option.priority.state, 0)
            if (
                active_weight > 0
                and option.priority.adaptation_id
                in prepared.release.exercise.primary_adaptation_ids
            ):
                eligible.append(option)
        return eligible[0] if len(eligible) == 1 else None

    @staticmethod
    def _environment_issues(
        option: ResourceDemandEnvironmentOption,
        prepared: PreparedResourceGovernanceCandidate,
    ) -> tuple[str, ...]:
        snapshot = option.snapshot
        issues = []
        available_equipment_ids = {item.equipment_id for item in snapshot.available_equipment}
        missing_equipment = tuple(
            equipment_id
            for equipment_id in prepared.release.exercise.equipment_requirement_ids
            if equipment_id not in available_equipment_ids
        )
        if missing_equipment:
            equipment_name = (
                prepared.release.equipment.name
                if prepared.release.equipment is not None
                else "required equipment"
            )
            issues.append(f"report {equipment_name.casefold()} as currently available")
        required_area = prepared.release.exercise.minimum_floor_area_m2
        if required_area is not None and (
            snapshot.floor_area_m2 is None or snapshot.floor_area_m2 < required_area
        ):
            issues.append(f"record at least {required_area:g} m² of usable floor space")
        return tuple(issues)

    def _resource_authority(
        self,
        option: ResourceDemandPriorityOption,
    ) -> PreparedResourceGovernanceCandidate:
        need = self.repository.get_capability_need(option.priority.capability_need_id)
        if need is None or need.capability_estimate_id is None:
            raise PreparedResourceDemandValidationError(
                "the priority has no governed capability estimate"
            )
        estimate = self.repository.get_capability_estimate(need.capability_estimate_id)
        if estimate is None:
            raise PreparedResourceDemandValidationError(
                "the priority capability estimate is unavailable"
            )
        return prepared_resource_governance_candidate_for_scope(
            estimate.estimate_scope, option.priority.state
        )

    def _candidate(
        self,
        strategy: LongRangeStrategy,
        option: ResourceDemandPriorityOption,
        environment: ResourceDemandEnvironmentOption,
        release: PreparedResourceGovernanceCandidate,
        strategy_cycle: PreparedStrategyCycleLineage,
        authority: AuthorizedRole,
        instant: datetime,
    ) -> PreparedResourceDemandCandidate | None:
        priority = option.priority
        exercise = release.release.exercise
        claim = release.release.claim
        resolver = release.release.resolver_policy
        minimum_weekly_minutes, target_weekly_minutes, sessions_per_week = (
            _weekly_resource_envelope(release.presentation.candidate_id)
        )
        candidate_version = _candidate_version(strategy_cycle, release.presentation.candidate_id)
        specification = StimulusSpecification(
            movement_patterns=exercise.movement_patterns,
            allowed_loading_types=(exercise.loading_type,),
            allowed_lateralities=(exercise.laterality,),
            minimum_loadability=Loadability.LIMITED,
            required_velocity_characteristics=exercise.velocity_characteristics,
            maximum_skill_complexity=exercise.skill_complexity,
            maximum_impact_level=exercise.impact_level,
            maximum_stability_demand=exercise.stability_demand,
            maximum_fatigue_cost=exercise.fatigue_cost,
            maximum_soreness_cost=exercise.soreness_cost,
            minimum_floor_area_m2=exercise.minimum_floor_area_m2,
            source_observation_ids=tuple(
                dict.fromkeys(
                    (*strategy.source_observation_ids, *environment.constraint_observation_ids)
                )
            ),
            evidence_claim_ids=tuple(dict.fromkeys((*strategy.evidence_claim_ids, claim.id))),
            rationale=(
                f"Require the exact governed {exercise.name} stimulus for adaptation "
                f"{option.adaptation.name} and resolve it only when every ontology, equipment, "
                "and current floor-space constraint is satisfied."
            ),
        )
        preview_requirement = StimulusRequirementBuilder().build(
            strategy=strategy,
            priority=priority,
            adaptation=option.adaptation,
            specification=specification,
            generated_at=instant,
        )
        preview_resolution = ExerciseResolver().resolve(
            requirement=preview_requirement,
            environment=environment.snapshot,
            exercises=(exercise,),
            policy=resolver,
            resolved_at=instant,
        )
        if (
            preview_resolution.status is not ResolutionStatus.FULL
            or preview_resolution.selected_exercise_id != exercise.id
        ):
            raise PreparedResourceDemandValidationError(
                "the exact governed exercise did not fully resolve against the selected environment"
            )
        scheduling_basis = (
            f"Reserve {target_weekly_minutes} minutes per week across {sessions_per_week} "
            f"{target_weekly_minutes // sessions_per_week}-minute scheduling slots as a deliberately small "
            "owner-alpha scheduling envelope. This is an explicit engineering starting allowance, "
            "not a literature-derived physiological dose."
        )
        if candidate_version == CANDIDATE_VERSION:
            applicability_rationale = (
                "Apply the ratified muscular-endurance resource authority to the sole active priority "
                f"in the factual {environment.environment.name} snapshot. The ACSM claim supports "
                "resistance-training direction and at-least-twice-weekly frequency; the "
                f"{target_weekly_minutes}-minute "
                "weekly reservation is a provisional scheduling choice only."
            )
        else:
            cycle_basis = (
                "reviewed successor strategy"
                if strategy_cycle.cycle == "successor"
                else "reviewed initial strategy"
            )
            applicability_rationale = (
                f"Apply the exact ratified {option.adaptation.name} resource authority to the "
                f"{priority.state.value.upper()} priority in this {cycle_basis} and the factual "
                f"{environment.environment.name} snapshot. Evidence claim {claim.id} supports "
                "the bounded training direction recorded by that authority; the "
                f"{target_weekly_minutes}-minute weekly reservation remains a provisional, "
                "separately reviewed scheduling choice."
            )
        uncertainty = (
            f"{exercise.name} is assessment-proximal and improvement may include test familiarity. "
            "No exact repetitions, sets, effort, tempo, rest, progression, current-session safety, "
            "or individualized response is established here."
        )
        safety_boundary = (
            "Current equipment availability and adequate floor space establish environmental feasibility "
            "only. They do not certify technique, pain tolerance, medical clearance, "
            "or readiness on the day of training; every session still requires its safety gate."
        )
        dose_boundary = (
            "Two weekly slots and five reserved minutes per slot are scheduling resources, not an "
            "exercise prescription. A separate reviewed dose authority must still set repetitions, "
            "sets, effort, tempo, rest, and stop rules before any workout can be performed."
            if candidate_version == CANDIDATE_VERSION
            else (
                f"{sessions_per_week} weekly slots and "
                f"{target_weekly_minutes // sessions_per_week} reserved minutes per slot are "
                "scheduling resources, not an exercise prescription. A separate reviewed dose "
                "authority must still set repetitions, sets, effort, tempo, rest, and stop rules "
                "before any workout can be performed."
            )
        )
        stable_content = {
            "candidate_version": candidate_version,
            "athlete_id": str(strategy.athlete_id),
            "strategy_id": str(strategy.id),
            "strategy_rule_version": strategy.rule_version,
            "priority": priority.model_dump(mode="json"),
            "environment_id": str(environment.environment.id),
            "environment_constraint_observation_ids": [
                str(item) for item in environment.constraint_observation_ids
            ],
            "environment_snapshot": {
                "environment_id": str(environment.snapshot.environment_id),
                "available_equipment": [
                    item.model_dump(mode="json")
                    for item in environment.snapshot.available_equipment
                ],
                "source_availability_ids": [
                    str(item) for item in environment.snapshot.source_availability_ids
                ],
                "floor_area_m2": environment.snapshot.floor_area_m2,
                "max_noise_level": environment.snapshot.max_noise_level.value,
                "outdoor_access": environment.snapshot.outdoor_access,
            },
            "authority_assignment_id": str(authority.assignment_id),
            "resource_authority_candidate_id": str(release.presentation.candidate_id),
            "resource_authority_content_digest": release.presentation.content_digest,
            "stimulus_specification": specification.model_dump(mode="json"),
            "exercise_candidate_id": str(exercise.id),
            "exercise_resolver_policy_id": str(resolver.id),
            "expected_resolution_status": preview_resolution.status.value,
            "expected_selected_exercise_id": str(exercise.id),
            "minimum_weekly_minutes": minimum_weekly_minutes,
            "target_weekly_minutes": target_weekly_minutes,
            "sessions_per_week": sessions_per_week,
            "scheduling_basis": scheduling_basis,
            "applicability_rationale": applicability_rationale,
            "uncertainty": uncertainty,
            "safety_boundary": safety_boundary,
            "dose_boundary": dose_boundary,
            "demand_version": _demand_version(release.presentation.candidate_id),
        }
        if candidate_version == SUCCESSOR_CANDIDATE_VERSION:
            stable_content["strategy_cycle"] = strategy_cycle.model_dump(mode="json")
        canonical = json.dumps(stable_content, sort_keys=True, separators=(",", ":"))
        content_digest = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        candidate_id = uuid5(CANDIDATE_NAMESPACE, content_digest)
        identities = PreparedResourceDemandIdentities(
            stimulus_requirement_id=uuid5(candidate_id, "stimulus-requirement"),
            exercise_resolution_id=uuid5(candidate_id, "exercise-resolution"),
            resource_demand_id=uuid5(candidate_id, "resource-demand"),
            decision_record_id=uuid5(candidate_id, "decision-record"),
        )
        existing = self._existing_result(
            identities,
            content_digest,
            strategy=strategy,
            option=option,
            environment=environment,
            specification=specification,
            exercise_id=exercise.id,
            resolver_policy_id=resolver.id,
            demand_version=_demand_version(release.presentation.candidate_id),
            minimum_weekly_minutes=minimum_weekly_minutes,
            target_weekly_minutes=target_weekly_minutes,
            sessions_per_week=sessions_per_week,
        )
        history_ids = {item.resource_demand.id for item in option.demand_history}
        if history_ids and history_ids != {identities.resource_demand_id}:
            return None
        return PreparedResourceDemandCandidate(
            candidate_version=candidate_version,
            candidate_id=candidate_id,
            content_digest=content_digest,
            prepared_at=instant,
            status="accepted" if existing is not None else "available",
            athlete_id=strategy.athlete_id,
            strategy_id=strategy.id,
            priority_id=priority.id,
            priority_state=priority.state,
            previous_priority_state=prior_state_for_adaptation(
                strategy_cycle, option.adaptation.id
            ),
            adaptation_id=option.adaptation.id,
            adaptation_name=option.adaptation.name,
            environment_id=environment.environment.id,
            environment_name=environment.environment.name,
            environment_snapshot=environment.snapshot,
            resource_authority_candidate_id=release.presentation.candidate_id,
            resource_authority_content_digest=release.presentation.content_digest,
            stimulus_specification=specification,
            exercise_candidate_id=exercise.id,
            exercise_name=exercise.name,
            exercise_resolver_policy_id=resolver.id,
            expected_resolution_status=preview_resolution.status,
            expected_selected_exercise_id=exercise.id,
            minimum_weekly_minutes=minimum_weekly_minutes,
            target_weekly_minutes=target_weekly_minutes,
            sessions_per_week=sessions_per_week,
            per_session_scheduling_minutes=minimum_weekly_minutes // sessions_per_week,
            scheduling_basis=scheduling_basis,
            applicability_rationale=applicability_rationale,
            uncertainty=uncertainty,
            safety_boundary=safety_boundary,
            dose_boundary=dose_boundary,
            strategy_cycle=strategy_cycle,
            identities=identities,
            accepted_result=existing,
        )

    def _existing_result(
        self,
        identities: PreparedResourceDemandIdentities,
        content_digest: str,
        *,
        strategy: LongRangeStrategy,
        option: ResourceDemandPriorityOption,
        environment: ResourceDemandEnvironmentOption,
        specification: StimulusSpecification,
        exercise_id: UUID,
        resolver_policy_id: UUID,
        demand_version: str,
        minimum_weekly_minutes: int,
        target_weekly_minutes: int,
        sessions_per_week: int,
    ) -> ResourceDemandPreparationResult | None:
        demand = self.repository.get_adaptation_resource_demand(identities.resource_demand_id)
        if demand is None:
            occupied = tuple(
                item
                for item in (
                    self.repository.get_stimulus_requirement(identities.stimulus_requirement_id),
                    self.repository.get_exercise_resolution(identities.exercise_resolution_id),
                    self.repository.get_decision_record(identities.decision_record_id),
                )
                if item is not None
            )
            if occupied:
                raise PreparedResourceDemandConflictError(
                    "prepared resource-demand identity is partially occupied"
                )
            return None
        requirement = self.repository.get_stimulus_requirement(identities.stimulus_requirement_id)
        resolution = self.repository.get_exercise_resolution(identities.exercise_resolution_id)
        decision = self.repository.get_decision_record(identities.decision_record_id)
        if (
            requirement is None
            or resolution is None
            or decision is None
            or requirement.athlete_id != strategy.athlete_id
            or requirement.long_range_strategy_id != strategy.id
            or requirement.adaptation_priority_id != option.priority.id
            or requirement.adaptation_id != option.adaptation.id
            or requirement.priority_state is not option.priority.state
            or requirement.movement_patterns != specification.movement_patterns
            or requirement.allowed_loading_types != specification.allowed_loading_types
            or requirement.allowed_lateralities != specification.allowed_lateralities
            or requirement.minimum_loadability is not specification.minimum_loadability
            or requirement.required_velocity_characteristics
            != specification.required_velocity_characteristics
            or requirement.maximum_skill_complexity is not specification.maximum_skill_complexity
            or requirement.maximum_impact_level is not specification.maximum_impact_level
            or requirement.maximum_stability_demand is not specification.maximum_stability_demand
            or requirement.maximum_fatigue_cost is not specification.maximum_fatigue_cost
            or requirement.maximum_soreness_cost is not specification.maximum_soreness_cost
            or requirement.requires_outdoor_access != specification.requires_outdoor_access
            or requirement.minimum_floor_area_m2 != specification.minimum_floor_area_m2
            or requirement.contraindication_tags != specification.contraindication_tags
            or requirement.source_observation_ids != specification.source_observation_ids
            or requirement.evidence_claim_ids != specification.evidence_claim_ids
            or requirement.rationale != specification.rationale
            or resolution.environment_id != environment.environment.id
            or resolution.resolver_policy_id != resolver_policy_id
            or resolution.status is not ResolutionStatus.FULL
            or resolution.selected_exercise_id != exercise_id
            or resolution.source_availability_ids != environment.snapshot.source_availability_ids
            or resolution.unresolved_issues
            or demand.stimulus_requirement_id != requirement.id
            or demand.exercise_resolution_id != resolution.id
            or demand.long_range_strategy_id != strategy.id
            or demand.adaptation_priority_id != option.priority.id
            or demand.adaptation_id != option.adaptation.id
            or demand.priority_state is not option.priority.state
            or demand.minimum_weekly_minutes != minimum_weekly_minutes
            or demand.target_weekly_minutes != target_weekly_minutes
            or demand.sessions_per_week != sessions_per_week
            or demand.source_observation_ids != specification.source_observation_ids
            or demand.evidence_claim_ids != specification.evidence_claim_ids
            or demand.demand_version != demand_version
            or content_digest not in decision.reason
            or f"adaptation_resource_demand:{demand.id}" not in decision.evidence
        ):
            raise PreparedResourceDemandConflictError(
                "prepared resource-demand identity is occupied by different or incomplete content"
            )
        return ResourceDemandPreparationResult(
            stimulus_requirement=requirement,
            exercise_resolution=resolution,
            resource_demand=demand,
            decision_record=decision,
        )


def ratify_prepared_resource_demand(
    session: Session,
    strategy_id: UUID,
    candidate_id: UUID,
    command: RatifyPreparedResourceDemandCommand,
    authority: AuthorizedRole,
) -> PreparedResourceDemandRatificationResult:
    projection = PreparedResourceDemandProjector(session).project(strategy_id, authority)
    candidate = next(
        (item for item in projection.candidates if item.candidate_id == candidate_id), None
    )
    if candidate is None:
        raise ResourceDemandPreparationNotFoundError(
            "the prepared resource demand is unavailable or its factual inputs changed"
        )
    if command.candidate_version != candidate.candidate_version:
        raise PreparedResourceDemandConflictError(
            "candidate version does not match the current prepared resource demand"
        )
    if command.content_digest != candidate.content_digest:
        raise PreparedResourceDemandConflictError(
            "candidate content changed; refresh and inspect the exact current resource demand"
        )
    if candidate.accepted_result is not None:
        return PreparedResourceDemandRatificationResult(
            candidate_id=candidate.candidate_id,
            candidate_content_digest=candidate.content_digest,
            created=False,
            result=candidate.accepted_result,
        )
    prepared_at = datetime.now(UTC)
    result = PersistedResourcePreparationService(session).execute(
        strategy_id,
        candidate.priority_id,
        ActiveResourceDemandCommand(
            mode="active",
            prepared_at=prepared_at,
            reviewed_by=f"account:{authority.account_id}",
            review_authority_assignment_id=authority.assignment_id,
            environment_id=candidate.environment_id,
            exercise_candidate_ids=(candidate.exercise_candidate_id,),
            exercise_resolver_policy_id=candidate.exercise_resolver_policy_id,
            stimulus_specification=candidate.stimulus_specification,
            minimum_weekly_minutes=candidate.minimum_weekly_minutes,
            target_weekly_minutes=candidate.target_weekly_minutes,
            sessions_per_week=candidate.sessions_per_week,
            demand_rationale=(f"{candidate.scheduling_basis} {candidate.dose_boundary}"),
            demand_version=_demand_version(candidate.resource_authority_candidate_id),
            applicability_rationale=(
                f"{candidate.applicability_rationale} Prepared candidate digest: "
                f"{candidate.content_digest}."
            ),
            uncertainty=candidate.uncertainty,
        ),
        identities=candidate.identities.service_identities(),
    )
    return PreparedResourceDemandRatificationResult(
        candidate_id=candidate.candidate_id,
        candidate_content_digest=candidate.content_digest,
        created=True,
        result=result,
    )


def _demand_version(resource_candidate_id: UUID) -> str:
    if resource_candidate_id == CHAIR_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return CHAIR_DEMAND_VERSION
    if resource_candidate_id == PUSHUP_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return PUSHUP_DEMAND_VERSION
    if resource_candidate_id == JUMP_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return JUMP_DEMAND_VERSION
    if resource_candidate_id == JUMP_MAINTENANCE_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return JUMP_MAINTENANCE_DEMAND_VERSION
    if resource_candidate_id == AEROBIC_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return AEROBIC_DEMAND_VERSION
    raise PreparedResourceDemandValidationError("resource authority has no demand version")


def _weekly_resource_envelope(resource_candidate_id: UUID) -> tuple[int, int, int]:
    if resource_candidate_id == CHAIR_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return MINIMUM_WEEKLY_MINUTES, TARGET_WEEKLY_MINUTES, SESSIONS_PER_WEEK
    if resource_candidate_id == PUSHUP_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return 12, 12, 2
    if resource_candidate_id == JUMP_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return 24, 24, 2
    if resource_candidate_id == JUMP_MAINTENANCE_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return 12, 12, 2
    if resource_candidate_id == AEROBIC_RESOURCE_AUTHORITY_CANDIDATE_ID:
        return 24, 24, 2
    raise PreparedResourceDemandValidationError("resource authority has no weekly envelope")


def _candidate_version(
    strategy_cycle: PreparedStrategyCycleLineage,
    resource_candidate_id: UUID,
) -> Literal["prepared-resource-demand@1.0.0", "prepared-resource-demand@1.1.0"]:
    if strategy_cycle.cycle == "initial" and resource_candidate_id not in {
        AEROBIC_RESOURCE_AUTHORITY_CANDIDATE_ID,
        JUMP_RESOURCE_AUTHORITY_CANDIDATE_ID,
        JUMP_MAINTENANCE_RESOURCE_AUTHORITY_CANDIDATE_ID,
    }:
        return CANDIDATE_VERSION
    return SUCCESSOR_CANDIDATE_VERSION
