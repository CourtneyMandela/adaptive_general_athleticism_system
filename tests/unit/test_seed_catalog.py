import json
from pathlib import Path

import pytest
from agas_seed_data import CatalogReviewStatus, load_seed_catalog
from pydantic import ValidationError


def test_seed_catalog_loads_with_explicit_nonproduction_review_status() -> None:
    catalog = load_seed_catalog()

    assert catalog.manifest.review_status is CatalogReviewStatus.SECONDARY_AI_VERIFIED
    assert len(catalog.evidence_claims) == 3
    assert len(catalog.adaptations) == 8
    assert len(catalog.exercises) == 14
    assert all(claim.source_identifiers for claim in catalog.evidence_claims)
    assert all("approval pending" in claim.reviewer for claim in catalog.evidence_claims)


def test_seed_catalog_rejects_unknown_cross_catalog_reference(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[2] / "data"
    for relative in (
        "seed-manifest.json",
        "evidence_seed/claims.json",
        "adaptations/catalog.json",
        "equipment/catalog.json",
        "exercises/catalog.json",
        "synthetic_athletes/travel_scenario.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((source / relative).read_text(encoding="utf-8"), encoding="utf-8")

    scenario_path = tmp_path / "synthetic_athletes" / "travel_scenario.json"
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    scenario["target_adaptation_ids"].append("ffffffff-ffff-4fff-8fff-ffffffffffff")
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    with pytest.raises(ValidationError, match="travel scenario adaptations"):
        load_seed_catalog(tmp_path)
