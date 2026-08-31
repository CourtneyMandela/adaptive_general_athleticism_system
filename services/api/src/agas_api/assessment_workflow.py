from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from agas_domain import (
    AssessmentDecision,
    AssessmentEligibilityOutcome,
    AssessmentIntensity,
    AssessmentMeasurementSchema,
    AssessmentReviewDecision,
    CapabilityDomain,
    Confidence,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy.orm import Session

from agas_api.assessment_catalog import list_evidence_ready_assessment_definitions
from agas_api.assessment_schedule import resolve_assessment_reassessment_schedule

AssessmentWorkflowStatus = Literal[
    "eligibility_required",
    "eligibility_review_required",
    "selection_blocked",
    "eligibility_inactive",
    "protocol_catalog_empty",
    "environment_required",
    "ready_to_start",
    "selection_deferred",
    "result_entry_ready",
    "run_blocked",
    "complete",
    "reassessment_due",
    "reassessment_not_due",
]
AssessmentResultStatus = Literal[
    "completed",
    "ready",
    "not_selected",
    "protocol_unavailable",
    "eligibility_unavailable",
]
AssessmentCapabilityEstimateStatus = Literal[
    "completed",
    "ready",
    "policy_unavailable",
    "policy_superseded",
    "stale",
]


class AssessmentWorkflowNotFoundError(LookupError):
    pass


class AssessmentEnvironmentProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_id: UUID
    name: str


class AssessmentEligibilityProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    eligibility_review_id: UUID
    outcome: AssessmentEligibilityOutcome
    reviewed_at: datetime
    valid_until: datetime
    rule_version: str


class AssessmentResultProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    performance_id: UUID
    result_observation_id: UUID
    performed_at: datetime
    measurement: JsonValue
    unit: str | None
    reliability: Confidence
    provenance: dict[str, JsonValue]
    rule_version: str
    next_reassessment_at: datetime
    reassessment_interval_source_review_id: UUID
    capability_estimate_status: AssessmentCapabilityEstimateStatus
    capability_estimate: AssessmentCapabilityEstimateProjection | None


class AssessmentCapabilityEstimateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    estimate_id: UUID
    estimate: JsonValue
    unit_or_scale: str
    estimate_scope: str
    confidence: Confidence
    calculation_method: str
    source_observation_ids: tuple[UUID, ...]
    estimated_at: datetime
    valid_until: datetime | None
    rule_version: str
    policy_id: UUID
    policy_reviewed_at: datetime
    policy_reviewed_by: str
    applicability_notes: str
    uncertainty: str
    evidence_claim_ids: tuple[UUID, ...]


class AssessmentDecisionProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    selection_id: UUID
    decision: AssessmentDecision
    reason_codes: tuple[str, ...]
    rationale: tuple[str, ...]
    assessment_definition_id: UUID
    assessment_definition_review_id: UUID | None
    name: str
    domain: CapabilityDomain
    intensity: AssessmentIntensity
    unit_or_scale: str
    protocol_version: str
    protocol_instructions: tuple[str, ...]
    result_entry_instructions: str
    measurement_schema: AssessmentMeasurementSchema | None
    applicability_notes: str
    uncertainty: str
    evidence_claim_ids: tuple[UUID, ...]
    review_version: str
    result_status: AssessmentResultStatus
    result: AssessmentResultProjection | None


class AssessmentRunProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: UUID
    environment_id: UUID
    environment_name: str
    evaluated_at: datetime
    rule_version: str
    decisions: tuple[AssessmentDecisionProjection, ...]


class AssessmentWorkflowProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete_id: UUID
    athlete_display_name: str
    as_of: datetime
    status: AssessmentWorkflowStatus
    message: str
    can_start_run: bool
    can_record_results: bool
    approved_self_administered_protocol_count: int
    due_protocol_count: int
    next_reassessment_at: datetime | None
    reassessment_rule_version: str
    eligibility: AssessmentEligibilityProjection | None
    environments: tuple[AssessmentEnvironmentProjection, ...]
    latest_run: AssessmentRunProjection | None


def get_assessment_workflow_projection(
    session: Session, athlete_id: UUID, as_of: datetime | None = None
) -> AssessmentWorkflowProjection:
    repository = DomainRepository(session)
    athlete = repository.get_athlete(athlete_id)
    if athlete is None:
        raise AssessmentWorkflowNotFoundError("athlete does not exist")
    instant = as_of or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("assessment workflow time must include a timezone")

    environments = repository.list_environments(athlete_id)
    environment_by_id = {item.id: item for item in environments}
    eligibility = repository.get_current_assessment_eligibility_review(athlete_id)
    reviewed_definitions = tuple(
        (definition, review)
        for definition, review in list_evidence_ready_assessment_definitions(repository)
        if review.self_administered and review.measurement_schema is not None
    )
    reassessment_schedule = resolve_assessment_reassessment_schedule(
        repository,
        athlete_id,
        reviewed_definitions,
        instant,
    )
    due_definition_ids = set(reassessment_schedule.due_definition_ids)
    eligibility_active = bool(
        eligibility
        and eligibility.outcome is AssessmentEligibilityOutcome.SELECTION_ALLOWED
        and eligibility.reviewed_at <= instant < eligibility.valid_until
    )
    selection_prerequisites_ready = bool(environments and due_definition_ids and eligibility_active)

    runs = repository.list_assessment_selection_runs(athlete_id)
    latest_run = runs[0] if runs else None
    run_projection: AssessmentRunProjection | None = None
    decision_projections: tuple[AssessmentDecisionProjection, ...] = ()
    if latest_run is not None:
        projected: list[AssessmentDecisionProjection] = []
        for selection_id in latest_run.selection_ids:
            selection = repository.get_assessment_selection(selection_id)
            if selection is None:
                raise ValueError("assessment run references a missing selection")
            definition = repository.get_assessment_definition(selection.assessment_definition_id)
            review = (
                repository.get_assessment_definition_review(
                    selection.assessment_definition_review_id
                )
                if selection.assessment_definition_review_id
                else None
            )
            if definition is None or review is None:
                raise ValueError("assessment selection references missing protocol authority")
            current_review = repository.get_current_assessment_definition_review(definition.id)
            performance = repository.get_assessment_performance_for_selection(selection.id)
            result = None
            if performance is not None:
                if review.recommended_reassessment_days is None:
                    raise ValueError("assessment performance review has no reassessment interval")
                observation = repository.get_observation(performance.result_observation_id)
                if observation is not None:
                    estimation_policy = repository.get_current_capability_estimation_policy(
                        definition.id
                    )
                    stored_estimate = repository.get_latest_assessment_capability_estimate(
                        performance.id
                    )
                    estimate_projection = None
                    estimate_policy = (
                        repository.get_capability_estimation_policy(
                            stored_estimate.capability_estimation_policy_id
                        )
                        if stored_estimate
                        and stored_estimate.capability_estimation_policy_id is not None
                        else None
                    )
                    estimation_ready = bool(
                        estimation_policy
                        and estimation_policy.decision is AssessmentReviewDecision.APPROVED
                        and current_review
                        and current_review.id == estimation_policy.assessment_definition_review_id
                        and current_review.decision is AssessmentReviewDecision.APPROVED
                        and performance.assessment_definition_review_id
                        == estimation_policy.assessment_definition_review_id
                        and estimation_policy.reviewed_at <= instant
                        and repository.evidence_authority_is_ready(
                            current_review.evidence_claim_ids,
                            current_review.reviewed_at,
                        )
                        and repository.evidence_authority_is_ready(
                            estimation_policy.evidence_claim_ids,
                            estimation_policy.reviewed_at,
                        )
                    )
                    if stored_estimate is not None and estimate_policy is not None:
                        estimate_projection = AssessmentCapabilityEstimateProjection(
                            estimate_id=stored_estimate.id,
                            estimate=stored_estimate.estimate,
                            unit_or_scale=stored_estimate.unit_or_scale,
                            estimate_scope=stored_estimate.estimate_scope,
                            confidence=stored_estimate.confidence,
                            calculation_method=stored_estimate.calculation_method,
                            source_observation_ids=stored_estimate.source_observation_ids,
                            estimated_at=stored_estimate.estimated_at,
                            valid_until=stored_estimate.valid_until,
                            rule_version=stored_estimate.rule_version,
                            policy_id=estimate_policy.id,
                            policy_reviewed_at=estimate_policy.reviewed_at,
                            policy_reviewed_by=estimate_policy.reviewed_by,
                            applicability_notes=estimate_policy.applicability_notes,
                            uncertainty=estimate_policy.uncertainty,
                            evidence_claim_ids=estimate_policy.evidence_claim_ids,
                        )
                    estimate_uses_current_policy = bool(
                        stored_estimate
                        and estimation_policy
                        and stored_estimate.capability_estimation_policy_id == estimation_policy.id
                    )
                    if estimation_ready and not estimate_uses_current_policy:
                        capability_estimate_status: AssessmentCapabilityEstimateStatus = "ready"
                    elif (
                        estimate_uses_current_policy
                        and stored_estimate is not None
                        and stored_estimate.valid_until is not None
                        and stored_estimate.valid_until <= instant
                    ):
                        capability_estimate_status = "stale"
                    elif estimate_uses_current_policy and estimation_ready:
                        capability_estimate_status = "completed"
                    elif stored_estimate is not None:
                        capability_estimate_status = "policy_superseded"
                    else:
                        capability_estimate_status = "policy_unavailable"
                    result = AssessmentResultProjection(
                        performance_id=performance.id,
                        result_observation_id=observation.id,
                        performed_at=performance.performed_at,
                        measurement=observation.measurement,
                        unit=observation.unit,
                        reliability=observation.reliability,
                        provenance=observation.provenance.model_dump(mode="json"),
                        rule_version=performance.rule_version,
                        next_reassessment_at=performance.performed_at
                        + timedelta(days=review.recommended_reassessment_days),
                        reassessment_interval_source_review_id=review.id,
                        capability_estimate_status=capability_estimate_status,
                        capability_estimate=estimate_projection,
                    )
                else:
                    raise ValueError("assessment performance references a missing observation")
            if result is not None:
                result_status: AssessmentResultStatus = "completed"
            elif selection.decision is not AssessmentDecision.SELECTED:
                result_status = "not_selected"
            elif (
                current_review is None
                or current_review.id != selection.assessment_definition_review_id
                or current_review.decision is not AssessmentReviewDecision.APPROVED
                or not current_review.self_administered
                or current_review.measurement_schema is None
                or not repository.evidence_authority_is_ready(
                    current_review.evidence_claim_ids,
                    current_review.reviewed_at,
                )
            ):
                result_status = "protocol_unavailable"
            elif (
                eligibility is None
                or eligibility.id != selection.assessment_eligibility_review_id
                or not eligibility_active
            ):
                result_status = "eligibility_unavailable"
            else:
                result_status = "ready"
            projected.append(
                AssessmentDecisionProjection(
                    selection_id=selection.id,
                    decision=selection.decision,
                    reason_codes=tuple(item.value for item in selection.reason_codes),
                    rationale=selection.rationale,
                    assessment_definition_id=definition.id,
                    assessment_definition_review_id=selection.assessment_definition_review_id,
                    name=definition.name,
                    domain=definition.domain,
                    intensity=definition.intensity,
                    unit_or_scale=definition.unit_or_scale,
                    protocol_version=definition.protocol_version,
                    protocol_instructions=review.protocol_instructions,
                    result_entry_instructions=review.result_entry_instructions,
                    measurement_schema=review.measurement_schema,
                    applicability_notes=review.applicability_notes,
                    uncertainty=review.uncertainty,
                    evidence_claim_ids=review.evidence_claim_ids,
                    review_version=review.review_version,
                    result_status=result_status,
                    result=result,
                )
            )
        decision_projections = tuple(projected)
        run_projection = AssessmentRunProjection(
            run_id=latest_run.id,
            environment_id=latest_run.environment_id,
            environment_name=(
                environment_by_id[latest_run.environment_id].name
                if latest_run.environment_id in environment_by_id
                else "Historical environment"
            ),
            evaluated_at=latest_run.evaluated_at,
            rule_version=latest_run.rule_version,
            decisions=decision_projections,
        )

    ready_results = sum(item.result_status == "ready" for item in decision_projections)
    selected_results = tuple(
        item for item in decision_projections if item.decision is AssessmentDecision.SELECTED
    )
    latest_run_complete = bool(
        selected_results and all(item.result_status == "completed" for item in selected_results)
    )
    if latest_run_complete and not reviewed_definitions:
        status: AssessmentWorkflowStatus = "protocol_catalog_empty"
        message = "No approved evidence-ready self-administered assessment protocol is available."
    elif latest_run_complete and not due_definition_ids:
        status = "reassessment_not_due"
        next_at = reassessment_schedule.next_reassessment_at
        message = (
            "Assessment results remain direct observations. The next reviewed reassessment "
            f"interval ends at {next_at.isoformat()}."
            if next_at
            else "Assessment results are recorded; no current protocol is due for reassessment."
        )
    elif ready_results:
        status = "result_entry_ready"
        message = "A governed selected assessment is ready for result entry."
    elif selected_results and not latest_run_complete:
        status = "run_blocked"
        message = "The latest selected assessment cannot accept a result under current authority."
    elif latest_run is not None and not latest_run_complete:
        status = "selection_deferred"
        message = "The latest run selected no protocol; review its explicit decision reasons."
    elif eligibility is None:
        status = "eligibility_required"
        message = "An operator eligibility review is required before assessment selection."
    elif eligibility.outcome is AssessmentEligibilityOutcome.REVIEW_REQUIRED:
        status = "eligibility_review_required"
        message = "The current eligibility decision requires further review."
    elif eligibility.outcome is AssessmentEligibilityOutcome.SELECTION_BLOCKED:
        status = "selection_blocked"
        message = "The current eligibility decision does not allow assessment selection."
    elif not eligibility_active:
        status = "eligibility_inactive"
        message = "The current eligibility review is not active at this time."
    elif not reviewed_definitions:
        status = "protocol_catalog_empty"
        message = "No approved evidence-ready self-administered assessment protocol is available."
    elif not environments:
        status = "environment_required"
        message = "At least one persisted environment is required for assessment selection."
    elif latest_run_complete:
        status = "reassessment_due"
        message = "A reviewed reassessment interval has ended; reassessment is now available."
    else:
        status = "ready_to_start"
        message = "Governed assessment selection is ready to start."

    return AssessmentWorkflowProjection(
        athlete_id=athlete.id,
        athlete_display_name=athlete.display_name,
        as_of=instant,
        status=status,
        message=message,
        can_start_run=selection_prerequisites_ready
        and status in ("ready_to_start", "selection_deferred", "reassessment_due"),
        can_record_results=ready_results > 0,
        approved_self_administered_protocol_count=len(reviewed_definitions),
        due_protocol_count=len(due_definition_ids),
        next_reassessment_at=reassessment_schedule.next_reassessment_at,
        reassessment_rule_version=reassessment_schedule.rule_version,
        eligibility=(
            AssessmentEligibilityProjection(
                eligibility_review_id=eligibility.id,
                outcome=eligibility.outcome,
                reviewed_at=eligibility.reviewed_at,
                valid_until=eligibility.valid_until,
                rule_version=eligibility.rule_version,
            )
            if eligibility
            else None
        ),
        environments=tuple(
            AssessmentEnvironmentProjection(environment_id=item.id, name=item.name)
            for item in environments
        ),
        latest_run=run_projection,
    )
