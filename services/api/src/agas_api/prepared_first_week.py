# ruff: noqa: E501 -- candidate boundaries remain explicit and reviewable.
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID, uuid5

from agas_domain import (
    AssessmentReviewDecision,
    AthleteSafetyPolicyAssignment,
    BlockPlan,
    BlockPlanStatus,
    BodyweightTarget,
    CapabilityEstimate,
    Confidence,
    EffortRpeTarget,
    Observation,
    ObservationSource,
    Provenance,
    ResolutionStatus,
    SessionSection,
    TechniqueTarget,
    WeeklyPlanStatus,
    WeeklySchedulingPolicy,
    WeeklySchedulingPolicyReview,
)
from agas_domain.persistence.repository import DomainRepository
from agas_planner import DerivedRepetitionDose, RepetitionDoseError, RepetitionDosePlanner
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from agas_api.evidence_governance import (
    EvidenceAuthorityEvaluationError,
    EvidenceAuthorityEvaluator,
    EvidenceAuthorityNotReadyError,
)
from agas_api.first_week_preparation import (
    FirstWeekAllocationInput,
    FirstWeekPreparationNotFoundError,
    FirstWeekPreparationProjectionError,
    FirstWeekPreparationProjector,
)
from agas_api.identity import AuthorizedRole
from agas_api.training_construction_candidates import (
    CANDIDATE_ID as TRAINING_CONSTRUCTION_CANDIDATE_ID,
)
from agas_api.training_construction_candidates import prepared_training_construction_candidate
from agas_api.weekly_planning import (
    AvailabilityWindowDraft,
    CreateWeeklyPlanCommand,
    PersistedWeeklyPlanService,
    SessionPrescriptionDraft,
    SessionTemplateDraft,
    SessionTemplateItemDraft,
    WeeklyAvailabilityDraft,
    WeeklyPlanCreationIdentities,
    WeeklyPlanCreationResult,
    WeeklyPlanUseCaseError,
)

CANDIDATE_VERSION = "prepared-first-week@1.1.0"
CANDIDATE_NAMESPACE = UUID("37728da6-7ebf-499d-b821-7d72da044ac7")
MAXIMUM_CANDIDATE_AGE = timedelta(minutes=30)
NonEmptyText = Annotated[str, Field(min_length=1)]


