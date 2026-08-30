from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from agas_domain import InitialPlanningContextDraft, InitialPlanningContextReview
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from agas_api import __version__
from agas_api.assessment_catalog import (
    ReviewedAssessmentCatalogItem,
    list_reviewed_assessment_catalog,
)
from agas_api.assessment_estimation import (
    AssessmentCapabilityEstimateResult,
    AssessmentCapabilityEstimationConflictError,
    AssessmentCapabilityEstimationNotFoundError,
    AssessmentCapabilityEstimationValidationError,
    PersistedAssessmentCapabilityEstimationService,
)
from agas_api.assessment_governance import (
    AssessmentGovernanceProjection,
    AssessmentGovernanceProjectionError,
    AssessmentGovernanceProjector,
)
from agas_api.assessment_performance import (
    AssessmentPerformanceConflictError,
    AssessmentPerformanceNotFoundError,
    AssessmentPerformanceResult,
    AssessmentPerformanceValidationError,
    PersistedAssessmentPerformanceService,
    RecordAssessmentPerformanceCommand,
)
from agas_api.assessment_selection import (
    AssessmentSelectionRunConflictError,
    AssessmentSelectionRunNotFoundError,
    AssessmentSelectionRunResult,
    AssessmentSelectionRunValidationError,
    CreateAssessmentSelectionRunCommand,
    PersistedAssessmentSelectionRunService,
)
from agas_api.assessment_workflow import (
    AssessmentWorkflowNotFoundError,
    AssessmentWorkflowProjection,
    get_assessment_workflow_projection,
)
from agas_api.athletic_dashboard import (
    AthleticDashboardNotFoundError,
    AthleticDashboardProjection,
    get_athletic_dashboard_projection,
)
from agas_api.block_creation import (
    BlockCreationConflictError,
    BlockCreationNotFoundError,
    BlockCreationValidationError,
    BlockPlanCreationResult,
)
from agas_api.block_preparation import (
    BlockPreparationNotFoundError,
    BlockPreparationProjection,
    BlockPreparationProjectionError,
    BlockPreparationProjector,
)
from agas_api.block_review_application import (
    BlockReviewConflictError,
    BlockReviewCreationResult,
    BlockReviewNotFoundError,
    BlockReviewValidationError,
)
from agas_api.current_week import (
    CurrentWeekConflictError,
    CurrentWeekNotFoundError,
    CurrentWeekProjection,
    CurrentWeekProjector,
)
from agas_api.database import database_session, database_session_dependency
from agas_api.environment_management import (
    AthleteEnvironmentProjection,
    EnvironmentManagementConflictError,
    EnvironmentManagementNotFoundError,
    EnvironmentManagementValidationError,
    EquipmentStateReportResult,
    PersistedEquipmentStateService,
    RecordEquipmentStateCommand,
    get_athlete_environment_projection,
)
from agas_api.environment_prescription_revision import (
    EnvironmentPrescriptionRevisionConflictError,
    EnvironmentPrescriptionRevisionNotFoundError,
    EnvironmentPrescriptionRevisionResult,
    EnvironmentPrescriptionRevisionValidationError,
)
from agas_api.exercise_reresolution import (
    ExerciseReResolutionConflictError,
    ExerciseReResolutionNotFoundError,
    ExerciseReResolutionResult,
    ExerciseReResolutionValidationError,
)
from agas_api.first_week_preparation import (
    FirstWeekPreparationNotFoundError,
    FirstWeekPreparationProjection,
    FirstWeekPreparationProjectionError,
    FirstWeekPreparationProjector,
)
from agas_api.identity import (
    AuthenticatedPrincipal,
    AuthorizedRole,
    OwnershipAuthorizer,
    assessment_reviewer_dependency,
    authenticated_principal_dependency,
    ownership_authorizer_dependency,
    planning_reviewer_dependency,
)
from agas_api.initial_planning import (
    InitialPlanningConflictError,
    InitialPlanningNotFoundError,
    InitialPlanningValidationError,
    InitialStrategyCreationResult,
)
from agas_api.initial_planning_context import (
    CreateInitialStrategyFromContextReviewRequest,
    InitialPlanningContextConflictError,
    InitialPlanningContextNotFoundError,
    InitialPlanningContextValidationError,
    OperatorInitialPlanningContextDraftRequest,
    OperatorInitialPlanningContextReviewRequest,
    PersistedInitialPlanningContextService,
)
from agas_api.initial_planning_preparation import (
    InitialPlanningPreparationNotFoundError,
    InitialPlanningPreparationProjection,
    InitialPlanningPreparationProjectionError,
    InitialPlanningPreparationProjector,
)
from agas_api.onboarding import (
    AthleteOnboardingConflictError,
    AthleteOnboardingNotFoundError,
    AthleteOnboardingResult,
    AthleteOnboardingValidationError,
    CreateAthleteOnboardingCommand,
    OnboardingEquipmentOption,
    PersistedAthleteOnboardingService,
    list_onboarding_equipment,
)
from agas_api.operator_block_preparation import (
    OperatorBlockPlanRequest,
    execute_operator_block_creation,
)
from agas_api.operator_environment_review import (
    OperatorEnvironmentPrescriptionRevisionRequest,
    OperatorExerciseReResolutionRequest,
    execute_operator_environment_prescription_revision,
    execute_operator_exercise_reresolution,
)
from agas_api.operator_initial_planning import (
    OperatorInitialStrategyRequest,
    execute_operator_initial_strategy,
)
from agas_api.operator_planning_queue import (
    PlanningReviewQueueProjection,
    PlanningReviewQueueProjectionError,
    PlanningReviewQueueProjector,
)
from agas_api.operator_post_block import (
    OperatorBlockReviewRequest,
    OperatorReplanningRequest,
    execute_operator_block_review,
    execute_operator_replanning,
)
from agas_api.operator_resource_preparation import (
    OperatorResourceDemandRequest,
    execute_operator_resource_preparation,
)
from agas_api.operator_review_queue import (
    EnvironmentReviewQueueProjection,
    EnvironmentReviewQueueProjector,
    OperatorReviewQueueProjectionError,
    PostBlockReviewQueueProjection,
    PostBlockReviewQueueProjector,
)
from agas_api.operator_weekly_planning import (
    OperatorWeeklyPlanRequest,
    execute_operator_weekly_plan_creation,
)
from agas_api.planning_status import (
    PlanningStatusNotFoundError,
    PlanningStatusProjection,
    get_planning_status_projection,
)
from agas_api.post_block_preparation import (
    BlockReviewPreparationProjection,
    BlockReviewPreparationProjector,
    PostBlockPreparationNotFoundError,
    PostBlockPreparationProjectionError,
    ReplanningPreparationProjection,
    ReplanningPreparationProjector,
)
from agas_api.progression_application import (
    AutomaticProgressionDecisionCommand,
    PersistedProgressionService,
    ProgressionConflictError,
    ProgressionCreationResult,
    ProgressionNotFoundError,
    ProgressionValidationError,
)
from agas_api.replanning import (
    PostBlockReplanningResult,
    ReplanningConflictError,
    ReplanningNotFoundError,
    ReplanningValidationError,
)
from agas_api.resource_demand_preparation import (
    ResourceDemandPreparationNotFoundError,
    ResourceDemandPreparationProjection,
    ResourceDemandPreparationProjectionError,
    ResourceDemandPreparationProjector,
)
from agas_api.resource_preparation import (
    ResourceDemandPreparationResult,
    ResourcePreparationConflictError,
    ResourcePreparationNotFoundError,
    ResourcePreparationValidationError,
)
from agas_api.session_recording import (
    CreateSessionExecutionCommand,
    CreateSessionSafetyDecisionCommand,
    PersistedSessionExecutionService,
    PersistedSessionSafetyService,
    SessionExecutionCreationResult,
    SessionRecordingConflictError,
    SessionRecordingNotFoundError,
    SessionRecordingValidationError,
    SessionSafetyCreationResult,
)
from agas_api.settings import get_settings
from agas_api.weekly_availability_confirmation import (
    ConfirmWeeklyAvailabilityCommand,
    PersistedWeeklyAvailabilityConfirmationService,
    WeeklyAvailabilityConfirmationConflictError,
    WeeklyAvailabilityConfirmationNotFoundError,
    WeeklyAvailabilityConfirmationResult,
    WeeklyAvailabilityConfirmationValidationError,
)
from agas_api.weekly_planning import (
    WeeklyPlanConflictError,
    WeeklyPlanCreationResult,
    WeeklyPlanNotFoundError,
    WeeklyPlanValidationError,
)
from agas_api.weekly_roll_forward import (
    PersistedWeeklyPlanRollForwardService,
    RollForwardWeeklyPlanCommand,
    WeeklyPlanRollForwardConflictError,
    WeeklyPlanRollForwardNotFoundError,
    WeeklyPlanRollForwardResult,
    WeeklyPlanRollForwardValidationError,
)

