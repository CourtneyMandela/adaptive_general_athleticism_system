# ruff: noqa: E501 -- reviewed evidence and protocol prose stays readable as exact sentences.
from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Annotated, Literal
from uuid import UUID

from agas_domain import (
    Applicability,
    AssessmentDefinition,
    AssessmentIntensity,
    AssessmentMeasurementSchema,
    AssessmentMeasurementType,
    CapabilityDomain,
    DecisionRecord,
    Equipment,
    EvidenceClaim,
    EvidenceSource,
    EvidenceSourceIdentifier,
    EvidenceStrength,
)
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from agas_api.assessment_governance import AssessmentGovernanceProjector
from agas_api.assessment_governance_release import (
    RELEASE_VERSION,
    AssessmentDefinitionReviewDraft,
    AssessmentGovernanceReleaseConflictError,
    AssessmentGovernanceReleaseRequest,
    AssessmentGovernanceReleaseResult,
    CapabilityEstimationPolicyDraft,
    EvidenceClaimReviewDraft,
    ratify_assessment_governance_release,
)
from agas_api.identity import AuthorizedRole

CANDIDATE_VERSION = "assessment-governance-candidate@1.0.0"
NonEmptyText = Annotated[str, Field(min_length=1)]


class AssessmentCandidateEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: NonEmptyText
    source_url: NonEmptyText
    population: NonEmptyText
    finding: NonEmptyText
    limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    conflict_disclosure: NonEmptyText


class AssessmentGovernanceCandidate(BaseModel):
    """An immutable, human-readable presentation of prepared scientific content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["assessment-governance-candidate@1.0.0"]
    candidate_id: UUID
    slug: NonEmptyText
    release_label: NonEmptyText
    prepared_at: datetime
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    summary: NonEmptyText
    measures: NonEmptyText
    does_not_measure: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    capability_domain: CapabilityDomain
    estimate_scope: NonEmptyText
    setup_requirements: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    protocol_steps: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    stop_conditions: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    operational_choices: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    unresolved_limitations: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    evidence: Annotated[tuple[AssessmentCandidateEvidenceSummary, ...], Field(min_length=1)]


class AssessmentGovernanceCandidateItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate: AssessmentGovernanceCandidate
    status: Literal["available", "ratified", "conflict"]
    ratified_at: datetime | None = None
    issues: tuple[str, ...] = ()


class AssessmentGovernanceCandidateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projected_at: datetime
    items: tuple[AssessmentGovernanceCandidateItem, ...]
    projection_version: str = "assessment-governance-candidates@1.0.0"


class RatifyAssessmentGovernanceCandidateCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_version: Literal["assessment-governance-candidate@1.0.0"]
    content_digest: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    approval_attestation: Literal[True]


class PreparedAssessmentGovernanceRelease(BaseModel):
    """Exact static release content; authority and ratification time are added by the server."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: UUID
    release_label: NonEmptyText
    prepared_at: datetime
    sources: Annotated[tuple[EvidenceSource, ...], Field(min_length=1)]
    supporting_equipment: tuple[Equipment, ...] = ()
    claims: Annotated[tuple[EvidenceClaim, ...], Field(min_length=1)]
    evidence_reviews: Annotated[tuple[EvidenceClaimReviewDraft, ...], Field(min_length=1)]
    definition: AssessmentDefinition
    protocol_review: AssessmentDefinitionReviewDraft
    estimation_policy: CapabilityEstimationPolicyDraft
    release_rationale: NonEmptyText
    release_uncertainty: NonEmptyText

    def release_request(
        self,
        *,
        candidate_content_digest: str,
        ratified_at: datetime,
    ) -> AssessmentGovernanceReleaseRequest:
        return AssessmentGovernanceReleaseRequest(
            release_version=RELEASE_VERSION,
            candidate_content_digest=candidate_content_digest,
            ratified_at=ratified_at,
            approval_attestation=True,
            **self.model_dump(),
        )


class PreparedAssessmentGovernanceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    presentation: AssessmentGovernanceCandidate
    release: PreparedAssessmentGovernanceRelease


def list_assessment_governance_candidates(
    session: Session,
    *,
    projected_at: datetime | None = None,
) -> AssessmentGovernanceCandidateProjection:
    instant = projected_at or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("candidate projection time must include a timezone")
    repository = DomainRepository(session)
    items: list[AssessmentGovernanceCandidateItem] = []
    for prepared in _candidate_registry().values():
        decision = repository.get_decision_record(prepared.release.release_id)
        if decision is None:
            status: Literal["available", "ratified", "conflict"] = "available"
            issues: tuple[str, ...] = ()
            ratified_at = None
        elif (
            f"candidate_content_digest:{prepared.presentation.content_digest}" in decision.evidence
        ):
            status = "ratified"
            issues = ()
            ratified_at = decision.created_at
        else:
            status = "conflict"
            issues = (
                "The candidate release identity is already occupied by different immutable content.",
            )
            ratified_at = decision.created_at
        items.append(
            AssessmentGovernanceCandidateItem(
                candidate=prepared.presentation,
                status=status,
                ratified_at=ratified_at,
                issues=issues,
            )
        )
    return AssessmentGovernanceCandidateProjection(
        projected_at=instant,
        items=tuple(sorted(items, key=lambda item: item.candidate.slug)),
    )


