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
    return tuple(
        ReviewedAssessmentCatalogItem(definition=definition, current_review=review)
        for definition, review in DomainRepository(session).list_approved_assessment_definitions()
    )
