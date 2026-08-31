from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from agas_domain import (
    AssessmentContext,
    AssessmentDecision,
    AssessmentDefinition,
    AssessmentDefinitionReview,
    AssessmentEligibilityOutcome,
    AssessmentSelection,
    AssessmentSelectionRun,
    CapabilityDomain,
    Confidence,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import AdaptiveAssessmentSelector, EnvironmentSnapshotBuilder
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.assessment_catalog import list_evidence_ready_assessment_definitions
from agas_api.assessment_schedule import resolve_assessment_reassessment_schedule

NonEmptyText = Annotated[str, Field(min_length=1)]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class CreateAssessmentSelectionRunCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    environment_id: UUID
    body_mass_kg: float | None = Field(default=None, gt=0)
    training_age_months_by_domain: dict[CapabilityDomain, Annotated[int, Field(ge=0)]] = Field(
        default_factory=dict
    )
    exercise_skill_tags: tuple[NonEmptyText, ...] = ()
    recent_exposure_tags: tuple[NonEmptyText, ...] = ()
    evaluated_at: datetime
    reliability: Confidence
    provenance: Provenance

    @field_validator("evaluated_at")
    @classmethod
    def require_aware_evaluated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_tags(self) -> CreateAssessmentSelectionRunCommand:
        for field_name in ("exercise_skill_tags", "recent_exposure_tags"):
            values = getattr(self, field_name)
            if len(set(values)) != len(values):
                raise ValueError(f"{field_name} must not contain duplicates")
        return self


class AssessmentRunDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    definition: AssessmentDefinition
    definition_review: AssessmentDefinitionReview
    selection: AssessmentSelection


class AssessmentSelectionRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run: AssessmentSelectionRun
    context_observation: Observation
    decisions: tuple[AssessmentRunDecision, ...]


class AssessmentSelectionRunError(RuntimeError):
    """Base error for persisted assessment-selection runs."""


class AssessmentSelectionRunNotFoundError(AssessmentSelectionRunError):
    pass


class AssessmentSelectionRunConflictError(AssessmentSelectionRunError):
    pass


class AssessmentSelectionRunValidationError(AssessmentSelectionRunError):
    pass


class PersistedAssessmentSelectionRunService:
    """Build one governed self-administered assessment selection snapshot atomically."""

    rule_version = "assessment-selection-run@3.0.0"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute(
        self, athlete_id: UUID, command: CreateAssessmentSelectionRunCommand
    ) -> AssessmentSelectionRunResult:
        try:
            result = self._build(athlete_id, command)
            self.repository.add_observation(result.context_observation)
            self.session.flush()
            for decision in result.decisions:
                self.repository.add_assessment_selection(decision.selection)
            self.session.flush()
            self.repository.add_assessment_selection_run(result.run)
            self.session.commit()
            return result
        except AssessmentSelectionRunError:
            self.session.rollback()
            raise
        except (DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise AssessmentSelectionRunValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise AssessmentSelectionRunConflictError(
                "assessment selection run conflicts with persisted athlete history"
            ) from error

    def _build(
        self, athlete_id: UUID, command: CreateAssessmentSelectionRunCommand
    ) -> AssessmentSelectionRunResult:
        if self.repository.get_athlete(athlete_id) is None:
            raise AssessmentSelectionRunNotFoundError("athlete does not exist")
        if command.evaluated_at > _utc_now():
            raise AssessmentSelectionRunValidationError("evaluated_at cannot be in the future")
        environment = self.repository.get_environment(command.environment_id)
        if environment is None or environment.athlete_id != athlete_id:
            raise AssessmentSelectionRunNotFoundError("environment does not exist")

        eligibility = self.repository.get_current_assessment_eligibility_review(athlete_id)
        if eligibility is None:
            raise AssessmentSelectionRunConflictError(
                "athlete has no current assessment eligibility review"
            )
        if eligibility.outcome is not AssessmentEligibilityOutcome.SELECTION_ALLOWED:
            raise AssessmentSelectionRunConflictError(
                "current assessment eligibility review does not allow selection"
            )
        if not eligibility.reviewed_at <= command.evaluated_at < eligibility.valid_until:
            raise AssessmentSelectionRunConflictError(
                "current assessment eligibility review is not active at evaluation time"
            )

        reviewed_definitions = tuple(
            (definition, review)
            for definition, review in list_evidence_ready_assessment_definitions(self.repository)
            if review.self_administered and review.measurement_schema is not None
        )
        if not reviewed_definitions:
            raise AssessmentSelectionRunConflictError(
                "no approved evidence-ready self-administered assessment definitions with "
                "measurement schemas are available"
            )

        runs = self.repository.list_assessment_selection_runs(athlete_id)
        if runs:
            for selection_id in runs[0].selection_ids:
                selection = self.repository.get_assessment_selection(selection_id)
                if selection is None:
                    raise AssessmentSelectionRunValidationError(
                        "latest assessment run references a missing selection"
                    )
                if (
                    selection.decision is AssessmentDecision.SELECTED
                    and self.repository.get_assessment_performance_for_selection(selection.id)
                    is None
                ):
                    raise AssessmentSelectionRunConflictError(
                        "latest assessment run has selected results awaiting completion"
                    )

        reassessment_schedule = resolve_assessment_reassessment_schedule(
            self.repository,
            athlete_id,
            reviewed_definitions,
            command.evaluated_at,
        )
        due_definition_ids = set(reassessment_schedule.due_definition_ids)
        reviewed_definitions = tuple(
            item for item in reviewed_definitions if item[0].id in due_definition_ids
        )
        if not reviewed_definitions:
            next_at = reassessment_schedule.next_reassessment_at
            detail = f"; next reviewed interval ends at {next_at.isoformat()}" if next_at else ""
            raise AssessmentSelectionRunConflictError(
                f"no governed assessment protocol is due for self-service selection{detail}"
            )

        availability = self.repository.list_equipment_availability(environment.id)
        equipment_ids = tuple(dict.fromkeys(item.equipment_id for item in availability))
        equipment = tuple(
            item
            for equipment_id in equipment_ids
            if (item := self.repository.get_equipment(equipment_id)) is not None
        )
        if len(equipment) != len(equipment_ids):
            raise AssessmentSelectionRunValidationError(
                "environment availability references missing equipment"
            )
        snapshot = EnvironmentSnapshotBuilder().build(
            environment, equipment, availability, command.evaluated_at
        )
        equipment_categories = tuple(
            sorted({item.category for item in snapshot.available_equipment})
        )
        training_history = {
            domain.value: months for domain, months in command.training_age_months_by_domain.items()
        }
        context_observation = Observation(
            created_at=command.evaluated_at,
            athlete_id=athlete_id,
            observed_at=command.evaluated_at,
            observation_type="assessment_selection_context_report",
            measurement={
                "body_mass_kg": command.body_mass_kg,
                "training_age_months_by_domain": training_history,
                "exercise_skill_tags": list(command.exercise_skill_tags),
                "recent_exposure_tags": list(command.recent_exposure_tags),
                "environment_id": str(environment.id),
                "available_equipment_categories": list(equipment_categories),
                "source_availability_ids": [str(item) for item in snapshot.source_availability_ids],
                "assessment_eligibility_review_id": str(eligibility.id),
            },
            source=ObservationSource.USER_REPORT,
            reliability=command.reliability,
            context={"assessment_selection_rule_version": self.rule_version},
            provenance=command.provenance,
        )
        source_observation_ids = tuple(
            dict.fromkeys((context_observation.id, *eligibility.source_observation_ids))
        )
        assessment_context = AssessmentContext(
            athlete_id=athlete_id,
            source_observation_ids=source_observation_ids,
            body_mass_kg=command.body_mass_kg,
            health_screening_completed=True,
            training_age_months_by_domain=training_history,
            exercise_skill_tags=command.exercise_skill_tags,
            recent_exposure_tags=command.recent_exposure_tags,
            available_equipment_categories=equipment_categories,
            evaluated_at=command.evaluated_at,
        )
        selections = AdaptiveAssessmentSelector(rule_version=self.rule_version).select_reviewed(
            assessment_context,
            reviewed_definitions,
            eligibility.id,
        )
        run = AssessmentSelectionRun(
            created_at=command.evaluated_at,
            athlete_id=athlete_id,
            assessment_eligibility_review_id=eligibility.id,
            environment_id=environment.id,
            context_observation_id=context_observation.id,
            selection_ids=tuple(item.id for item in selections),
            evaluated_at=command.evaluated_at,
            rule_version=self.rule_version,
        )
        return AssessmentSelectionRunResult(
            run=run,
            context_observation=context_observation,
            decisions=tuple(
                AssessmentRunDecision(
                    definition=definition,
                    definition_review=review,
                    selection=selection,
                )
                for (definition, review), selection in zip(
                    reviewed_definitions, selections, strict=True
                )
            ),
        )