def ratify_assessment_governance_candidate(
    session: Session,
    candidate_id: UUID,
    command: RatifyAssessmentGovernanceCandidateCommand,
    authority: AuthorizedRole,
    *,
    ratified_at: datetime | None = None,
) -> AssessmentGovernanceReleaseResult:
    try:
        prepared = _candidate_registry()[candidate_id]
    except KeyError as error:
        raise KeyError("assessment-governance candidate does not exist") from error
    if command.candidate_version != prepared.presentation.candidate_version:
        raise ValueError("candidate version does not match the prepared release")
    if command.content_digest != prepared.presentation.content_digest:
        raise AssessmentGovernanceReleaseConflictError(
            "candidate content changed; refresh and review the exact current release"
        )

    repository = DomainRepository(session)
    existing_decision = repository.get_decision_record(prepared.release.release_id)
    if existing_decision is not None:
        return _existing_candidate_result(
            session,
            prepared,
            existing_decision,
        )

    instant = ratified_at or datetime.now(UTC)
    return ratify_assessment_governance_release(
        session,
        prepared.release.release_request(
            candidate_content_digest=prepared.presentation.content_digest,
            ratified_at=instant,
        ),
        authority,
        recorded_at=instant,
    )


def _existing_candidate_result(
    session: Session,
    prepared: PreparedAssessmentGovernanceCandidate,
    decision: DecisionRecord,
) -> AssessmentGovernanceReleaseResult:
    values = {
        key: value
        for item in decision.evidence
        if ":" in item
        for key, value in (item.split(":", 1),)
    }
    if values.get("candidate_content_digest") != prepared.presentation.content_digest:
        raise AssessmentGovernanceReleaseConflictError(
            "candidate release identity is occupied by different immutable content"
        )
    try:
        content_digest = values["content_digest"]
        authority_account_id = UUID(values["authority_account_id"])
        authority_assignment_id = UUID(values["authority_assignment_id"])
    except (KeyError, ValueError) as error:
        raise AssessmentGovernanceReleaseConflictError(
            "persisted candidate decision has incomplete authority provenance"
        ) from error
    assessment = next(
        (
            item
            for item in AssessmentGovernanceProjector(session).project(decision.created_at).items
            if item.definition.id == prepared.release.definition.id
        ),
        None,
    )
    if assessment is None or assessment.readiness != "ready":
        raise AssessmentGovernanceReleaseConflictError(
            "persisted candidate decision no longer resolves to a ready assessment chain"
        )
    return AssessmentGovernanceReleaseResult(
        release_id=prepared.release.release_id,
        release_version=RELEASE_VERSION,
        content_digest=content_digest,
        authority_account_id=authority_account_id,
        authority_assignment_id=authority_assignment_id,
        created_source_ids=(),
        created_claim_ids=(),
        created_evidence_review_ids=(),
        definition_created=False,
        protocol_review_created=False,
        estimation_policy_created=False,
        decision_record_created=False,
        assessment=assessment,
    )


@lru_cache
def _candidate_registry() -> dict[UUID, PreparedAssessmentGovernanceCandidate]:
    candidates: dict[UUID, PreparedAssessmentGovernanceCandidate] = {}
    for prepared, presentation_fields in (
        (_chair_stand_release(), _chair_stand_presentation_fields()),
        (_standard_pushup_release(), _standard_pushup_presentation_fields()),
    ):
        content_digest = _candidate_digest(prepared, presentation_fields)
        presentation = AssessmentGovernanceCandidate(
            candidate_version=CANDIDATE_VERSION,
            content_digest=content_digest,
            **presentation_fields,
        )
        candidate = PreparedAssessmentGovernanceCandidate(
            presentation=presentation,
            release=prepared,
        )
        if presentation.candidate_id in candidates:
            raise ValueError("assessment candidate ids must be unique")
        candidates[presentation.candidate_id] = candidate
    return candidates


