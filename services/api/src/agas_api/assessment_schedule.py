from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from agas_domain import AssessmentDefinition, AssessmentDefinitionReview
from agas_domain.persistence.repository import DomainRepository
from agas_planner import AssessmentReassessmentSchedule, AssessmentReassessmentScheduler


def resolve_assessment_reassessment_schedule(
    repository: DomainRepository,
    athlete_id: UUID,
    reviewed_definitions: Iterable[tuple[AssessmentDefinition, AssessmentDefinitionReview]],
    evaluated_at: datetime,
) -> AssessmentReassessmentSchedule:
    definitions = tuple(reviewed_definitions)
    performances = repository.list_assessment_performances(athlete_id)
    review_ids = tuple(dict.fromkeys(item.assessment_definition_review_id for item in performances))
    performance_reviews = {
        review_id: review
        for review_id in review_ids
        if (review := repository.get_assessment_definition_review(review_id)) is not None
    }
    return AssessmentReassessmentScheduler().schedule(
        definitions,
        performances,
        performance_reviews,
        evaluated_at,
    )
