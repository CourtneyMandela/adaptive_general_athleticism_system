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
    Observation,
    ObservationSource,
    Provenance,
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
