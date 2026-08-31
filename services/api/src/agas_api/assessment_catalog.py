from agas_domain import AssessmentDefinition, AssessmentDefinitionReview
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session


class ReviewedAssessmentCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    definition: AssessmentDefinition
    current_review: AssessmentDefinitionReview


def list_reviewed_assessment_catalog(
    session: Session,
) -> tuple[ReviewedAssessmentCatalogItem, ...]:
    repository = DomainRepository(session)
    return tuple(
        ReviewedAssessmentCatalogItem(definition=definition, current_review=review)
        for definition, review in list_evidence_ready_assessment_definitions(repository)
    )


def list_evidence_ready_assessment_definitions(
    repository: DomainRepository,
) -> tuple[tuple[AssessmentDefinition, AssessmentDefinitionReview], ...]:
    """Return current approvals that had ready evidence at their decision time."""

    return tuple(
        (definition, review)
        for definition, review in repository.list_approved_assessment_definitions()
        if repository.evidence_authority_is_ready(
            review.evidence_claim_ids,
            review.reviewed_at,
        )
    )