def _candidate_digest(
    release: PreparedAssessmentGovernanceRelease,
    presentation_fields: dict[str, object],
) -> str:
    canonical = json.dumps(
        {
            "candidate_version": CANDIDATE_VERSION,
            "presentation": presentation_fields,
            "release": release.model_dump(mode="json"),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _chair_stand_release() -> PreparedAssessmentGovernanceRelease:
    source_created_at = datetime(2026, 9, 8, 10, 20, tzinfo=UTC)
    claim_created_at = datetime(2026, 9, 8, 10, 30, tzinfo=UTC)
    definition_created_at = datetime(2026, 9, 8, 10, 35, tzinfo=UTC)
    prepared_at = datetime(2026, 9, 8, 10, 45, tzinfo=UTC)

    young_adult_pmid = EvidenceSourceIdentifier(scheme="pmid", value="35949374")
    young_adult_doi = EvidenceSourceIdentifier(scheme="doi", value="10.26603/001c.36432")
    young_adult_pmcid = EvidenceSourceIdentifier(scheme="other", value="pmcid:PMC9340829")
    self_admin_pmid = EvidenceSourceIdentifier(scheme="pmid", value="40330808")
    self_admin_doi = EvidenceSourceIdentifier(scheme="doi", value="10.1016/j.ocarto.2025.100613")
    self_admin_pmcid = EvidenceSourceIdentifier(scheme="other", value="pmcid:PMC12053707")
    young_adult_source = EvidenceSource(
        id=UUID("90000000-0000-4000-8000-000000000001"),
        created_at=source_created_at,
        title="Normative Reference Values and Validity for the 30-Second Chair-Stand Test in Healthy Young Adults",
        authors=("Donald H Lein Jr", "Mansour Alotaibi", "Marzouq Almutairi", "Harshvardhan Singh"),
        journal="International Journal of Sports Physical Therapy",
        publication_year=2022,
        publication_date=date(2022, 8, 1),
        publication_types=("Cross-sectional study", "Journal article"),
        primary_identifier=young_adult_pmid,
        source_identifiers=(young_adult_pmid, young_adult_doi, young_adult_pmcid),
        metadata_provider="pubmed",
        retrieval_uri="https://pubmed.ncbi.nlm.nih.gov/35949374/",
        retrieval_query="PMID 35949374",
        retrieved_at=source_created_at,
        metadata_version="pubmed-record-snapshot@2026-09-08",
        provenance_notes=(
            "Metadata and numerical results were checked against the PubMed record.",
            "The abstract is intentionally not copied into the stored snapshot.",
        ),
    )
    self_admin_source = EvidenceSource(
        id=UUID("90000000-0000-4000-8000-000000000002"),
        created_at=source_created_at,
        title="Reliability of digitally instructed self-reported 30-second chair stand test for lower extremity function",
        authors=(
            "Leif E Dahlberg",
            "Oscar Karlsson",
            "Paulina Sirard",
            "L Stefan Lohmander",
            "Ali Kiadaliri",
        ),
        journal="Osteoarthritis and Cartilage Open",
        publication_year=2025,
        publication_date=date(2025, 4, 9),
        publication_types=("Reliability study", "Journal article"),
        primary_identifier=self_admin_pmid,
        source_identifiers=(self_admin_pmid, self_admin_doi, self_admin_pmcid),
        metadata_provider="pubmed",
        retrieval_uri="https://pubmed.ncbi.nlm.nih.gov/40330808/",
        retrieval_query="PMID 40330808",
        retrieved_at=source_created_at,
        metadata_version="pubmed-record-snapshot@2026-09-08",
        provenance_notes=(
            "Metadata, reliability estimates, mean self-report difference, and conflicts were checked against the PubMed record.",
            "The abstract is intentionally not copied into the stored snapshot.",
        ),
    )

    young_adult_claim = EvidenceClaim(
        id=UUID("91000000-0000-4000-8000-000000000001"),
        created_at=claim_created_at,
        claim=(
            "In 81 healthy adults aged 19 to 35, 30-second chair-stand repetition count was associated with five-times sit-to-stand time (r=-0.79) and lateral step-up performance (r=0.51)."
        ),
        domain="assessment_validity",
        population="81 healthy adults aged 19 to 35 years; mean age 25.1 years; 47 female.",
        intervention="Two trials of the investigator-administered 30-second chair-stand test.",
        comparator="Five-times sit-to-stand, lateral step-up, and physical-activity grouping.",
        outcome="Chair-stand repetition count and concurrent, convergent, and discriminative validity results.",
        study_design="Cross-sectional validity study",
        sample_size=81,
        effect_direction="More repetitions aligned with better comparator-test performance.",
        uncertainty=(
            "A single cross-sectional convenience sample supports an assessment-specific functional-performance interpretation, not causal, normative, or sport-performance conclusions."
        ),
        limitations=(
            "The protocol was investigator-administered and included two trials.",
            "The study did not establish prediction of sport performance or training outcomes.",
            "Reference values should not be generalized beyond the sampled population.",
        ),
        evidence_strength=EvidenceStrength.LOW,
        athlete_applicability=Applicability.LOW,
        applicability_notes=(
            "Useful as indirect support that the count contains lower-extremity functional-performance information; no population match is assumed for the current athlete."
        ),
        source_identifiers=(young_adult_pmid, young_adult_doi, young_adult_pmcid),
        source_record_ids=(young_adult_source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="chair-stand-young-adult-validity@1.0.0",
    )
    self_admin_claim = EvidenceClaim(
        id=UUID("91000000-0000-4000-8000-000000000002"),
        created_at=claim_created_at,
        claim=(
            "Digitally instructed self-reported 30-second chair-stand counts showed test-retest ICC 0.88 (95% CI 0.79 to 0.93) in 54 older adults with hip or knee osteoarthritis and averaged 1.5 repetitions higher than in-person physiotherapist counts in a separate 18-person comparison."
        ),
        domain="assessment_self_administration_reliability",
        population="Adults with hip or knee osteoarthritis; mean age 69 in the test-retest sample and 67 in the inter-rater sample.",
        intervention="Digitally instructed, self-administered, self-reported 30-second chair-stand test at home.",
        comparator="Repeat digital self-assessment and in-person physiotherapist assessment.",
        outcome="Test-retest and inter-rater reliability plus mean self-report difference.",
        study_design="Reliability and agreement study",
        sample_size=54,
        duration="Test-retest interval 10 to 14 days.",
        effect_direction="Repeat self-reports were reasonably consistent, with evidence of modest overcounting relative to physiotherapist assessment.",
        uncertainty=(
            "The samples were small, older, predominantly female, and affected by osteoarthritis; inter-rater precision was wide and transfer to a healthy individual is uncertain."
        ),
        limitations=(
            "Inter-rater comparison included only 18 participants and one physiotherapist.",
            "The inter-rater ICC 95% confidence interval was wide (0.47 to 0.96).",
            "Participants were already familiar with the digital treatment context.",
            "Self-reported counts averaged 1.5 repetitions above in-person counts.",
        ),
        evidence_strength=EvidenceStrength.LOW,
        athlete_applicability=Applicability.LOW,
        applicability_notes=(
            "Directly supports feasibility of digital self-administration, but does not establish equivalent accuracy or reliability for a younger healthy athlete."
        ),
        source_identifiers=(self_admin_pmid, self_admin_doi, self_admin_pmcid),
        source_record_ids=(self_admin_source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="chair-stand-digital-self-administration@1.0.0",
    )
    definition = AssessmentDefinition(
        id=UUID("92000000-0000-4000-8000-000000000001"),
        created_at=definition_created_at,
        slug="thirty_second_chair_stand",
        name="30-second chair stand",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
        observation_type="thirty_second_chair_stand_repetitions",
        intensity=AssessmentIntensity.MODERATE,
        unit_or_scale="repetitions",
        protocol_version="agas-thirty-second-chair-stand@1.0.0",
        required_equipment_categories=("chair",),
        blocked_by_health_screening_flags=(
            "lower_body_or_balance_concern",
            "chair_stand_control_not_confirmed",
        ),
    )
    chair = Equipment(
        id=UUID("97000000-0000-4000-8000-000000000001"),
        created_at=definition_created_at,
        name="Stable armless chair (43-45 cm seat)",
        category="chair",
        capabilities={
            "stable": True,
            "armless": True,
            "straight_back": True,
            "firm_seat": True,
            "seat_height_cm_min": 43,
            "seat_height_cm_max": 45,
        },
    )
    review_id = UUID("93000000-0000-4000-8000-000000000001")
    return PreparedAssessmentGovernanceRelease(
        release_id=UUID("94000000-0000-4000-8000-000000000001"),
        release_label="30-second chair stand owner-alpha release",
        prepared_at=prepared_at,
        sources=(young_adult_source, self_admin_source),
        supporting_equipment=(chair,),
        claims=(young_adult_claim, self_admin_claim),
        evidence_reviews=(
            EvidenceClaimReviewDraft(
                id=UUID("95000000-0000-4000-8000-000000000001"),
                evidence_claim_id=young_adult_claim.id,
                sequence_number=1,
                source_verification_rationale=(
                    "The title, authors, identifiers, sample, correlations, activity-group difference, conclusion, future-research statement, and conflict statement were checked against PMID 35949374."
                ),
                extraction_rationale=(
                    "The claim retains the sample and reported correlations while excluding normative thresholds and stronger causal or predictive interpretations."
                ),
                evidence_strength_rationale=(
                    "Low reflects one cross-sectional study rather than replicated validation across athlete populations."
                ),
                applicability_rationale=(
                    "Low applicability avoids assuming the current athlete matches the sampled age, health, or administration context."
                ),
                uncertainty=(
                    "The test count is retained only as assessment-specific functional-performance information."
                ),
                conflict_disclosure="The PubMed record reports that the authors declared no conflicts of interest.",
                review_version="chair-stand-evidence-review@1.0.0",
            ),
            EvidenceClaimReviewDraft(
                id=UUID("95000000-0000-4000-8000-000000000002"),
                evidence_claim_id=self_admin_claim.id,
                sequence_number=1,
                source_verification_rationale=(
                    "The title, authors, identifiers, samples, ICC estimates, mean self-report difference, and conflict statement were checked against PMID 40330808."
                ),
                extraction_rationale=(
                    "The claim preserves the population mismatch, wide interval, and self-report bias instead of reducing the finding to 'validated for home use'."
                ),
                evidence_strength_rationale=(
                    "Low reflects small, selected samples and uncertain transfer beyond older adults with osteoarthritis."
                ),
                applicability_rationale=(
                    "Low recognizes direct digital self-administration evidence but no demonstrated population match to the current athlete."
                ),
                uncertainty=(
                    "Self-administered counts may be systematically higher and should be compared only with the same protocol."
                ),
                conflict_disclosure=(
                    "The PubMed record reports several authors as Joint Academy employees, advisors, or founders and one additional advisory/DSMB role."
                ),
                review_version="chair-stand-evidence-review@1.0.0",
            ),
        ),
        definition=definition,
        protocol_review=AssessmentDefinitionReviewDraft(
            id=review_id,
            assessment_definition_id=definition.id,
            sequence_number=1,
            protocol_instructions=(
                "Use a sturdy, straight-backed, armless chair with a firm seat about 43 to 45 cm (17 inches) high; place it against a wall on a nonslip floor and clear the surrounding area.",
                "Use the same chair, footwear, and surface on future attempts. Place the timer where it can be started without rushing and where the signal can be heard.",
                "Sit in the middle of the seat with back straight, feet flat and about hip-width apart, one foot slightly ahead if needed for balance, and arms crossed at the wrists against the chest.",
                "Before the recorded attempt, perform a comfortable 10-second familiarization, then sit and rest for at least 60 seconds.",
                "Start the 30-second timer. Rise to a fully upright standing position and return to a fully seated position as many times as possible without using the arms.",
                "Count each completed stand-and-sit cycle. If the timer ends after the final rise has passed halfway to full standing, count that final repetition.",
                "Stop immediately if an arm must be used, balance is lost, technique becomes uncontrolled, or any stop condition occurs; record the attempt as stopped rather than estimating a count.",
            ),
            result_entry_instructions=(
                "Enter the whole-number repetition count you directly observed. Do not convert it to a percentile, fitness rating, or strength score. If the attempt was stopped or the setup changed, do not enter a completed result."
            ),
            measurement_schema=AssessmentMeasurementSchema(
                measurement_type=AssessmentMeasurementType.INTEGER,
                label="Completed chair-stand repetitions in 30 seconds",
                minimum=0,
                step=1,
                measurement_schema_version="thirty-second-chair-stand-count@1.0.0",
            ),
            recommended_reassessment_days=28,
            self_administered=True,
            evidence_claim_ids=(young_adult_claim.id, self_admin_claim.id),
            applicability_notes=(
                "Owner-alpha use is limited to repeat measurement of the same individual's assessment-specific sit-to-stand performance after separate eligibility review and with a matching chair setup."
            ),
            uncertainty=(
                "The AGAS one-recorded-trial protocol is a conservative operational adaptation, not an exact reproduction of either study. Digital self-report may overcount; population transfer, learning effects, and day-to-day variability remain unresolved."
            ),
            review_version="agas-thirty-second-chair-stand-review@1.0.0",
        ),
        estimation_policy=CapabilityEstimationPolicyDraft(
            id=UUID("96000000-0000-4000-8000-000000000001"),
            assessment_definition_id=definition.id,
            assessment_definition_review_id=review_id,
            sequence_number=1,
            domain=definition.domain,
            observation_type=definition.observation_type,
            unit_or_scale=definition.unit_or_scale,
            calculation_method="latest-matching-observation",
            valid_for_days=28,
            multi_observation_window_days=28,
            evidence_claim_ids=(young_adult_claim.id, self_admin_claim.id),
            applicability_notes=(
                "Preserve the direct repetition count as a low-confidence, assessment-specific muscular-endurance estimate for within-person tracking only."
            ),
            uncertainty=(
                "No normative conversion, universal score, maximum-strength inference, or exercise prescription is authorized. A single result remains low confidence."
            ),
            rule_version="chair-stand-latest-matching-observation@1.0.0",
        ),
        release_rationale=(
            "Provide one low-cost, equipment-light first measurement while preserving direct observation, narrow interpretation, evidence provenance, and explicit population and self-report limitations."
        ),
        release_uncertainty=(
            "This owner-alpha release has not received independent clinician or domain-expert review. Approval would authorize the exact narrow protocol and estimate only; it would not establish medical clearance or scientific consensus."
        ),
    )


def _chair_stand_presentation_fields() -> dict[str, object]:
    return {
        "candidate_id": UUID("94000000-0000-4000-8000-000000000001"),
        "slug": "thirty_second_chair_stand",
        "release_label": "30-second chair stand owner-alpha release",
        "prepared_at": datetime(2026, 9, 8, 10, 45, tzinfo=UTC),
        "summary": (
            "A 30-second count of controlled stand-and-sit repetitions using a standardized chair. It is intended as a simple first repeatable measurement, not a workout or pass/fail test."
        ),
        "measures": (
            "Assessment-specific lower-body sit-to-stand performance with muscular-endurance and functional-strength demands."
        ),
        "does_not_measure": (
            "Maximum strength, power, sport performance, injury risk, or medical fitness.",
            "A universal 0-100 athleticism score or a comparison with population norms.",
            "Whether a particular exercise or training dose is appropriate.",
        ),
        "capability_domain": CapabilityDomain.MUSCULAR_ENDURANCE,
        "estimate_scope": "assessment_specific:thirty_second_chair_stand_repetitions",
        "setup_requirements": (
            "Sturdy straight-backed chair without arms, with a firm seat about 43-45 cm (17 inches) high.",
            "Chair placed against a wall on a nonslip surface with the nearby floor clear.",
            "Audible 30-second timer and a consistent footwear/surface setup for later comparisons.",
        ),
        "protocol_steps": (
            "Set up the chair and timer; do not improvise with a rolling, soft, unstable, or unusually high/low seat.",
            "Perform a comfortable 10-second familiarization, then rest seated for at least 60 seconds.",
            "Cross arms at the chest and complete controlled full stands and sits for 30 seconds without using the arms.",
            "Enter only the directly counted whole-number repetitions; a stopped or changed-setup attempt is not a completed result.",
        ),
        "stop_conditions": (
            "Do not start when the separate eligibility review is missing, expired, or does not authorize assessment.",
            "Stop for pain, dizziness, chest discomfort, unusual shortness of breath, loss of balance, or uncontrolled movement.",
            "Stop if the arms are needed to continue; do not guess what the final count would have been.",
        ),
        "operational_choices": (
            "One recorded trial follows a 10-second familiarization and 60-second rest.",
            "Reassessment is provisionally spaced at 28 days to reduce practice-driven retesting.",
            "The estimate stores the direct repetition count, remains assessment-specific, and is valid for 28 days.",
            "A single completed attempt produces low confidence; repeated comparable observations can raise it only to moderate.",
        ),
        "unresolved_limitations": (
            "The healthy-young-adult evidence used investigator administration and two trials; this protocol does not reproduce that procedure exactly.",
            "Direct digital self-administration evidence comes from older adults with hip or knee osteoarthritis, not a general healthy-athlete sample.",
            "Self-reported counts averaged 1.5 repetitions above in-person counts in the small comparison study.",
            "The 28-day interval is a conservative product decision, not a validated optimal reassessment schedule.",
            "No independent clinician or domain-expert has reviewed this owner-alpha candidate.",
        ),
        "evidence": (
            AssessmentCandidateEvidenceSummary(
                title="Lein et al. (2022): healthy young-adult validity study",
                source_url="https://pubmed.ncbi.nlm.nih.gov/35949374/",
                population="81 healthy adults aged 19-35.",
                finding="Chair-stand count correlated with five-times sit-to-stand and lateral step-up performance.",
                limitations=(
                    "Cross-sectional single study with investigator administration and two trials.",
                    "Did not establish sport-performance prediction, causal effects, or universal norms.",
                ),
                conflict_disclosure="The PubMed record reports no declared conflicts of interest.",
            ),
            AssessmentCandidateEvidenceSummary(
                title="Dahlberg et al. (2025): digital self-administration reliability study",
                source_url="https://pubmed.ncbi.nlm.nih.gov/40330808/",
                population="Older adults with hip or knee osteoarthritis; 54 in test-retest and 18 in the in-person comparison.",
                finding="Digital self-reports were repeatable, but averaged 1.5 repetitions above in-person counts.",
                limitations=(
                    "Small selected samples; predominantly female and already familiar with the digital treatment context.",
                    "Population transfer is uncertain and the inter-rater confidence interval was wide.",
                ),
                conflict_disclosure="The paper reports employment, advisory, founder, and other roles involving Joint Academy among several authors.",
            ),
        ),
    }


def _standard_pushup_release() -> PreparedAssessmentGovernanceRelease:
    source_created_at = datetime(2026, 9, 15, 9, 0, tzinfo=UTC)
    claim_created_at = datetime(2026, 9, 15, 9, 10, tzinfo=UTC)
    definition_created_at = datetime(2026, 9, 15, 9, 20, tzinfo=UTC)
    prepared_at = datetime(2026, 9, 15, 9, 30, tzinfo=UTC)

    isbn = EvidenceSourceIdentifier(scheme="isbn", value="9781975219246")
    source = EvidenceSource(
        id=UUID("90000000-0000-4000-8000-000000000003"),
        created_at=source_created_at,
        title="ACSM's Guidelines for Exercise Testing and Prescription",
        authors=(
            "Cemal Ozemek",
            "Amanda Bonikowske",
            "Jeffrey Christle",
            "Paul M. Gallo",
        ),
        journal=None,
        publication_year=2026,
        publication_types=("Professional guideline", "Textbook"),
        primary_identifier=isbn,
        source_identifiers=(isbn,),
        metadata_provider="manual",
        retrieval_uri="https://www.ncbi.nlm.nih.gov/nlmcatalog/137328",
        retrieval_query="ISBN 9781975219246; Chapter 3; Box 3.10; Table 3.11",
        retrieved_at=source_created_at,
        metadata_version="owner-supplied-acsm-12-pdf-and-nlm-catalog@2026-09-15",
        provenance_notes=(
            "The owner supplied a local copy for review; the PDF itself is not stored in AGAS.",
            "The NLM Catalog record confirms the editors, edition, publisher, and EPUB ISBN 9781975219246.",
            "The protocol statement was checked against Chapter 3, PDF pages 244-245, including Box 3.10.",
            "Table 3.11 was inspected but its sex-specific categories are not activated by this release.",
        ),
    )
    claim = EvidenceClaim(
        id=UUID("91000000-0000-4000-8000-000000000003"),
        created_at=claim_created_at,
        claim=(
            "ACSM's 12th-edition guideline describes the maximum number of consecutive push-ups "
            "performed without rest, with standardized body alignment and repetition criteria, "
            "as a simple field assessment of upper-body muscular endurance."
        ),
        domain="assessment_protocol_and_construct",
        population=(
            "Apparently healthy adults addressed by the guideline; the accompanying reference "
            "categories are age- and sex-stratified and do not define one universal population."
        ),
        intervention=(
            "Maximum consecutive push-up field test performed with the Box 3.10 technique."
        ),
        comparator="No comparator is required for the direct repetition-count observation.",
        outcome="Maximum consecutive repetitions completed without rest while technique is retained.",
        study_design="Professional guideline and textbook synthesis citing primary references 166-168",
        effect_direction=(
            "A larger valid repetition count represents greater performance on this exact test."
        ),
        uncertainty=(
            "The source provides a protocol and descriptive reference categories; it does not "
            "establish an AGAS competency floor, exercise prescription, or total-body fitness inference."
        ),
        limitations=(
            "Push-up results are specific to the exact movement, range of motion, pace, and stopping rules.",
            "Table 3.11 uses standard push-ups for males and modified knee push-ups for females, so its rows are not directly comparable.",
            "The textbook does not reproduce subgroup sampling details for the reference table.",
            "Self-counted technique has not been independently validated by this release.",
        ),
        evidence_strength=EvidenceStrength.LOW,
        athlete_applicability=Applicability.MODERATE,
        applicability_notes=(
            "The no-equipment field protocol is practical for an adult recreationally trained "
            "athlete, but only within-person tracking of the standard version is authorized."
        ),
        source_identifiers=(isbn,),
        source_record_ids=(source.id,),
        reviewer="Codex evidence synthesis candidate; authority pending",
        claim_version="acsm-standard-pushup-protocol@1.0.0",
    )
    definition = AssessmentDefinition(
        id=UUID("92000000-0000-4000-8000-000000000002"),
        created_at=definition_created_at,
        slug="maximum_consecutive_standard_pushups",
        name="Maximum consecutive standard push-ups",
        domain=CapabilityDomain.MUSCULAR_ENDURANCE,
        observation_type="maximum_consecutive_standard_pushup_repetitions",
        intensity=AssessmentIntensity.HIGH,
        unit_or_scale="repetitions",
        protocol_version="agas-maximum-consecutive-standard-pushups@1.0.0",
        blocked_by_health_screening_flags=(
            "upper_body_wrist_or_hand_concern",
            "standard_pushup_control_not_confirmed",
        ),
    )
    review_id = UUID("93000000-0000-4000-8000-000000000002")
    return PreparedAssessmentGovernanceRelease(
        release_id=UUID("94000000-0000-4000-8000-000000000002"),
        release_label="Maximum consecutive standard push-ups owner-alpha release",
        prepared_at=prepared_at,
        sources=(source,),
        claims=(claim,),
        evidence_reviews=(
            EvidenceClaimReviewDraft(
                id=UUID("95000000-0000-4000-8000-000000000003"),
                evidence_claim_id=claim.id,
                sequence_number=1,
                source_verification_rationale=(
                    "The construct statement, consecutive-without-rest score, technique criteria, "
                    "stopping rule, sex-specific protocol difference, and normative limitation were "
                    "checked against Chapter 3, Box 3.10 and Table 3.11 on PDF pages 244-245."
                ),
                extraction_rationale=(
                    "The claim retains only the source-supported test construct and procedure. It "
                    "does not import an age/sex category, percentile, fitness grade, or training dose."
                ),
                evidence_strength_rationale=(
                    "Low reflects use of a textbook synthesis for a narrow protocol claim without "
                    "independent appraisal of its cited primary validation studies."
                ),
                applicability_rationale=(
                    "Moderate reflects a practical no-equipment adult field test while limiting "
                    "interpretation to repeat performance on the exact standard version."
                ),
                uncertainty=(
                    "Self-counting, technique drift, familiarization, fatigue, and day-to-day "
                    "variation may materially affect the result."
                ),
                conflict_disclosure=(
                    "No protocol-specific conflict disclosure was identified in the inspected "
                    "textbook pages; this is not a claim that the cited primary studies had none."
                ),
                review_version="acsm-standard-pushup-evidence-review@1.0.0",
            ),
        ),
        definition=definition,
        protocol_review=AssessmentDefinitionReviewDraft(
            id=review_id,
            assessment_definition_id=definition.id,
            sequence_number=1,
            protocol_instructions=(
                "Use a nonslip, level floor with enough clear space for a full plank. Wear the same footwear, or use the same barefoot setup, on later attempts.",
                "Warm up for 5 to 10 minutes with light aerobic movement, dynamic upper-body movement, and several comfortable practice push-ups; rest until breathing is comfortable before the recorded attempt.",
                "Start in the standard down position with fingers pointing forward under the shoulders, toes as the pivot, head neutral, and the body held in one straight line.",
                "Press to straight arms, then lower under control until the chin lightly touches a clean folded towel or other thin, consistent target while the abdomen stays off the floor.",
                "Continue consecutive repetitions without resting. Count only repetitions that return to straight arms while body alignment and the same target depth are maintained.",
                "End the attempt when you stop to rest, strain forcibly, or cannot restore the required technique within two attempted repetitions. Record only the valid completed repetitions before the stopping condition.",
            ),
            result_entry_instructions=(
                "Enter the whole-number count of valid consecutive standard push-ups directly "
                "observed. Do not convert it to a sex/age category, pressing-strength score, or "
                "training dose. Do not enter a completed result if pain or another safety stop ended the attempt."
            ),
            measurement_schema=AssessmentMeasurementSchema(
                measurement_type=AssessmentMeasurementType.INTEGER,
                label="Valid consecutive standard push-up repetitions",
                minimum=0,
                step=1,
                measurement_schema_version="maximum-standard-pushup-count@1.0.0",
            ),
            recommended_reassessment_days=28,
            self_administered=True,
            evidence_claim_ids=(claim.id,),
            applicability_notes=(
                "Owner-alpha use is limited to repeat measurement of the same athlete's standard "
                "push-up performance after current readiness screening and a pain-free controlled repetition."
            ),
            uncertainty=(
                "The sex-neutral use of the standard version is an AGAS operational choice for "
                "within-person tracking, not a claim that the source's male and female reference "
                "rows are interchangeable. No normative category is calculated."
            ),
            review_version="agas-maximum-standard-pushup-review@1.0.0",
        ),
        estimation_policy=CapabilityEstimationPolicyDraft(
            id=UUID("96000000-0000-4000-8000-000000000002"),
            assessment_definition_id=definition.id,
            assessment_definition_review_id=review_id,
            sequence_number=1,
            domain=definition.domain,
            observation_type=definition.observation_type,
            unit_or_scale=definition.unit_or_scale,
            calculation_method="latest-matching-observation",
            valid_for_days=28,
            multi_observation_window_days=28,
            evidence_claim_ids=(claim.id,),
            applicability_notes=(
                "Preserve the direct repetition count as a low-confidence, assessment-specific "
                "upper-body muscular-endurance estimate for within-person tracking only."
            ),
            uncertainty=(
                "No normative conversion, universal score, maximum-strength inference, competency "
                "floor, or exercise prescription is authorized."
            ),
            rule_version="standard-pushup-latest-matching-observation@1.0.0",
        ),
        release_rationale=(
            "Add a practical no-equipment upper-body endurance measurement while retaining exact "
            "protocol provenance and refusing the source's non-comparable sex-specific categories."
        ),
        release_uncertainty=(
            "This owner-alpha release has not received independent domain-expert review. Approval "
            "would authorize only the exact assessment and narrow estimate, not a training threshold."
        ),
    )


def _standard_pushup_presentation_fields() -> dict[str, object]:
    return {
        "candidate_id": UUID("94000000-0000-4000-8000-000000000002"),
        "slug": "maximum_consecutive_standard_pushups",
        "release_label": "Maximum consecutive standard push-ups owner-alpha release",
        "prepared_at": datetime(2026, 9, 15, 9, 30, tzinfo=UTC),
        "summary": (
            "A no-equipment count of consecutive standard push-ups using one repeatable form. It "
            "creates a personal baseline, not a sex-based fitness grade or a workout prescription."
        ),
        "measures": (
            "Assessment-specific upper-body muscular-endurance performance during consecutive standard push-ups."
        ),
        "does_not_measure": (
            "Maximum pressing strength, whole-body athleticism, injury risk, or medical fitness.",
            "A universal 0-100 score or a valid comparison between standard and knee push-ups.",
            "Whether push-ups belong in a workout or what dose should be prescribed.",
        ),
        "capability_domain": CapabilityDomain.MUSCULAR_ENDURANCE,
        "estimate_scope": "assessment_specific:maximum_consecutive_standard_pushup_repetitions",
        "setup_requirements": (
            "Level nonslip floor with clear space for a full plank.",
            "A clean folded towel or similarly thin, repeatable chin-depth target.",
            "The same footwear, surface, hand position, and depth target on future attempts.",
        ),
        "protocol_steps": (
            "Warm up with light movement and comfortable practice repetitions, then rest until breathing is comfortable.",
            "Use the standard toes-as-pivot version with hands under shoulders and body held in one straight line.",
            "Press to straight arms and lower until the chin lightly touches the consistent target without the abdomen touching the floor.",
            "Continue without rest and count only valid repetitions; stop when the governed technique rule is reached.",
        ),
        "stop_conditions": (
            "Do not start when the current readiness screen is missing, expired, or does not authorize the assessment.",
            "Stop immediately for pain, dizziness, chest discomfort, unusual shortness of breath, numbness, or loss of control.",
            "End the test when you rest, strain forcibly, or cannot restore valid technique within two attempted repetitions.",
        ),
        "operational_choices": (
            "The same standard movement is recorded for any athlete who selects this protocol; AGAS does not infer sex.",
            "ACSM Table 3.11 age/sex categories are not activated because the table compares different movement versions.",
            "The estimate stores the direct count, remains assessment-specific, and is valid for 28 days.",
            "A single completed attempt produces low confidence and is intended for within-person comparison only.",
        ),
        "unresolved_limitations": (
            "The source is a professional guideline/textbook synthesis; its cited primary protocol studies were not independently appraised in this release.",
            "Self-counting may miss depth, alignment, locking, or rest errors without an observer or video review.",
            "The warm-up and thin chin target make the instructions reproducible but are AGAS operational details, not a verbatim reproduction of Box 3.10.",
            "No governed competency floor or training dose currently consumes this estimate.",
            "No independent domain expert has reviewed this owner-alpha candidate.",
        ),
        "evidence": (
            AssessmentCandidateEvidenceSummary(
                title="ACSM Guidelines, 12th edition: Box 3.10 and Table 3.11",
                source_url="https://www.ncbi.nlm.nih.gov/nlmcatalog/137328",
                population=(
                    "Apparently healthy adults addressed by the guideline; the reference table is age- and sex-stratified."
                ),
                finding=(
                    "The guideline presents maximum consecutive push-ups without rest as a simple field assessment of upper-body muscular endurance and specifies repetition technique."
                ),
                limitations=(
                    "The reference table uses standard push-ups for males and modified knee push-ups for females.",
                    "This release does not use the table's categories or claim that self-counted form is externally validated.",
                ),
                conflict_disclosure=(
                    "No protocol-specific conflict disclosure was identified on the inspected textbook pages."
                ),
            ),
        ),
    }
