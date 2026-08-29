from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from agas_api.athletic_dashboard import (
    AthleticDashboardNotFoundError,
    get_athletic_dashboard_projection,
)
from agas_domain import (
    Athlete,
    CapabilityDomain,
    CapabilityEstimate,
    Confidence,
    Observation,
    ObservationSource,
    Provenance,
)
from agas_domain.persistence.repository import DomainRepository
from sqlalchemy.orm import Session

AS_OF = datetime(2026, 8, 28, 16, 0, tzinfo=UTC)
PROVENANCE = Provenance(
    recorded_by="dashboard-fixture",
    source_system="integration-test",
    ingestion_method="synthetic-fixture",
)


def test_dashboard_keeps_every_unestimated_domain_explicit(session: Session) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Unmeasured athlete")
    repository.add_athlete(athlete)
    session.commit()

    projection = get_athletic_dashboard_projection(session, athlete.id, AS_OF)

    assert projection.estimated_domain_count == 0
    assert projection.unestimated_domain_count == len(CapabilityDomain)
    assert tuple(item.domain for item in projection.domains) == tuple(CapabilityDomain)
    assert all(item.status == "not_estimated" for item in projection.domains)
    assert all(item.latest_estimates == () for item in projection.domains)


def test_dashboard_separates_measurement_series_and_preserves_derived_lineage(
    session: Session,
) -> None:
    repository = DomainRepository(session)
    athlete = Athlete(display_name="Measured athlete")
    repository.add_athlete(athlete)
    session.flush()

    observations = tuple(
        Observation(
            athlete_id=athlete.id,
            observed_at=AS_OF - timedelta(days=offset),
            observation_type=f"dashboard_fixture_{offset}",
            measurement=value,
            unit="kg",
            source=ObservationSource.TEST_RESULT,
            reliability=Confidence.MODERATE,
            provenance=PROVENANCE,
        )
        for offset, value in ((30, 80), (5, 90), (20, 10), (-1, 999))
    )
    for observation in observations:
        repository.add_observation(observation)
    session.flush()

    old_estimate = _estimate(
        athlete.id,
        observations[0],
        estimate=80,
        scope="assessment_specific:trap_bar_3rm",
        estimated_at=AS_OF - timedelta(days=30),
        valid_until=AS_OF - timedelta(days=1),
    )
    current_estimate = _estimate(
        athlete.id,
        observations[1],
        estimate=90,
        scope="assessment_specific:trap_bar_3rm",
        estimated_at=AS_OF - timedelta(days=5),
        valid_until=AS_OF + timedelta(days=25),
    )
    stale_distinct_series = _estimate(
        athlete.id,
        observations[2],
        estimate=10,
        scope="assessment_specific:push_up_repetitions",
        estimated_at=AS_OF - timedelta(days=20),
        valid_until=AS_OF,
    )
    future_estimate = _estimate(
        athlete.id,
        observations[3],
        estimate=999,
        scope="assessment_specific:future_test",
        estimated_at=AS_OF + timedelta(days=1),
        valid_until=AS_OF + timedelta(days=31),
    )
    for estimate in (
        old_estimate,
        current_estimate,
        stale_distinct_series,
        future_estimate,
    ):
        repository.add_capability_estimate(estimate)
    session.commit()

    projection = get_athletic_dashboard_projection(session, athlete.id, AS_OF)
    strength = next(
        item for item in projection.domains if item.domain is CapabilityDomain.MAXIMUM_STRENGTH
    )

    assert strength.status == "mixed"
    assert strength.historical_estimate_count == 3
    assert len(strength.latest_estimates) == 2
    trap_bar = next(
        item
        for item in strength.latest_estimates
        if item.estimate_scope == "assessment_specific:trap_bar_3rm"
    )
    assert trap_bar.estimate_id == current_estimate.id
    assert trap_bar.kind == "derived"
    assert trap_bar.status == "current"
    assert trap_bar.historical_estimate_count == 2
    assert trap_bar.source_observation_ids == (observations[1].id,)
    assert trap_bar.calculation_method == "synthetic dashboard fixture"
    push_up = next(
        item
        for item in strength.latest_estimates
        if item.estimate_scope == "assessment_specific:push_up_repetitions"
    )
    assert push_up.status == "stale"
    assert all(item.estimate_id != future_estimate.id for item in strength.latest_estimates)
    assert projection.estimated_domain_count == 1


def test_dashboard_rejects_missing_athletes_and_naive_projection_times(
    session: Session,
) -> None:
    with pytest.raises(AthleticDashboardNotFoundError, match="athlete does not exist"):
        get_athletic_dashboard_projection(session, uuid4(), AS_OF)

    repository = DomainRepository(session)
    athlete = Athlete(display_name="Time validation athlete")
    repository.add_athlete(athlete)
    session.commit()
    with pytest.raises(ValueError, match="must include a timezone"):
        get_athletic_dashboard_projection(session, athlete.id, datetime(2026, 8, 28, 16, 0))


def _estimate(
    athlete_id: UUID,
    observation: Observation,
    *,
    estimate: float,
    scope: str,
    estimated_at: datetime,
    valid_until: datetime,
) -> CapabilityEstimate:
    return CapabilityEstimate(
        athlete_id=athlete_id,
        domain=CapabilityDomain.MAXIMUM_STRENGTH,
        estimate=estimate,
        unit_or_scale="kg",
        estimate_scope=scope,
        confidence=Confidence.MODERATE,
        calculation_method="synthetic dashboard fixture",
        source_observation_ids=(observation.id,),
        estimated_at=estimated_at,
        valid_until=valid_until,
        rule_version="dashboard-fixture@1.0.0",
    )
