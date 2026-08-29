from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from agas_domain import CapabilityDomain, CapabilityEstimate, Confidence
from agas_domain.persistence.repository import DomainRepository
from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy.orm import Session

CapabilitySeriesStatus = Literal["current", "stale"]
CapabilityDomainStatus = Literal["not_estimated", "current", "stale", "mixed"]


class CapabilitySeriesProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    estimate_id: UUID
    kind: Literal["derived"] = "derived"
    estimate_scope: str
    estimate: JsonValue
    unit_or_scale: str
    confidence: Confidence
    status: CapabilitySeriesStatus
    calculation_method: str
    source_observation_ids: tuple[UUID, ...]
    estimated_at: datetime
    valid_until: datetime | None
    rule_version: str
    historical_estimate_count: int


class CapabilityDomainProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    domain: CapabilityDomain
    status: CapabilityDomainStatus
    latest_estimates: tuple[CapabilitySeriesProjection, ...]
    historical_estimate_count: int


class AthleticDashboardProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    athlete_id: UUID
    athlete_display_name: str
    as_of: datetime
    domains: tuple[CapabilityDomainProjection, ...]
    estimated_domain_count: int
    unestimated_domain_count: int
    projection_version: str = "athletic-dashboard-projection@1.0.0"


class AthleticDashboardNotFoundError(LookupError):
    pass


def get_athletic_dashboard_projection(
    session: Session, athlete_id: UUID, as_of: datetime | None = None
) -> AthleticDashboardProjection:
    repository = DomainRepository(session)
    athlete = repository.get_athlete(athlete_id)
    if athlete is None:
        raise AthleticDashboardNotFoundError("athlete does not exist")
    instant = as_of or datetime.now(UTC)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("athletic dashboard time must include a timezone")

    visible_estimates = tuple(
        estimate
        for estimate in repository.list_capability_estimates(athlete_id)
        if estimate.estimated_at <= instant
    )
    series_counts = Counter(
        (estimate.domain, estimate.estimate_scope, estimate.unit_or_scale)
        for estimate in visible_estimates
    )
    latest_by_series: dict[tuple[CapabilityDomain, str, str], CapabilityEstimate] = {}
    for estimate in visible_estimates:
        key = (estimate.domain, estimate.estimate_scope, estimate.unit_or_scale)
        latest_by_series.setdefault(key, estimate)

    domains = []
    for domain in CapabilityDomain:
        domain_keys = sorted(
            (key for key in latest_by_series if key[0] is domain),
            key=lambda key: (key[1], key[2]),
        )
        domain_series = tuple(
            CapabilitySeriesProjection(
                estimate_id=estimate.id,
                estimate_scope=estimate.estimate_scope,
                estimate=estimate.estimate,
                unit_or_scale=estimate.unit_or_scale,
                confidence=estimate.confidence,
                status=(
                    "stale"
                    if estimate.valid_until is not None and estimate.valid_until <= instant
                    else "current"
                ),
                calculation_method=estimate.calculation_method,
                source_observation_ids=estimate.source_observation_ids,
                estimated_at=estimate.estimated_at,
                valid_until=estimate.valid_until,
                rule_version=estimate.rule_version,
                historical_estimate_count=series_counts[
                    (estimate.domain, estimate.estimate_scope, estimate.unit_or_scale)
                ],
            )
            for key in domain_keys
            for estimate in (latest_by_series[key],)
        )
        statuses = {item.status for item in domain_series}
        if not statuses:
            domain_status: CapabilityDomainStatus = "not_estimated"
        elif len(statuses) > 1:
            domain_status = "mixed"
        elif "stale" in statuses:
            domain_status = "stale"
        else:
            domain_status = "current"
        domains.append(
            CapabilityDomainProjection(
                domain=domain,
                status=domain_status,
                latest_estimates=domain_series,
                historical_estimate_count=sum(
                    count for key, count in series_counts.items() if key[0] is domain
                ),
            )
        )

    estimated_domain_count = sum(item.status != "not_estimated" for item in domains)
    return AthleticDashboardProjection(
        athlete_id=athlete.id,
        athlete_display_name=athlete.display_name,
        as_of=instant,
        domains=tuple(domains),
        estimated_domain_count=estimated_domain_count,
        unestimated_domain_count=len(domains) - estimated_domain_count,
    )
