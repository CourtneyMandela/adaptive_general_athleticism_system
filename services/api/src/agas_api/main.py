from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from agas_domain import BlockPlan, ClosedLoopReplanningResult
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
from agas_api.block_creation import (
    BlockCreationConflictError,
    BlockCreationNotFoundError,
    BlockCreationValidationError,
    CreateBlockPlanCommand,
    PersistedBlockCreationService,
)
from agas_api.block_review_application import (
    BlockReviewConflictError,
    BlockReviewCreationResult,
    BlockReviewNotFoundError,
    BlockReviewValidationError,
    CreateBlockReviewCommand,
    PersistedBlockReviewService,
)
from agas_api.current_week import (
    CurrentWeekConflictError,
    CurrentWeekNotFoundError,
    CurrentWeekProjection,
    CurrentWeekProjector,
)
from agas_api.database import database_session, database_session_dependency
from agas_api.identity import (
    AuthenticatedPrincipal,
    OwnershipAuthorizer,
    authenticated_principal_dependency,
    ownership_authorizer_dependency,
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
from agas_api.progression_application import (
    CreateProgressionDecisionCommand,
    PersistedProgressionService,
    ProgressionConflictError,
    ProgressionCreationResult,
    ProgressionNotFoundError,
    ProgressionValidationError,
)
from agas_api.replanning import (
    PersistedReplanningService,
    PostBlockReplanningCommand,
    ReplanningConflictError,
    ReplanningNotFoundError,
    ReplanningValidationError,
)
from agas_api.resource_preparation import (
    PersistedResourcePreparationService,
    ResourceDemandPreparationCommand,
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
from agas_api.weekly_planning import (
    CreateWeeklyPlanCommand,
    PersistedWeeklyPlanService,
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
    "/v1/blocks/{block_id}/reviews",
    tags=["planning"],
    response_model=BlockReviewCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_block_review(
    block_id: UUID,
    command: CreateBlockReviewCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> BlockReviewCreationResult:
    authorizer.require_block(block_id)
    try:
        return PersistedBlockReviewService(session).execute(block_id, command)
    except BlockReviewNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except BlockReviewConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except BlockReviewValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/block-reviews/{block_review_id}/replan",
    tags=["planning"],
    response_model=ClosedLoopReplanningResult,
    status_code=status.HTTP_201_CREATED,
)
def replan_after_block_review(
    block_review_id: UUID,
    command: PostBlockReplanningCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> ClosedLoopReplanningResult:
    authorizer.require_block_review(block_review_id)
    try:
        return PersistedReplanningService(session).execute(block_review_id, command)
    except ReplanningNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ReplanningConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ReplanningValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/strategies/{strategy_id}/blocks",
    tags=["planning"],
    response_model=BlockPlan,
    status_code=status.HTTP_201_CREATED,
)
def create_block_plan(
    strategy_id: UUID,
    command: CreateBlockPlanCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> BlockPlan:
    authorizer.require_strategy(strategy_id)
    try:
        return PersistedBlockCreationService(session).execute(strategy_id, command)
    except BlockCreationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except BlockCreationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except BlockCreationValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/strategies/{strategy_id}/priorities/{priority_id}/resource-demands",
    tags=["planning"],
    response_model=ResourceDemandPreparationResult,
    status_code=status.HTTP_201_CREATED,
)
def prepare_resource_demand(
    strategy_id: UUID,
    priority_id: UUID,
    command: ResourceDemandPreparationCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> ResourceDemandPreparationResult:
    authorizer.require_strategy(strategy_id)
    try:
        return PersistedResourcePreparationService(session).execute(
            strategy_id, priority_id, command
        )
    except ResourcePreparationNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ResourcePreparationConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ResourcePreparationValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error


@app.post(
    "/v1/blocks/{block_id}/weekly-plans",
    tags=["planning"],
    response_model=WeeklyPlanCreationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_weekly_plan(
    block_id: UUID,
    command: CreateWeeklyPlanCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> WeeklyPlanCreationResult:
    authorizer.require_block(block_id)
    try:
        return PersistedWeeklyPlanService(session).execute(block_id, command)
    except WeeklyPlanNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except WeeklyPlanConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except WeeklyPlanValidationError as error:
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
    command: CreateProgressionDecisionCommand,
    session: Annotated[Session, Depends(database_session_dependency)],
    authorizer: Annotated[OwnershipAuthorizer, Depends(ownership_authorizer_dependency)],
) -> ProgressionCreationResult:
    authorizer.require_session_execution(session_execution_id)
    try:
        return PersistedProgressionService(session).execute(
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
