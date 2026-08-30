from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from agas_domain import (
    AssessmentReviewDecision,
    InitialPlanningCandidateContext,
    InitialPlanningContextDraft,
    InitialPlanningContextReview,
)
from agas_domain.persistence.repository import DomainIntegrityError, DomainRepository
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agas_api.identity import AuthorizedRole
from agas_api.initial_planning import (
    CreateInitialStrategyCommand,
    InitialPlanningConflictError,
    InitialPlanningNotFoundError,
    InitialPlanningUseCaseError,
    InitialPlanningValidationError,
    InitialStrategyCreationResult,
    PersistedInitialPlanningService,
)

NonEmptyText = Annotated[str, Field(min_length=1)]


class OperatorInitialPlanningContextDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    priority_policy_id: UUID
    priority_policy_review_id: UUID
    candidate_contexts: Annotated[tuple[InitialPlanningCandidateContext, ...], Field(min_length=1)]
    horizon_months: int = Field(ge=6, le=24)
    review_after_days: int = Field(ge=1)
    authored_at: datetime
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("authored_at")
    @classmethod
    def require_aware_authored_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authored_at must include a timezone")
        return value

    @field_validator("applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("draft review metadata must not be blank")
        return normalized

    @model_validator(mode="after")
    def require_one_context_per_adaptation(self) -> OperatorInitialPlanningContextDraftRequest:
        adaptation_ids = tuple(item.adaptation_id for item in self.candidate_contexts)
        if len(set(adaptation_ids)) != len(adaptation_ids):
            raise ValueError("candidate_contexts must contain each adaptation once")
        return self


class OperatorInitialPlanningContextReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: AssessmentReviewDecision
    reviewed_at: datetime
    applicability_rationale: NonEmptyText
    uncertainty: NonEmptyText

    @field_validator("reviewed_at")
    @classmethod
    def require_aware_reviewed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must include a timezone")
        return value

    @field_validator("applicability_rationale", "uncertainty")
    @classmethod
    def require_meaningful_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("review metadata must not be blank")
        return normalized


class CreateInitialStrategyFromContextReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    generated_at: datetime

    @field_validator("generated_at")
    @classmethod
    def require_aware_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        return value


class InitialPlanningContextError(RuntimeError):
    pass


class InitialPlanningContextNotFoundError(InitialPlanningContextError):
    pass


class InitialPlanningContextConflictError(InitialPlanningContextError):
    pass


class InitialPlanningContextValidationError(InitialPlanningContextError):
    pass


class PersistedInitialPlanningContextService:
    draft_version = "initial-planning-context-draft@1.0.0"
    review_version = "initial-planning-context-review@1.0.0"

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DomainRepository(session)
        self.planning = PersistedInitialPlanningService(session)

    def create_draft(
        self,
        athlete_id: UUID,
        request: OperatorInitialPlanningContextDraftRequest,
        authority: AuthorizedRole,
    ) -> InitialPlanningContextDraft:
        try:
            if request.authored_at < authority.assigned_at:
                raise InitialPlanningContextValidationError(
                    "context draft cannot predate the author role assignment"
                )
            validation_command = CreateInitialStrategyCommand(
                priority_policy_id=request.priority_policy_id,
                priority_policy_review_id=request.priority_policy_review_id,
                candidate_contexts=request.candidate_contexts,
                generated_at=request.authored_at,
                horizon_months=request.horizon_months,
                review_after_days=request.review_after_days,
                reviewed_by=f"account:{authority.account_id}",
                review_authority_assignment_id=authority.assignment_id,
                applicability_rationale=request.applicability_rationale,
                uncertainty=request.uncertainty,
            )
            self.planning.preview(athlete_id, validation_command)
            draft = InitialPlanningContextDraft(
                athlete_id=athlete_id,
                priority_policy_id=request.priority_policy_id,
                priority_policy_review_id=request.priority_policy_review_id,
                candidate_contexts=request.candidate_contexts,
                horizon_months=request.horizon_months,
                review_after_days=request.review_after_days,
                authored_by_account_id=authority.account_id,
                author_authority_assignment_id=authority.assignment_id,
                authored_at=request.authored_at,
                applicability_rationale=request.applicability_rationale,
                uncertainty=request.uncertainty,
                draft_version=self.draft_version,
            )
            self.repository.add_initial_planning_context_draft(draft)
            self.session.commit()
            return draft
        except InitialPlanningContextError:
            self.session.rollback()
            raise
        except InitialPlanningNotFoundError as error:
            self.session.rollback()
            raise InitialPlanningContextNotFoundError(str(error)) from error
        except (InitialPlanningUseCaseError, DomainIntegrityError) as error:
            self.session.rollback()
            raise InitialPlanningContextValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise InitialPlanningContextConflictError(
                "initial planning context draft conflicts with persisted state"
            ) from error

    def review_draft(
        self,
        draft_id: UUID,
        request: OperatorInitialPlanningContextReviewRequest,
        authority: AuthorizedRole,
    ) -> InitialPlanningContextReview:
        try:
            draft = self.repository.get_initial_planning_context_draft(draft_id)
            if draft is None:
                raise InitialPlanningContextNotFoundError(
                    "initial planning context draft does not exist"
                )
            if self.repository.get_initial_planning_context_review_by_draft(draft.id) is not None:
                raise InitialPlanningContextConflictError(
                    "initial planning context draft already has a review"
                )
            if request.reviewed_at < draft.authored_at:
                raise InitialPlanningContextValidationError(
                    "context review cannot predate its draft"
                )
            if request.reviewed_at < authority.assigned_at:
                raise InitialPlanningContextValidationError(
                    "context review cannot predate the reviewer role assignment"
                )
            if request.decision is AssessmentReviewDecision.APPROVED:
                self.planning.preview(
                    draft.athlete_id,
                    self._command_from_draft(
                        draft,
                        generated_at=request.reviewed_at,
                        account_id=authority.account_id,
                        assignment_id=authority.assignment_id,
                        applicability_rationale=request.applicability_rationale,
                        uncertainty=request.uncertainty,
                    ),
                )
            review = InitialPlanningContextReview(
                draft_id=draft.id,
                decision=request.decision,
                reviewed_by_account_id=authority.account_id,
                review_authority_assignment_id=authority.assignment_id,
                reviewed_at=request.reviewed_at,
                applicability_rationale=request.applicability_rationale,
                uncertainty=request.uncertainty,
                review_version=self.review_version,
            )
            self.repository.add_initial_planning_context_review(review)
            self.session.commit()
            return review
        except InitialPlanningContextError:
            self.session.rollback()
            raise
        except InitialPlanningNotFoundError as error:
            self.session.rollback()
            raise InitialPlanningContextNotFoundError(str(error)) from error
        except (InitialPlanningUseCaseError, DomainIntegrityError) as error:
            self.session.rollback()
            raise InitialPlanningContextValidationError(str(error)) from error
        except IntegrityError as error:
            self.session.rollback()
            raise InitialPlanningContextConflictError(
                "initial planning context draft already has a review"
            ) from error

    def create_strategy(
        self,
        review_id: UUID,
        request: CreateInitialStrategyFromContextReviewRequest,
        authority: AuthorizedRole,
    ) -> InitialStrategyCreationResult:
        review = self.repository.get_initial_planning_context_review(review_id)
        if review is None:
            raise InitialPlanningContextNotFoundError(
                "initial planning context review does not exist"
            )
        draft = self.repository.get_initial_planning_context_draft(review.draft_id)
        if draft is None:
            raise InitialPlanningContextNotFoundError(
                "initial planning context draft does not exist"
            )
        if review.decision is not AssessmentReviewDecision.APPROVED:
            raise InitialPlanningContextValidationError(
                "initial strategy requires an approved context review"
            )
        if (
            authority.account_id != review.reviewed_by_account_id
            or authority.assignment_id != review.review_authority_assignment_id
        ):
            raise InitialPlanningContextValidationError(
                "the approving reviewer must create the initial strategy"
            )
        if request.generated_at < review.reviewed_at:
            raise InitialPlanningContextValidationError(
                "initial strategy cannot predate its context review"
            )
        command = self._command_from_draft(
            draft,
            generated_at=request.generated_at,
            account_id=review.reviewed_by_account_id,
            assignment_id=review.review_authority_assignment_id,
            applicability_rationale=(
                f"Approved context draft {draft.id}. {review.applicability_rationale} "
                f"Draft rationale: {draft.applicability_rationale}"
            ),
            uncertainty=(
                f"Review uncertainty: {review.uncertainty} Draft uncertainty: {draft.uncertainty}"
            ),
            draft_id=draft.id,
            review_id=review.id,
        )
        try:
            return self.planning.execute(draft.athlete_id, command)
        except InitialPlanningNotFoundError as error:
            raise InitialPlanningContextNotFoundError(str(error)) from error
        except InitialPlanningConflictError as error:
            raise InitialPlanningContextConflictError(str(error)) from error
        except InitialPlanningValidationError as error:
            raise InitialPlanningContextValidationError(str(error)) from error

    @staticmethod
    def _command_from_draft(
        draft: InitialPlanningContextDraft,
        *,
        generated_at: datetime,
        account_id: UUID,
        assignment_id: UUID,
        applicability_rationale: str,
        uncertainty: str,
        draft_id: UUID | None = None,
        review_id: UUID | None = None,
    ) -> CreateInitialStrategyCommand:
        return CreateInitialStrategyCommand(
            priority_policy_id=draft.priority_policy_id,
            priority_policy_review_id=draft.priority_policy_review_id,
            candidate_contexts=draft.candidate_contexts,
            generated_at=generated_at,
            horizon_months=draft.horizon_months,
            review_after_days=draft.review_after_days,
            reviewed_by=f"account:{account_id}",
            review_authority_assignment_id=assignment_id,
            candidate_context_draft_id=draft_id,
            candidate_context_review_id=review_id,
            applicability_rationale=applicability_rationale,
            uncertainty=uncertainty,
        )