class PrepareFirstWeekCommand(BaseModel):
    """Factual availability offered by the owner; no training values are accepted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    windows: Annotated[tuple[AvailabilityWindowDraft, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def reject_duplicate_windows(self) -> PrepareFirstWeekCommand:
        keys = tuple((item.environment_id, item.starts_at, item.ends_at) for item in self.windows)
        if len(set(keys)) != len(keys):
            raise ValueError("availability windows must not contain duplicates")
        return self


class PreparedFirstWeekIdentities(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    availability_observation_id: UUID
    safety_policy_assignment_id: UUID
    prescription_id: UUID
    session_template_id: UUID
    weekly_availability_id: UUID
    availability_window_ids: tuple[UUID, ...]
    weekly_plan_id: UUID
    planned_session_ids: tuple[UUID, ...]
    decision_record_id: UUID

    def service_identities(self) -> WeeklyPlanCreationIdentities:
        return WeeklyPlanCreationIdentities(
            prescription_ids=(self.prescription_id,),
            session_template_ids=(self.session_template_id,),
            weekly_availability_id=self.weekly_availability_id,
            availability_window_ids=self.availability_window_ids,
            weekly_plan_id=self.weekly_plan_id,
            planned_session_ids=self.planned_session_ids,
            decision_record_id=self.decision_record_id,
        )


class PreparedFirstWeekCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["prepared-first-week@1.1.0"]
    candidate_id: UUID
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    prepared_at: datetime
    status: Literal["available", "accepted"]
    athlete_id: UUID
    block_id: UUID
    week_start: str
    exercise_name: NonEmptyText
    environment_name: NonEmptyText
    sessions: tuple[dict[str, str], ...]
    sets: int
    repetitions_per_set: int
    rest_seconds: int
    effort_rpe_range: NonEmptyText
    planned_duration_minutes: int
    technique_constraints: tuple[NonEmptyText, ...]
    dose_calculation: NonEmptyText
    provenance_summary: NonEmptyText
    uncertainty: NonEmptyText
    safety_boundary: NonEmptyText
    safety_policy_assignment: AthleteSafetyPolicyAssignment
    safety_assignment_status: Literal["will_assign", "already_assigned"]
    identities: PreparedFirstWeekIdentities
    accepted_result: WeeklyPlanCreationResult | None = None


class PreparedFirstWeekProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    block_id: UUID
    athlete_id: UUID | None = None
    projected_at: datetime
    status: Literal["available", "blocked", "accepted"]
    message: NonEmptyText
    candidate: PreparedFirstWeekCandidate | None = None
    blockers: tuple[str, ...] = ()
    projection_version: str = "prepared-first-week-projection@1.1.0"


class RatifyPreparedFirstWeekCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["prepared-first-week@1.1.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    prepared_at: datetime
    windows: Annotated[tuple[AvailabilityWindowDraft, ...], Field(min_length=1)]
    approval_attestation: Literal[True]

    @model_validator(mode="after")
    def validate_command(self) -> RatifyPreparedFirstWeekCommand:
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("prepared_at must include a timezone")
        PrepareFirstWeekCommand(windows=self.windows)
        return self


class PreparedFirstWeekRatificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: UUID
    candidate_content_digest: str
    created: bool
    availability_observation: Observation
    safety_policy_assignment: AthleteSafetyPolicyAssignment
    result: WeeklyPlanCreationResult
    ratification_version: str = "prepared-first-week-ratification@1.1.0"


class PreparedFirstWeekConflictError(RuntimeError):
    pass


class PreparedFirstWeekValidationError(RuntimeError):
    pass


class PreparedFirstWeekProjector:
    """Build one exact chair-stand Week 1 from governed dose and factual availability."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def project(
        self,
        block_id: UUID,
        command: PrepareFirstWeekCommand,
        authority: AuthorizedRole,
        projected_at: datetime | None = None,
    ) -> PreparedFirstWeekProjection:
        instant = projected_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("prepared first-week time must include a timezone")
        preparation = FirstWeekPreparationProjector(self.session).project(block_id, instant)
        block = preparation.block
        blockers: list[str] = []
        if block.status is not BlockPlanStatus.FULL:
            blockers.append("The first prepared week requires a FULL block.")

        active = tuple(
            item
            for item in preparation.allocation_inputs
            if item.allocation.allocated_weekly_minutes > 0
        )
        if len(active) != 1:
            blockers.append(
                "The current owner-alpha prepared week requires exactly one active allocation."
            )
        exact_policy, exact_review = self._construction_authority(instant, blockers)
        if blockers or len(active) != 1 or exact_policy is None or exact_review is None:
            return self._blocked(block.id, block.athlete_id, instant, blockers)

        allocation_input = active[0]
        allocation = allocation_input.allocation
        resolution = allocation_input.exercise_resolution
        exercise = allocation_input.selected_exercise
        requirement = allocation_input.stimulus_requirement
        if resolution is None or exercise is None or requirement is None:
            return self._blocked(
                block.id,
                block.athlete_id,
                instant,
                ["The active allocation has incomplete exercise lineage."],
            )
        if resolution.status is not ResolutionStatus.FULL:
            blockers.append("The prepared first week requires a FULL exercise resolution.")
        if len(command.windows) < allocation.sessions_per_week:
            blockers.append(
                f"Offer at least {allocation.sessions_per_week} non-overlapping training times "
                "so every required session can be scheduled."
            )
        if any(window.environment_id != resolution.environment_id for window in command.windows):
            blockers.append(
                "Every offered time must use the exercise's fully resolved environment."
            )
        if any(window.starts_at < instant for window in command.windows):
            blockers.append("Offered training times cannot be in the past.")

        environment = self.repository.get_environment(resolution.environment_id)
        if environment is None or environment.athlete_id != block.athlete_id:
            blockers.append("The resolved training environment is unavailable for this athlete.")

        strategy = self.repository.get_long_range_strategy(block.long_range_strategy_id)
        if strategy is None:
            raise FirstWeekPreparationProjectionError("the block strategy does not exist")
        priority = next(
            (item for item in strategy.priorities if item.id == allocation.adaptation_priority_id),
            None,
        )
        need = (
            self.repository.get_capability_need(priority.capability_need_id)
            if priority is not None
            else None
        )
        estimate = (
            self.repository.get_capability_estimate(need.capability_estimate_id)
            if need is not None and need.capability_estimate_id is not None
            else None
        )
        adaptation = self.repository.get_adaptation(allocation.adaptation_id)
        dose_policy = prepared_training_construction_candidate().release.repetition_dose_policy
        if adaptation is None or estimate is None:
            blockers.append("The allocation no longer has its exact capability estimate lineage.")
            dose = None
        else:
            try:
                dose = RepetitionDosePlanner().derive(
                    adaptation=adaptation,
                    estimate=estimate,
                    policy=dose_policy,
                    derived_at=instant,
                )
            except RepetitionDoseError as error:
                blockers.append(f"The governed starting dose cannot be derived: {error}")
                dose = None
        if blockers or environment is None or estimate is None or dose is None:
            return self._blocked(block.id, block.athlete_id, instant, blockers)

        release = prepared_training_construction_candidate().release
        expected_assignment_id = uuid5(
            CANDIDATE_NAMESPACE,
            f"safety-assignment:{block.athlete_id}:{release.session_safety_policy.id}:"
            f"{authority.assignment_id}",
        )
        current_assignment = self.repository.get_current_athlete_safety_policy_assignment(
            block.athlete_id
        )
        if (
            current_assignment is not None
            and current_assignment.safety_policy_id != release.session_safety_policy.id
        ):
            return self._blocked(
                block.id,
                block.athlete_id,
                instant,
                [
                    "A different athlete safety-policy assignment already exists; review it before preparing Week 1."
                ],
            )
        safety_assignment = current_assignment or AthleteSafetyPolicyAssignment(
            id=expected_assignment_id,
            created_at=instant,
            athlete_id=block.athlete_id,
            safety_policy_id=release.session_safety_policy.id,
            sequence_number=1,
            assigned_at=instant,
            assigned_by=f"account:{authority.account_id}",
            applicability_rationale=(
                "Assign the exact ratified owner-alpha non-diagnostic readiness policy to this "
                "athlete before the first scheduled session."
            ),
            rule_version="prepared-first-week-safety-assignment@1.0.0",
        )

        stable_content = {
            "candidate_version": CANDIDATE_VERSION,
            "block": block.model_dump(mode="json"),
            "allocation_input": allocation_input.model_dump(mode="json"),
            "capability_estimate": estimate.model_dump(mode="json"),
            "dose_policy": dose_policy.model_dump(mode="json"),
            "derived_dose": dose.model_dump(mode="json", exclude={"derived_at"}),
            "weekly_scheduling_policy": exact_policy.model_dump(mode="json"),
            "weekly_scheduling_policy_review": exact_review.model_dump(mode="json"),
            "safety_policy_assignment": safety_assignment.model_dump(mode="json"),
            "windows": [item.model_dump(mode="json") for item in command.windows],
            "prepared_at": instant.isoformat(),
            "review_authority_assignment_id": str(authority.assignment_id),
            "training_construction_candidate_id": str(TRAINING_CONSTRUCTION_CANDIDATE_ID),
            "training_construction_digest": prepared_training_construction_candidate().presentation.content_digest,
        }
        canonical = json.dumps(stable_content, sort_keys=True, separators=(",", ":"))
        content_digest = f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
        candidate_id = uuid5(CANDIDATE_NAMESPACE, content_digest)
        identities = PreparedFirstWeekIdentities(
            availability_observation_id=uuid5(candidate_id, "availability-observation"),
            safety_policy_assignment_id=safety_assignment.id,
            prescription_id=uuid5(candidate_id, "session-prescription"),
            session_template_id=uuid5(candidate_id, "session-template"),
            weekly_availability_id=uuid5(candidate_id, "weekly-availability"),
            availability_window_ids=tuple(
                uuid5(candidate_id, f"availability-window:{index}")
                for index in range(len(command.windows))
            ),
            weekly_plan_id=uuid5(candidate_id, "weekly-plan"),
            planned_session_ids=tuple(
                uuid5(candidate_id, f"planned-session:{index}")
                for index in range(allocation.sessions_per_week)
            ),
            decision_record_id=uuid5(candidate_id, "decision-record"),
        )
        availability_observation = self._availability_observation(
            block.athlete_id, block.starts_on.isoformat(), command, instant, authority, identities
        )
        weekly_command = self._weekly_command(
            block=block,
            allocation_input=allocation_input,
            estimate=estimate,
            dose=dose,
            scheduling_policy_id=exact_policy.id,
            scheduling_policy_review_id=exact_review.id,
            windows=command.windows,
            availability_observation_id=availability_observation.id,
            prepared_at=instant,
            authority=authority,
            content_digest=content_digest,
        )
        try:
            preview = PersistedWeeklyPlanService(self.session).preview(
                block.id, weekly_command, identities=identities.service_identities()
            )
        except WeeklyPlanUseCaseError as error:
            return self._blocked(block.id, block.athlete_id, instant, [str(error)])
        if preview.weekly_plan.status is not WeeklyPlanStatus.FEASIBLE:
            issues = tuple(item.detail for item in preview.weekly_plan.issues)
            return self._blocked(
                block.id,
                block.athlete_id,
                instant,
                list(issues or ("The offered times cannot schedule every required session.",)),
            )

        existing_observation = self.repository.get_observation(
            identities.availability_observation_id
        )
        existing_result = self._existing_result(identities, preview)
        existing_plans = tuple(
            item
            for item in preparation.existing_first_week_plans
            if item.id != identities.weekly_plan_id
        )
        if existing_plans:
            return self._blocked(
                block.id,
                block.athlete_id,
                instant,
                ["A different Week 1 plan already exists; immutable history requires review."],
            )
        if (existing_observation is None) != (existing_result is None):
            raise PreparedFirstWeekConflictError(
                "prepared first-week identity is partially occupied"
            )
        if existing_observation is not None and existing_observation != availability_observation:
            raise PreparedFirstWeekConflictError(
                "prepared availability identity contains different content"
            )

        candidate = PreparedFirstWeekCandidate(
            candidate_version=CANDIDATE_VERSION,
            candidate_id=candidate_id,
            content_digest=content_digest,
            prepared_at=instant,
            status="accepted" if existing_result is not None else "available",
            athlete_id=block.athlete_id,
            block_id=block.id,
            week_start=block.starts_on.isoformat(),
            exercise_name=exercise.name,
            environment_name=environment.name,
            sessions=tuple(
                {
                    "starts_at": item.starts_at.isoformat(),
                    "ends_at": item.ends_at.isoformat(),
                }
                for item in preview.weekly_plan.sessions
            ),
            sets=dose.sets,
            repetitions_per_set=dose.repetitions_per_set,
            rest_seconds=dose.rest_seconds,
            effort_rpe_range=f"{dose.effort_rpe_minimum:g}-{dose.effort_rpe_maximum:g}",
            planned_duration_minutes=dose.planned_duration_minutes,
            technique_constraints=dose.technique_constraints,
            dose_calculation=(
                f"Derived from capability estimate {estimate.id} using {dose.calculation_method} "
                f"under dose policy {dose.repetition_dose_policy_id}."
            ),
            provenance_summary=(
                "The prescription comes from the block's exact adaptation and exercise resolution; "
                "the scheduled times come only from the availability just reported."
            ),
            uncertainty=dose_policy.uncertainty,
            safety_boundary=(
                "This plan schedules sessions but does not clear you to perform them. The phone "
                "must still record a current pre-session safety check before each session."
            ),
            safety_policy_assignment=safety_assignment,
            safety_assignment_status=(
                "already_assigned" if current_assignment is not None else "will_assign"
            ),
            identities=identities,
            accepted_result=existing_result,
        )
        return PreparedFirstWeekProjection(
            block_id=block.id,
            athlete_id=block.athlete_id,
            projected_at=instant,
            status="accepted" if existing_result is not None else "available",
            message=(
                "The exact first week is already stored with immutable provenance."
                if existing_result is not None
                else "Review the derived dose and scheduled times before recording Week 1."
            ),
            candidate=candidate,
        )

    def _construction_authority(
        self, instant: datetime, blockers: list[str]
    ) -> tuple[WeeklySchedulingPolicy | None, WeeklySchedulingPolicyReview | None]:
        prepared = prepared_training_construction_candidate()
        release = prepared.release
        decision = self.repository.get_decision_record(TRAINING_CONSTRUCTION_CANDIDATE_ID)
        policy = self.repository.get_weekly_scheduling_policy(release.weekly_scheduling_policy.id)
        review = self.repository.get_weekly_scheduling_policy_review(
            release.weekly_scheduling_policy_review_id
        )
        exact = (
            decision is not None
            and f"candidate_content_digest:{prepared.presentation.content_digest}"
            in decision.evidence
            and policy == release.weekly_scheduling_policy
            and review is not None
            and review.decision is AssessmentReviewDecision.APPROVED
            and self.repository.get_repetition_dose_policy(release.repetition_dose_policy.id)
            == release.repetition_dose_policy
            and self.repository.get_progression_policy(release.progression_policy.id)
            == release.progression_policy
            and self.repository.get_session_safety_policy(release.session_safety_policy.id)
            == release.session_safety_policy
        )
        if not exact:
            blockers.append("The exact owner-alpha training-construction authority is unavailable.")
            return None, None
        try:
            EvidenceAuthorityEvaluator(self.session).require_ready(
                release.repetition_dose_policy.evidence_claim_ids, instant
            )
        except (EvidenceAuthorityEvaluationError, EvidenceAuthorityNotReadyError) as error:
            blockers.append(f"The dose evidence authority is not current: {error}")
            return None, None
        return policy, review

    @staticmethod
    def _availability_observation(
        athlete_id: UUID,
        week_start: str,
        command: PrepareFirstWeekCommand,
        instant: datetime,
        authority: AuthorizedRole,
        identities: PreparedFirstWeekIdentities,
    ) -> Observation:
        return Observation(
            id=identities.availability_observation_id,
            created_at=instant,
            athlete_id=athlete_id,
            observed_at=instant,
            observation_type="weekly_training_availability_report",
            measurement={
                "week_start": week_start,
                "windows": [item.model_dump(mode="json") for item in command.windows],
            },
            unit=None,
            source=ObservationSource.USER_REPORT,
            reliability=Confidence.UNKNOWN,
            context={"report_scope": "first_week", "candidate_version": CANDIDATE_VERSION},
            provenance=Provenance(
                recorded_by=f"account:{authority.account_id}",
                source_system="agas-owner-pwa",
                ingestion_method="prepared-first-week-availability-form",
            ),
        )

    @staticmethod
    def _weekly_command(
        *,
        block: BlockPlan,
        allocation_input: FirstWeekAllocationInput,
        estimate: CapabilityEstimate,
        dose: DerivedRepetitionDose,
        scheduling_policy_id: UUID,
        scheduling_policy_review_id: UUID,
        windows: tuple[AvailabilityWindowDraft, ...],
        availability_observation_id: UUID,
        prepared_at: datetime,
        authority: AuthorizedRole,
        content_digest: str,
    ) -> CreateWeeklyPlanCommand:
        requirement = allocation_input.stimulus_requirement
        exercise = allocation_input.selected_exercise
        if requirement is None or exercise is None:
            raise PreparedFirstWeekValidationError(
                "the prepared prescription requires complete exercise lineage"
            )
        evidence_ids = tuple(
            dict.fromkeys(
                (
                    *allocation_input.resource_demand.evidence_claim_ids,
                    *requirement.evidence_claim_ids,
                    *prepared_training_construction_candidate().release.repetition_dose_policy.evidence_claim_ids,
                )
            )
        )
        observation_ids = tuple(
            dict.fromkeys(
                (
                    *estimate.source_observation_ids,
                    *requirement.source_observation_ids,
                )
            )
        )
        prescription = SessionPrescriptionDraft(
            resource_allocation_id=allocation_input.allocation.id,
            reason_for_inclusion=(
                "Deliver the block's sole DEVELOP allocation through its exact FULL exercise "
                "resolution using the ratified assessment-calibrated starting-dose policy."
            ),
            sets=dose.sets,
            repetitions_per_set=dose.repetitions_per_set,
            intensity_targets=(
                BodyweightTarget(),
                EffortRpeTarget(minimum=dose.effort_rpe_minimum, maximum=dose.effort_rpe_maximum),
                TechniqueTarget(constraints=dose.technique_constraints),
            ),
            rest_seconds=dose.rest_seconds,
            progression_rule_reference=(
                prepared_training_construction_candidate().release.progression_policy.reference
            ),
            substitution_class="exact_full_resolution_only",
            planned_duration_minutes=dose.planned_duration_minutes,
            fatigue_cost=exercise.fatigue_cost,
            source_observation_ids=observation_ids,
            evidence_claim_ids=evidence_ids,
            rule_version=(f"prepared-first-week-prescription@1.0.0;dose={dose.rule_version}"),
        )
        template = SessionTemplateDraft(
            name="First chair sit-to-stand session",
            items=(
                SessionTemplateItemDraft(
                    resource_allocation_id=allocation_input.allocation.id,
                    order_index=1,
                    section=SessionSection.PRIMARY,
                ),
            ),
            sessions_per_week=allocation_input.allocation.sessions_per_week,
            planned_duration_minutes=dose.planned_duration_minutes,
            fatigue_cost=exercise.fatigue_cost,
            source_observation_ids=observation_ids,
            evidence_claim_ids=evidence_ids,
            rule_version="prepared-first-week-session-template@1.0.0",
        )
        return CreateWeeklyPlanCommand(
            prescriptions=(prescription,),
            session_templates=(template,),
            availability=WeeklyAvailabilityDraft(
                week_start=block.starts_on,
                windows=windows,
                source_observation_ids=(availability_observation_id,),
                rule_version="owner-reported-first-week-availability@1.0.0",
            ),
            scheduling_policy_id=scheduling_policy_id,
            scheduling_policy_review_id=scheduling_policy_review_id,
            prepared_at=prepared_at,
            reviewed_by=f"account:{authority.account_id}",
            review_authority_assignment_id=authority.assignment_id,
            applicability_rationale=(
                "Apply the exact owner-alpha dose and scheduling authorities to this athlete, "
                f"block, FULL exercise resolution, and reported availability. Candidate digest: {content_digest}."
            ),
            uncertainty=(
                "The starting dose uses provisional engineering constants and has not yet been "
                "calibrated against this athlete's training response."
            ),
        )

    def _existing_result(
        self,
        identities: PreparedFirstWeekIdentities,
        expected: WeeklyPlanCreationResult,
    ) -> WeeklyPlanCreationResult | None:
        prescription = self.repository.get_session_prescription(identities.prescription_id)
        prescriptions = () if prescription is None else (prescription,)
        template = self.repository.get_session_template(identities.session_template_id)
        templates = () if template is None else (template,)
        availability = self.repository.get_weekly_availability(identities.weekly_availability_id)
        plan = self.repository.get_weekly_plan(identities.weekly_plan_id)
        decision = self.repository.get_decision_record(identities.decision_record_id)
        found_count = (
            len(prescriptions)
            + len(templates)
            + sum(item is not None for item in (availability, plan, decision))
        )
        if found_count == 0:
            return None
        if (
            len(prescriptions) != 1
            or len(templates) != 1
            or availability is None
            or plan is None
            or decision is None
        ):
            raise PreparedFirstWeekConflictError(
                "prepared first-week identity is partially occupied"
            )
        existing = WeeklyPlanCreationResult(
            prescriptions=prescriptions,
            session_templates=templates,
            availability=availability,
            weekly_plan=plan,
            decision_record=decision,
        )
        if existing != expected:
            raise PreparedFirstWeekConflictError(
                "prepared first-week identity contains different or incomplete content"
            )
        return existing

    @staticmethod
    def _blocked(
        block_id: UUID,
        athlete_id: UUID,
        instant: datetime,
        blockers: list[str],
    ) -> PreparedFirstWeekProjection:
        return PreparedFirstWeekProjection(
            block_id=block_id,
            athlete_id=athlete_id,
            projected_at=instant,
            status="blocked",
            message="The exact first week is not ready from these availability times.",
            blockers=tuple(dict.fromkeys(blockers)),
        )


