from datetime import UTC, datetime
from uuid import uuid4

import pytest
from agas_domain import (
    AdaptationRelationship,
    AdaptationRelationshipType,
    Athlete,
    CapabilityDomain,
    CapabilityEstimate,
    Confidence,
    EvidenceSource,
    EvidenceSourceIdentifier,
    Observation,
    ObservationSource,
    Provenance,
    TrainingResponse,
)
from pydantic import ValidationError

NOW = datetime(2026, 8, 19, 14, 0, tzinfo=UTC)


def test_observation_and_capability_estimate_are_distinct_types() -> None:
    athlete = Athlete(display_name="Test athlete")
    observation = Observation(
        athlete_id=athlete.id,
        observed_at=NOW,
        observation_type="standing_broad_jump",
        measurement=1.82,
        unit="m",
        source=ObservationSource.TEST_RESULT,
        reliability=Confidence.MODERATE,
        provenance=Provenance(
            recorded_by="athlete",
            source_system="agas-web",
            ingestion_method="manual",
        ),
    )
    estimate = CapabilityEstimate(
        athlete_id=athlete.id,
        domain=CapabilityDomain.EXPLOSIVE_POWER,
        estimate={"band": "developing"},
        unit_or_scale="ordinal_band_v1",
        confidence=Confidence.LOW,
        calculation_method="broad_jump_band",
        source_observation_ids=(observation.id,),
        estimated_at=NOW,
        rule_version="broad-jump-band@1.0.0",
    )

    assert observation.measurement == 1.82
    assert estimate.kind == "derived"
    assert estimate.source_observation_ids == (observation.id,)
    assert observation.__class__.__name__ == "Observation"
    assert estimate.__class__.__name__ == "CapabilityEstimate"


def test_capability_estimate_requires_observation_provenance() -> None:
    with pytest.raises(ValidationError, match="source_observation_ids"):
        CapabilityEstimate(
            athlete_id=uuid4(),
            domain=CapabilityDomain.EXPLOSIVE_POWER,
            estimate=74,
            unit_or_scale="unsupported_score",
            confidence=Confidence.HIGH,
            calculation_method="unknown",
            source_observation_ids=(),
            estimated_at=NOW,
            rule_version="unknown@1.0.0",
        )


def test_assessment_estimate_requires_complete_policy_and_performance_lineage() -> None:
    with pytest.raises(ValidationError, match="must be supplied together"):
        CapabilityEstimate(
            athlete_id=uuid4(),
            domain=CapabilityDomain.EXPLOSIVE_POWER,
            estimate=1.82,
            unit_or_scale="m",
            estimate_scope="assessment_specific:standing_broad_jump",
            confidence=Confidence.LOW,
            calculation_method="latest-matching-observation",
            source_observation_ids=(uuid4(),),
            estimated_at=NOW,
            rule_version="latest-matching-observation@1.0.0",
            capability_estimation_policy_id=uuid4(),
        )


def test_domain_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        Observation(
            athlete_id=uuid4(),
            observed_at=datetime(2026, 8, 19, 14, 0),
            observation_type="user_report",
            measurement="felt steady",
            source=ObservationSource.USER_REPORT,
            reliability=Confidence.LOW,
            provenance=Provenance(
                recorded_by="athlete",
                source_system="agas-web",
                ingestion_method="manual",
            ),
        )


def test_adaptation_relationship_requires_evidence_provenance() -> None:
    with pytest.raises(ValidationError, match="evidence_claim_ids"):
        AdaptationRelationship(
            target_adaptation_id=uuid4(),
            relationship=AdaptationRelationshipType.PREREQUISITE,
            strength=Confidence.LOW,
            confidence=Confidence.LOW,
            population="unspecified",
            evidence_claim_ids=(),
        )


def test_training_response_counts_prescription_items_not_whole_sessions() -> None:
    execution_id = uuid4()
    adherence_ids = (uuid4(), uuid4())
    response = TrainingResponse(
        athlete_id=uuid4(),
        block_plan_id=uuid4(),
        adaptation_id=uuid4(),
        intervention_summary="Two prescription items delivered in one session.",
        prescription_ids=(uuid4(), uuid4()),
        session_execution_ids=(execution_id,),
        session_adherence_ids=adherence_ids,
        prescribed_item_count=2,
        completed_item_count=2,
        prescribed_dose_total=20,
        actual_dose_total=20,
        dose_unit="repetitions",
        adherence_ratio=1,
        baseline_capability_estimate_id=uuid4(),
        followup_capability_estimate_id=uuid4(),
        baseline_value=10,
        followup_value=12,
        observed_change=2,
        measurement_uncertainty="Software fixture.",
        confidence=Confidence.MODERATE,
        source_observation_ids=(uuid4(),),
        calculated_at=NOW,
        calculation_method="software fixture",
        rule_version="fixture@1.0.0",
    )

    assert response.prescribed_item_count == len(adherence_ids)
    assert response.prescribed_item_count > len(response.session_execution_ids)

    with pytest.raises(ValidationError, match="prescribed item count"):
        TrainingResponse.model_validate(
            {
                **response.model_dump(),
                "prescribed_item_count": 1,
                "completed_item_count": 1,
            }
        )


def test_evidence_source_requires_explicit_snapshot_lineage() -> None:
    identifier = EvidenceSourceIdentifier(scheme="pmid", value="12345678")
    first = EvidenceSource(
        title="Software fixture publication",
        primary_identifier=identifier,
        source_identifiers=(identifier,),
        metadata_provider="pubmed",
        retrieval_uri="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        retrieved_at=NOW,
        metadata_version="pubmed-xml@1",
    )

    assert first.sequence_number == 1
    assert first.supersedes_source_id is None
    with pytest.raises(ValidationError, match="must identify the snapshot"):
        EvidenceSource(
            title="Updated software fixture publication",
            primary_identifier=identifier,
            source_identifiers=(identifier,),
            metadata_provider="pubmed",
            retrieval_uri="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            retrieved_at=NOW,
            metadata_version="pubmed-xml@2",
            sequence_number=2,
        )


def test_evidence_source_primary_identifier_must_be_in_retrieved_metadata() -> None:
    with pytest.raises(ValidationError, match="primary_identifier"):
        EvidenceSource(
            title="Software fixture publication",
            primary_identifier=EvidenceSourceIdentifier(scheme="pmid", value="12345678"),
            source_identifiers=(
                EvidenceSourceIdentifier(scheme="doi", value="10.0000/software-fixture"),
            ),
            metadata_provider="manual",
            retrieval_uri="urn:agas:test:evidence-source",
            retrieved_at=NOW,
            metadata_version="fixture@1",
        )
