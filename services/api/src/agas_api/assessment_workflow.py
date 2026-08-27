from __future__ import annotations

from datetime import UTC, datetime
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
]
AssessmentResultStatus = Literal[
    "completed",
    "ready",
    "not_selected",
    "protocol_unavailable",
    "eligibility_unavailable",
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
        for definition, review in repository.list_approved_assessment_definitions()
        if review.self_administered and review.measurement_schema is not None
    )
    eligibility_active = bool(
        eligibility
        and eligibility.outcome is AssessmentEligibilityOutcome.SELECTION_ALLOWED
        and eligibility.reviewed_at <= instant < eligibility.valid_until
    )
    selection_prerequisites_ready = bool(
        environments and reviewed_definitions and eligibility_active
    )

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
                observation = repository.get_observation(performance.result_observation_id)
                if observation is not None:
                    result = AssessmentResultProjection(
                        performance_id=performance.id,
                        result_observation_id=observation.id,
                        performed_at=performance.performed_at,
                        measurement=observation.measurement,
                        unit=observation.unit,
                        reliability=observation.reliability,
                        provenance=observation.provenance.model_dump(mode="json"),
                        rule_version=performance.rule_version,
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
    if selected_results and all(item.result_status == "completed" for item in selected_results):
        status: AssessmentWorkflowStatus = "complete"
        message = (
            "Assessment results are recorded as observations. No capability interpretation has "
            "been applied."
        )
    elif ready_results:
        status = "result_entry_ready"
        message = "A governed selected assessment is ready for result entry."
    elif selected_results:
        status = "run_blocked"
        message = "The latest selected assessment cannot accept a result under current authority."
    elif latest_run is not None:
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
        message = "No approved self-administered assessment protocol is available."
    elif not environments:
        status = "environment_required"
        message = "At least one persisted environment is required for assessment selection."
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
        and status in ("ready_to_start", "selection_deferred"),
        can_record_results=ready_results > 0,
        approved_self_administered_protocol_count=len(reviewed_definitions),
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
