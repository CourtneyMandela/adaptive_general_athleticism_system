from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from agas_domain import (
    ExposureEntry,
    ExposureTarget,
    ExposureValidationDecision,
    ProgressionDecision,
    ProgressionDimension,
    ProgressionOutcome,
    SessionExecution,
    SessionPrescription,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from agas_planner import (
    ExposureEntryCalculator,
    ExposureProgressionValidator,
    PrescriptionProgressionApplicator,
    ProgressionEngine,
    ProgressionError,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class ExposureProgressionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exposure_definition_id: UUID
    exposure_progression_policy_id: UUID
    proposed_dose: float = Field(gt=0)
    proposed_for: datetime

    @field_validator("proposed_for")
    @classmethod
    def require_aware_proposed_for(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("exposure target timestamps must include a timezone")
        return value


class CreateProgressionDecisionCommand(BaseModel):
    """Governed internal inputs; not an athlete-facing transport contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    progression_policy_id: UUID
    exposure: ExposureProgressionDraft | None = None
    decided_at: datetime
    revision_prescribed_at: datetime | None = None
    revised_planned_duration_minutes: int | None = Field(default=None, gt=0)

    @field_validator("decided_at", "revision_prescribed_at")
    @classmethod
    def require_aware_progression_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("progression timestamps must include a timezone")
        return value


class AutomaticProgressionDecisionCommand(BaseModel):
    """Athlete request to evaluate history under server-resolved policy authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decided_at: datetime

    @field_validator("decided_at")
    @classmethod
    def require_aware_decided_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("progression timestamps must include a timezone")
        return value


class ProgressionCreationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exposure_entry: ExposureEntry | None = None
    exposure_validation: ExposureValidationDecision | None = None
    progression_decision: ProgressionDecision
    revised_prescription: SessionPrescription | None = None


class ProgressionUseCaseError(RuntimeError):
    """Base error for the persisted post-session progression use case."""


class ProgressionNotFoundError(ProgressionUseCaseError):
    pass


class ProgressionConflictError(ProgressionUseCaseError):
    pass


class ProgressionValidationError(ProgressionUseCaseError):
    pass


class PersistedProgressionService:
    """Derive and append one complete post-session progression chain atomically."""

    _AUTOMATIC_REVISION_DIMENSIONS: ClassVar[frozenset[ProgressionDimension]] = frozenset(
        {
            ProgressionDimension.LOAD,
            ProgressionDimension.REPETITIONS,
            ProgressionDimension.SETS,
            ProgressionDimension.DURATION,
        }
    )

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)

    def execute_automatic(
        self,
        session_execution_id: UUID,
        prescription_id: UUID,
        command: AutomaticProgressionDecisionCommand,
    ) -> ProgressionCreationResult:
        """Resolve one simple policy from immutable prescription authority and evaluate it."""

        execution = self.repository.get_session_execution(session_execution_id)
        if execution is None:
            raise ProgressionNotFoundError("session execution does not exist")
        prescription = self.repository.get_session_prescription(prescription_id)
        if prescription is None:
            raise ProgressionNotFoundError("session prescription does not exist")
        if not any(item.prescription_id == prescription.id for item in execution.items):
            raise ProgressionValidationError(
                "session prescription does not belong to the execution"
            )
        policies = self.repository.list_progression_policies_by_reference(
            prescription.progression_rule_reference
        )
        if len(policies) != 1:
            reason = (
                "no progression policy matches the prescription rule reference"
                if not policies
                else "multiple progression policies match the prescription rule reference"
            )
            raise ProgressionValidationError(reason)
        policy = policies[0]
        if policy.exposure_type is not None:
            raise ProgressionValidationError(
                "exposure-sensitive progression requires governed configuration"
            )
        if policy.adjustment.dimension not in {
            ProgressionDimension.LOAD,
            ProgressionDimension.REPETITIONS,
        }:
            raise ProgressionValidationError(
                f"{policy.adjustment.dimension.value} progression requires governed configuration"
            )
        return self.execute(
            session_execution_id,
            prescription_id,
            CreateProgressionDecisionCommand(
                progression_policy_id=policy.id,
                decided_at=command.decided_at,
                revision_prescribed_at=command.decided_at,
            ),
        )

    def execute(
        self,
        session_execution_id: UUID,
        prescription_id: UUID,
        command: CreateProgressionDecisionCommand,
    ) -> ProgressionCreationResult:
        try:
            result = self._build(session_execution_id, prescription_id, command)
            if result.exposure_entry is not None:
                self.repository.add_exposure_entry(result.exposure_entry)
                self.session.flush()
            if result.exposure_validation is not None:
                self.repository.add_exposure_validation_decision(result.exposure_validation)
                self.session.flush()
            self.repository.add_progression_decision(result.progression_decision)
            self.session.flush()
            if result.revised_prescription is not None:
                self.repository.add_session_prescription(result.revised_prescription)
            self.session.commit()
            return result
        except ProgressionUseCaseError:
            self.session.rollback()
            raise
        except (ProgressionError, DomainIntegrityError, ValueError) as error:
            self.session.rollback()
            raise ProgressionValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise ProgressionConflictError(
                "the execution and prescription already have a progression result"
            ) from error

    def _build(
        self,
        session_execution_id: UUID,
        prescription_id: UUID,
        command: CreateProgressionDecisionCommand,
    ) -> ProgressionCreationResult:
        if (
            self.repository.get_progression_decision_by_execution_and_prescription(
                session_execution_id, prescription_id
            )
            is not None
        ):
            raise ProgressionConflictError(
                "the execution and prescription already have a progression result"
            )
        execution = self.repository.get_session_execution(session_execution_id)
        if execution is None:
            raise ProgressionNotFoundError("session execution does not exist")
        prescription = self.repository.get_session_prescription(prescription_id)
        if prescription is None:
            raise ProgressionNotFoundError("session prescription does not exist")
        if not any(item.prescription_id == prescription.id for item in execution.items):
            raise ProgressionValidationError(
                "session prescription does not belong to the execution"
            )
        adherence = self.repository.get_session_adherence_by_execution_and_prescription(
            execution.id, prescription.id
        )
        if adherence is None:
            raise ProgressionNotFoundError("session adherence does not exist")
        policy = self.repository.get_progression_policy(command.progression_policy_id)
        if policy is None:
            raise ProgressionNotFoundError("progression policy does not exist")
        post_session_decisions = self.repository.list_post_session_safety_decisions(execution.id)
        if not post_session_decisions:
            raise ProgressionValidationError(
                "progression requires a persisted post-session safety decision"
            )

        exposure_entry = None
        exposure_validation = None
        if policy.exposure_type is None:
            if command.exposure is not None:
                raise ProgressionValidationError(
                    "a progression policy without exposure tracking rejects exposure input"
                )
        else:
            if command.exposure is None:
                raise ProgressionValidationError(
                    "the progression policy requires explicit exposure validation"
                )
            exposure_entry, exposure_validation = self._build_exposure(
                execution=execution,
                prescription=prescription,
                exposure=command.exposure,
                decided_at=command.decided_at,
            )

        progression_decision = ProgressionEngine().decide(
            prescription=prescription,
            execution=execution,
            adherence=adherence,
            policy=policy,
            decided_at=command.decided_at,
            post_session_decisions=post_session_decisions,
            exposure_validation=exposure_validation,
        )
        revised_prescription = None
        if (
            progression_decision.outcome is ProgressionOutcome.PROGRESS
            and policy.adjustment.dimension in self._AUTOMATIC_REVISION_DIMENSIONS
        ):
            if command.revision_prescribed_at is None:
                raise ProgressionValidationError(
                    "an automatically supported progression requires revision_prescribed_at"
                )
            if command.revision_prescribed_at < command.decided_at:
                raise ProgressionValidationError(
                    "a revised prescription cannot predate its progression decision"
                )
            revised_prescription = PrescriptionProgressionApplicator().apply(
                prescription=prescription,
                decision=progression_decision,
                policy=policy,
                prescribed_at=command.revision_prescribed_at,
                planned_duration_minutes=command.revised_planned_duration_minutes,
            )
        return ProgressionCreationResult(
            exposure_entry=exposure_entry,
            exposure_validation=exposure_validation,
            progression_decision=progression_decision,
            revised_prescription=revised_prescription,
        )

    def _build_exposure(
        self,
        *,
        execution: SessionExecution,
        prescription: SessionPrescription,
        exposure: ExposureProgressionDraft,
        decided_at: datetime,
    ) -> tuple[ExposureEntry, ExposureValidationDecision]:
        definition = self.repository.get_exposure_definition(exposure.exposure_definition_id)
        if definition is None:
            raise ProgressionNotFoundError("exposure definition does not exist")
        if (
            self.repository.get_exposure_entry_for_execution_prescription_definition(
                execution.id, prescription.id, definition.id
            )
            is not None
        ):
            raise ProgressionConflictError(
                "the execution and prescription already have this exposure entry"
            )
        exposure_policy = self.repository.get_exposure_progression_policy(
            exposure.exposure_progression_policy_id
        )
        if exposure_policy is None:
            raise ProgressionNotFoundError("exposure progression policy does not exist")
        entry = ExposureEntryCalculator().calculate(
            execution=execution,
            prescription=prescription,
            definition=definition,
        )
        target = ExposureTarget(
            athlete_id=execution.athlete_id,
            prescription_id=prescription.id,
            exposure_type=definition.exposure_type,
            proposed_dose=exposure.proposed_dose,
            dose_unit=definition.dose_unit,
            proposed_for=exposure.proposed_for,
        )
        prior_entries = self.repository.list_exposure_entries_for_athlete(
            execution.athlete_id, definition.exposure_type.value
        )
        decision = ExposureProgressionValidator().validate(
            target=target,
            policy=exposure_policy,
            entries=(*prior_entries, entry),
            decided_at=decided_at,
        )
        return entry, decision