def ratify_prepared_first_week(
    session: Session,
    block_id: UUID,
    candidate_id: UUID,
    command: RatifyPreparedFirstWeekCommand,
    authority: AuthorizedRole,
) -> PreparedFirstWeekRatificationResult:
    factual_input = PrepareFirstWeekCommand(windows=command.windows)
    projection = PreparedFirstWeekProjector(session).project(
        block_id, factual_input, authority, command.prepared_at
    )
    candidate = projection.candidate
    if candidate is None or candidate.candidate_id != candidate_id:
        raise FirstWeekPreparationNotFoundError(
            "the prepared first week is unavailable or its governed inputs changed"
        )
    if command.candidate_version != candidate.candidate_version:
        raise PreparedFirstWeekConflictError(
            "candidate version does not match the current prepared first week"
        )
    if command.content_digest != candidate.content_digest:
        raise PreparedFirstWeekConflictError(
            "candidate content changed; refresh and inspect the exact current week"
        )
    if candidate.accepted_result is not None:
        observation = DomainRepository(session).get_observation(
            candidate.identities.availability_observation_id
        )
        if observation is None:
            raise PreparedFirstWeekConflictError(
                "accepted first week is missing its availability observation"
            )
        return PreparedFirstWeekRatificationResult(
            candidate_id=candidate.candidate_id,
            candidate_content_digest=candidate.content_digest,
            created=False,
            availability_observation=observation,
            safety_policy_assignment=candidate.safety_policy_assignment,
            result=candidate.accepted_result,
        )
    now = datetime.now(UTC)
    if command.prepared_at > now + timedelta(minutes=5):
        raise PreparedFirstWeekValidationError("candidate preparation time cannot be in the future")
    if now - command.prepared_at > MAXIMUM_CANDIDATE_AGE:
        raise PreparedFirstWeekValidationError(
            "the availability candidate is older than 30 minutes; prepare it again"
        )
    repository = DomainRepository(session)
    observation = PreparedFirstWeekProjector._availability_observation(
        candidate.athlete_id,
        candidate.week_start,
        factual_input,
        command.prepared_at,
        authority,
        candidate.identities,
    )
    try:
        repository.add_observation(observation)
        current_assignment = repository.get_current_athlete_safety_policy_assignment(
            candidate.athlete_id
        )
        if current_assignment is None:
            repository.add_athlete_safety_policy_assignment(candidate.safety_policy_assignment)
        elif current_assignment != candidate.safety_policy_assignment:
            raise PreparedFirstWeekConflictError(
                "athlete safety-policy assignment changed after candidate preparation"
            )
        preparation = FirstWeekPreparationProjector(session).project(block_id, command.prepared_at)
        active = next(
            item
            for item in preparation.allocation_inputs
            if item.allocation.allocated_weekly_minutes > 0
        )
        strategy = repository.get_long_range_strategy(preparation.block.long_range_strategy_id)
        if strategy is None:
            raise PreparedFirstWeekValidationError("the block strategy is unavailable")
        priority = next(
            item
            for item in strategy.priorities
            if item.id == active.allocation.adaptation_priority_id
        )
        need = repository.get_capability_need(priority.capability_need_id)
        if need is None or need.capability_estimate_id is None:
            raise PreparedFirstWeekValidationError("the capability estimate is unavailable")
        estimate = repository.get_capability_estimate(need.capability_estimate_id)
        adaptation = repository.get_adaptation(active.allocation.adaptation_id)
        if estimate is None or adaptation is None:
            raise PreparedFirstWeekValidationError("the dose inputs are unavailable")
        release = prepared_training_construction_candidate().release
        dose = RepetitionDosePlanner().derive(
            adaptation=adaptation,
            estimate=estimate,
            policy=release.repetition_dose_policy,
            derived_at=command.prepared_at,
        )
        result = PersistedWeeklyPlanService(session).execute(
            block_id,
            PreparedFirstWeekProjector._weekly_command(
                block=preparation.block,
                allocation_input=active,
                estimate=estimate,
                dose=dose,
                scheduling_policy_id=release.weekly_scheduling_policy.id,
                scheduling_policy_review_id=release.weekly_scheduling_policy_review_id,
                windows=command.windows,
                availability_observation_id=observation.id,
                prepared_at=command.prepared_at,
                authority=authority,
                content_digest=candidate.content_digest,
            ),
            identities=candidate.identities.service_identities(),
        )
    except Exception:
        session.rollback()
        raise
    return PreparedFirstWeekRatificationResult(
        candidate_id=candidate.candidate_id,
        candidate_content_digest=candidate.content_digest,
        created=True,
        availability_observation=observation,
        safety_policy_assignment=candidate.safety_policy_assignment,
        result=result,
    )