settings = get_settings()

app = FastAPI(
    title="Adaptive General Athleticism System API",
    version=__version__,
    description="Domain-first planning, execution, review, and daily-use API.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).rstrip("/") for origin in settings.cors_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@contextmanager
def _session_scope() -> Iterator[Session]:
    session = database_session()
    try:
        yield session
    finally:
        session.close()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agas-api", "version": __version__}


@app.get(
    "/v1/operator/assessment-governance",
    tags=["operator"],
    response_model=AssessmentGovernanceProjection,
)
def get_assessment_governance(
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(assessment_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query(alias="at")] = None,
) -> AssessmentGovernanceProjection:
    try:
        return AssessmentGovernanceProjector(session).project(projected_at)
    except AssessmentGovernanceProjectionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/operator/environment-review-queue",
    tags=["operator"],
    response_model=EnvironmentReviewQueueProjection,
)
def get_environment_review_queue(
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query()] = None,
) -> EnvironmentReviewQueueProjection:
    try:
        return EnvironmentReviewQueueProjector(session).project(projected_at)
    except (OperatorReviewQueueProjectionError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.get(
    "/v1/operator/post-block-review-queue",
    tags=["operator"],
    response_model=PostBlockReviewQueueProjection,
)
def get_post_block_review_queue(
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query(alias="at")] = None,
) -> PostBlockReviewQueueProjection:
    try:
        return PostBlockReviewQueueProjector(session).project(projected_at)
    except (OperatorReviewQueueProjectionError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.get(
    "/v1/operator/planning-review-queue",
    tags=["operator"],
    response_model=PlanningReviewQueueProjection,
)
def get_planning_review_queue(
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query(alias="at")] = None,
) -> PlanningReviewQueueProjection:
    try:
        return PlanningReviewQueueProjector(session).project(projected_at)
    except (PlanningReviewQueueProjectionError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.get(
    "/v1/operator/athletes/{athlete_id}/initial-planning-preparation",
    tags=["operator"],
    response_model=InitialPlanningPreparationProjection,
)
def get_operator_initial_planning_preparation(
    athlete_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query(alias="at")] = None,
) -> InitialPlanningPreparationProjection:
    try:
        return InitialPlanningPreparationProjector(session).project(athlete_id, projected_at)
    except InitialPlanningPreparationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InitialPlanningPreparationProjectionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/athletes/{athlete_id}/initial-planning-context-drafts",
    tags=["operator"],
    response_model=InitialPlanningContextDraft,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_initial_planning_context_draft(
    athlete_id: UUID,
    command: OperatorInitialPlanningContextDraftRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> InitialPlanningContextDraft:
    try:
        return PersistedInitialPlanningContextService(session).create_draft(
            athlete_id, command, authority
        )
    except InitialPlanningContextNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InitialPlanningContextConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InitialPlanningContextValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/initial-planning-context-drafts/{draft_id}/reviews",
    tags=["operator"],
    response_model=InitialPlanningContextReview,
    status_code=status.HTTP_201_CREATED,
)
def review_operator_initial_planning_context_draft(
    draft_id: UUID,
    command: OperatorInitialPlanningContextReviewRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> InitialPlanningContextReview:
    try:
        return PersistedInitialPlanningContextService(session).review_draft(
            draft_id, command, authority
        )
    except InitialPlanningContextNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InitialPlanningContextConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InitialPlanningContextValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/initial-planning-context-reviews/{review_id}/strategy",
    tags=["operator"],
    response_model=InitialStrategyCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_initial_strategy_from_context_review(
    review_id: UUID,
    command: CreateInitialStrategyFromContextReviewRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> InitialStrategyCreationResult:
    try:
        return PersistedInitialPlanningContextService(session).create_strategy(
            review_id, command, authority
        )
    except InitialPlanningContextNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InitialPlanningContextConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InitialPlanningContextValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/athletes/{athlete_id}/initial-strategies",
    tags=["operator"],
    response_model=InitialStrategyCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_initial_strategy(
    athlete_id: UUID,
    command: OperatorInitialStrategyRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> InitialStrategyCreationResult:
    try:
        return execute_operator_initial_strategy(session, athlete_id, command, authority)
    except InitialPlanningNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InitialPlanningConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except InitialPlanningValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/operator/strategies/{strategy_id}/resource-demand-preparation",
    tags=["operator"],
    response_model=ResourceDemandPreparationProjection,
)
def get_operator_resource_demand_preparation(
    strategy_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query(alias="at")] = None,
) -> ResourceDemandPreparationProjection:
    try:
        return ResourceDemandPreparationProjector(session).project(strategy_id, projected_at)
    except ResourceDemandPreparationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ResourceDemandPreparationProjectionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/strategies/{strategy_id}/priorities/{priority_id}/resource-demands",
    tags=["operator"],
    response_model=ResourceDemandPreparationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_resource_demand(
    strategy_id: UUID,
    priority_id: UUID,
    command: OperatorResourceDemandRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> ResourceDemandPreparationResult:
    try:
        return execute_operator_resource_preparation(
            session,
            strategy_id,
            priority_id,
            command,
            authority,
        )
    except ResourcePreparationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ResourcePreparationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ResourcePreparationValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/operator/strategies/{strategy_id}/block-preparation",
    tags=["operator"],
    response_model=BlockPreparationProjection,
)
def get_operator_block_preparation(
    strategy_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query(alias="at")] = None,
) -> BlockPreparationProjection:
    try:
        return BlockPreparationProjector(session).project(strategy_id, projected_at)
    except BlockPreparationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except BlockPreparationProjectionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/strategies/{strategy_id}/blocks",
    tags=["operator"],
    response_model=BlockPlanCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_block_plan(
    strategy_id: UUID,
    command: OperatorBlockPlanRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> BlockPlanCreationResult:
    try:
        return execute_operator_block_creation(session, strategy_id, command, authority)
    except BlockCreationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except BlockCreationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except BlockCreationValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/operator/blocks/{block_id}/first-week-preparation",
    tags=["operator"],
    response_model=FirstWeekPreparationProjection,
)
def get_operator_first_week_preparation(
    block_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query(alias="at")] = None,
) -> FirstWeekPreparationProjection:
    try:
        return FirstWeekPreparationProjector(session).project(block_id, projected_at)
    except FirstWeekPreparationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except FirstWeekPreparationProjectionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/blocks/{block_id}/first-week-plans",
    tags=["operator"],
    response_model=WeeklyPlanCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_first_week_plan(
    block_id: UUID,
    command: OperatorWeeklyPlanRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> WeeklyPlanCreationResult:
    try:
        return execute_operator_weekly_plan_creation(session, block_id, command, authority)
    except WeeklyPlanNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except WeeklyPlanConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except WeeklyPlanValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/operator/blocks/{block_id}/review-preparation",
    tags=["operator"],
    response_model=BlockReviewPreparationProjection,
)
def get_operator_block_review_preparation(
    block_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query(alias="at")] = None,
) -> BlockReviewPreparationProjection:
    try:
        return BlockReviewPreparationProjector(session).project(block_id, projected_at)
    except PostBlockPreparationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except PostBlockPreparationProjectionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/blocks/{block_id}/reviews",
    tags=["operator"],
    response_model=BlockReviewCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_block_review(
    block_id: UUID,
    command: OperatorBlockReviewRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> BlockReviewCreationResult:
    try:
        return execute_operator_block_review(session, block_id, command, authority)
    except BlockReviewNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except BlockReviewConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except BlockReviewValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/operator/block-reviews/{block_review_id}/replanning-preparation",
    tags=["operator"],
    response_model=ReplanningPreparationProjection,
)
def get_operator_replanning_preparation(
    block_review_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    _authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
    projected_at: Annotated[datetime | None, Query(alias="at")] = None,
) -> ReplanningPreparationProjection:
    try:
        return ReplanningPreparationProjector(session).project(block_review_id, projected_at)
    except PostBlockPreparationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except PostBlockPreparationProjectionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/block-reviews/{block_review_id}/replanning",
    tags=["operator"],
    response_model=PostBlockReplanningResult,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_replanning(
    block_review_id: UUID,
    command: OperatorReplanningRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> PostBlockReplanningResult:
    try:
        return execute_operator_replanning(session, block_review_id, command, authority)
    except ReplanningNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ReplanningConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ReplanningValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/stimulus-requirements/{stimulus_requirement_id}/exercise-reresolutions",
    tags=["operator"],
    response_model=ExerciseReResolutionResult,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_exercise_reresolution(
    stimulus_requirement_id: UUID,
    command: OperatorExerciseReResolutionRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> ExerciseReResolutionResult:
    try:
        return execute_operator_exercise_reresolution(
            session, stimulus_requirement_id, command, authority
        )
    except ExerciseReResolutionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ExerciseReResolutionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ExerciseReResolutionValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/operator/weekly-plans/{source_weekly_plan_id}/environment-prescription-revisions",
    tags=["operator"],
    response_model=EnvironmentPrescriptionRevisionResult,
    status_code=status.HTTP_201_CREATED,
)
def create_operator_environment_prescription_revision(
    source_weekly_plan_id: UUID,
    command: OperatorEnvironmentPrescriptionRevisionRequest,
    session: Annotated[Session, Depends(database_session_dependency)],
    authority: Annotated[AuthorizedRole, Depends(planning_reviewer_dependency)],
) -> EnvironmentPrescriptionRevisionResult:
    try:
        return execute_operator_environment_prescription_revision(
            session, source_weekly_plan_id, command, authority
        )
    except EnvironmentPrescriptionRevisionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except EnvironmentPrescriptionRevisionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except EnvironmentPrescriptionRevisionValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get("/ready", tags=["system"])
def ready() -> dict[str, str]:
    with _session_scope() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get(
    "/v1/onboarding/equipment",
    tags=["onboarding"],
    response_model=tuple[OnboardingEquipmentOption, ...],
)
def get_onboarding_equipment(
    session: Annotated[Session, Depends(database_session_dependency)],
) -> tuple[OnboardingEquipmentOption, ...]:
    return list_onboarding_equipment(session)


@app.get(
    "/v1/assessments/catalog",
    tags=["assessment"],
    response_model=tuple[ReviewedAssessmentCatalogItem, ...],
)
def get_reviewed_assessment_catalog(
    session: Annotated[Session, Depends(database_session_dependency)],
) -> tuple[ReviewedAssessmentCatalogItem, ...]:
    return list_reviewed_assessment_catalog(session)


@app.get(
    "/v1/athletes/{athlete_id}/dashboard",
    tags=["athlete"],
    response_model=AthleticDashboardProjection,
)
def get_athletic_dashboard(
    athlete_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
    at: Annotated[datetime | None, Query()] = None,
) -> AthleticDashboardProjection:
    authorizer.require_athlete(athlete_id)
    try:
        return get_athletic_dashboard_projection(session, athlete_id, at)
    except AthleticDashboardNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/athletes/{athlete_id}/environments",
    tags=["athlete"],
    response_model=AthleteEnvironmentProjection,
)
def get_athlete_environments(
    athlete_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
    at: Annotated[datetime | None, Query()] = None,
) -> AthleteEnvironmentProjection:
    authorizer.require_athlete(athlete_id)
    try:
        return get_athlete_environment_projection(session, athlete_id, at)
    except EnvironmentManagementNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (EnvironmentManagementValidationError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/athletes/{athlete_id}/environments/{environment_id}/equipment-reports",
    tags=["athlete"],
    response_model=EquipmentStateReportResult,
    status_code=status.HTTP_201_CREATED,
)
def record_equipment_state(
    athlete_id: UUID,
    environment_id: UUID,
    command: RecordEquipmentStateCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> EquipmentStateReportResult:
    authorizer.require_athlete(athlete_id)
    try:
        return PersistedEquipmentStateService(session).execute(athlete_id, environment_id, command)
    except EnvironmentManagementNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except EnvironmentManagementConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except EnvironmentManagementValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/athletes/{athlete_id}/assessment-workflow",
    tags=["assessment"],
    response_model=AssessmentWorkflowProjection,
)
def get_assessment_workflow(
    athlete_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
    at: Annotated[datetime | None, Query()] = None,
) -> AssessmentWorkflowProjection:
    authorizer.require_athlete(athlete_id)
    try:
        return get_assessment_workflow_projection(session, athlete_id, at)
    except AssessmentWorkflowNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/athletes/{athlete_id}/assessment-runs",
    tags=["assessment"],
    response_model=AssessmentSelectionRunResult,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment_selection_run(
    athlete_id: UUID,
    command: CreateAssessmentSelectionRunCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> AssessmentSelectionRunResult:
    authorizer.require_athlete(athlete_id)
    try:
        return PersistedAssessmentSelectionRunService(session).execute(athlete_id, command)
    except AssessmentSelectionRunNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AssessmentSelectionRunConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except AssessmentSelectionRunValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/athletes/{athlete_id}/assessment-runs/{run_id}/selections/{selection_id}/result",
    tags=["assessment"],
    response_model=AssessmentPerformanceResult,
    status_code=status.HTTP_201_CREATED,
)
def record_assessment_performance(
    athlete_id: UUID,
    run_id: UUID,
    selection_id: UUID,
    command: RecordAssessmentPerformanceCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> AssessmentPerformanceResult:
    authorizer.require_athlete(athlete_id)
    try:
        return PersistedAssessmentPerformanceService(session).execute(
            athlete_id, run_id, selection_id, command
        )
    except AssessmentPerformanceNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AssessmentPerformanceConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except AssessmentPerformanceValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/athletes/{athlete_id}/assessment-performances/{performance_id}/capability-estimate",
    tags=["assessment"],
    response_model=AssessmentCapabilityEstimateResult,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment_capability_estimate(
    athlete_id: UUID,
    performance_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> AssessmentCapabilityEstimateResult:
    authorizer.require_athlete(athlete_id)
    try:
        return PersistedAssessmentCapabilityEstimationService(session).execute(
            athlete_id, performance_id
        )
    except AssessmentCapabilityEstimationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AssessmentCapabilityEstimationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except AssessmentCapabilityEstimationValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/onboarding/athletes",
    tags=["onboarding"],
    response_model=AthleteOnboardingResult,
    status_code=status.HTTP_201_CREATED,
)
def create_athlete_onboarding(
    command: CreateAthleteOnboardingCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    principal: Annotated[AuthenticatedPrincipal, Depends(authenticated_principal_dependency)],
) -> AthleteOnboardingResult:
    try:
        return PersistedAthleteOnboardingService(session).execute(command, principal)
    except AthleteOnboardingNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AthleteOnboardingConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except AthleteOnboardingValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/athletes/{athlete_id}/planning-status",
    tags=["planning"],
    response_model=PlanningStatusProjection,
)
def get_planning_status(
    athlete_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
    at: Annotated[datetime | None, Query()] = None,
) -> PlanningStatusProjection:
    authorizer.require_athlete(athlete_id)
    try:
        return get_planning_status_projection(session, athlete_id, at)
    except PlanningStatusNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.get(
    "/v1/athletes/{athlete_id}/current-week",
    tags=["daily-use"],
    response_model=CurrentWeekProjection,
)
def get_current_week(
    athlete_id: UUID,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
    on: Annotated[date, Query(description="Date that must fall within the requested week")],
) -> CurrentWeekProjection:
    authorizer.require_athlete(athlete_id)
    try:
        return CurrentWeekProjector(session).project(athlete_id, on)
    except CurrentWeekNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except CurrentWeekConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.post(
    "/v1/weekly-plans/{weekly_plan_id}/availability-confirmations",
    tags=["planning"],
    response_model=WeeklyAvailabilityConfirmationResult,
    status_code=status.HTTP_201_CREATED,
)
def confirm_next_week_availability(
    weekly_plan_id: UUID,
    command: ConfirmWeeklyAvailabilityCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> WeeklyAvailabilityConfirmationResult:
    authorizer.require_weekly_plan(weekly_plan_id)
    try:
        return PersistedWeeklyAvailabilityConfirmationService(session).execute(
            weekly_plan_id, command
        )
    except WeeklyAvailabilityConfirmationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except WeeklyAvailabilityConfirmationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except WeeklyAvailabilityConfirmationValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/weekly-plans/{weekly_plan_id}/roll-forward",
    tags=["planning"],
    response_model=WeeklyPlanRollForwardResult,
    status_code=status.HTTP_201_CREATED,
)
def roll_forward_weekly_plan(
    weekly_plan_id: UUID,
    command: RollForwardWeeklyPlanCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> WeeklyPlanRollForwardResult:
    authorizer.require_weekly_plan(weekly_plan_id)
    try:
        return PersistedWeeklyPlanRollForwardService(session).execute(weekly_plan_id, command)
    except WeeklyPlanRollForwardNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except WeeklyPlanRollForwardConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except WeeklyPlanRollForwardValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/weekly-plans/{weekly_plan_id}/sessions/{planned_session_id}/safety-checks",
    tags=["execution"],
    response_model=SessionSafetyCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_session_safety_decision(
    weekly_plan_id: UUID,
    planned_session_id: UUID,
    command: CreateSessionSafetyDecisionCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> SessionSafetyCreationResult:
    authorizer.require_weekly_plan(weekly_plan_id)
    try:
        return PersistedSessionSafetyService(session).execute(
            weekly_plan_id, planned_session_id, command
        )
    except SessionRecordingNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except SessionRecordingConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except SessionRecordingValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/weekly-plans/{weekly_plan_id}/sessions/{planned_session_id}/executions",
    tags=["execution"],
    response_model=SessionExecutionCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_session_execution(
    weekly_plan_id: UUID,
    planned_session_id: UUID,
    command: CreateSessionExecutionCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> SessionExecutionCreationResult:
    authorizer.require_weekly_plan(weekly_plan_id)
    try:
        return PersistedSessionExecutionService(session).execute(
            weekly_plan_id, planned_session_id, command
        )
    except SessionRecordingNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except SessionRecordingConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except SessionRecordingValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/session-executions/{session_execution_id}/prescriptions/{prescription_id}/progression",
    tags=["progression"],
    response_model=ProgressionCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_progression_decision(
    session_execution_id: UUID,
    prescription_id: UUID,
    command: AutomaticProgressionDecisionCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> ProgressionCreationResult:
    authorizer.require_session_execution(session_execution_id)
    try:
        return PersistedProgressionService(session).execute_automatic(
            session_execution_id, prescription_id, command
        )
    except ProgressionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ProgressionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ProgressionValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
