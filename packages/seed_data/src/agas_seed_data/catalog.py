from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from agas_domain import Adaptation, Athlete, CostLevel, Equipment, EvidenceClaim, Exercise
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CatalogReviewStatus(StrEnum):
    SECONDARY_AI_VERIFIED = "secondary_ai_verified"
    PRODUCTION_APPROVED = "production_approved"


class SeedCatalogManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    catalog_version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
    review_status: CatalogReviewStatus
    reviewed_by: Annotated[str, Field(min_length=1)]
    reviewed_at: Annotated[str, Field(min_length=1)]
    scope: Annotated[str, Field(min_length=1)]
    notes: Annotated[tuple[str, ...], Field(min_length=1)]


class ScenarioEnvironment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Annotated[str, Field(min_length=1)]
    equipment_ids: tuple[UUID, ...]
    floor_area_m2: float = Field(gt=0)
    max_noise_level: CostLevel
    outdoor_access: bool


class TravelScenarioSeed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scenario_version: Annotated[str, Field(pattern=r"^\d+\.\d+\.\d+$")]
    athlete: Athlete
    available_weekdays: Annotated[tuple[int, ...], Field(min_length=1)]
    target_adaptation_ids: Annotated[tuple[UUID, ...], Field(min_length=1)]
    home: ScenarioEnvironment
    travel: ScenarioEnvironment
    notes: Annotated[tuple[str, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_days(self) -> TravelScenarioSeed:
        if len(set(self.available_weekdays)) != len(self.available_weekdays):
            raise ValueError("available_weekdays must not contain duplicates")
        if any(day < 0 or day > 6 for day in self.available_weekdays):
            raise ValueError("available weekdays must be in the range 0 through 6")
        return self


class SeedCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest: SeedCatalogManifest
    evidence_claims: tuple[EvidenceClaim, ...]
    adaptations: tuple[Adaptation, ...]
    equipment: tuple[Equipment, ...]
    exercises: tuple[Exercise, ...]
    travel_scenario: TravelScenarioSeed

    @model_validator(mode="after")
    def validate_references(self) -> SeedCatalog:
        claim_ids = self._unique_ids("evidence claims", self.evidence_claims)
        adaptation_ids = self._unique_ids("adaptations", self.adaptations)
        equipment_ids = self._unique_ids("equipment", self.equipment)
        exercise_ids = self._unique_ids("exercises", self.exercises)

        for adaptation in self.adaptations:
            self._require_subset(
                f"adaptation {adaptation.id} evidence", adaptation.evidence_claim_ids, claim_ids
            )
        for exercise in self.exercises:
            self._require_subset(
                f"exercise {exercise.id} adaptations",
                (*exercise.primary_adaptation_ids, *exercise.secondary_adaptation_ids),
                adaptation_ids,
            )
            self._require_subset(
                f"exercise {exercise.id} equipment",
                exercise.equipment_requirement_ids,
                equipment_ids,
            )
            self._require_subset(
                f"exercise {exercise.id} relationships",
                (*exercise.progression_exercise_ids, *exercise.regression_exercise_ids),
                exercise_ids,
            )
        self._require_subset(
            "travel scenario adaptations",
            self.travel_scenario.target_adaptation_ids,
            adaptation_ids,
        )
        self._require_subset(
            "home scenario equipment", self.travel_scenario.home.equipment_ids, equipment_ids
        )
        self._require_subset(
            "travel scenario equipment", self.travel_scenario.travel.equipment_ids, equipment_ids
        )
        return self

    @staticmethod
    def _unique_ids(label: str, records: tuple[Any, ...]) -> set[UUID]:
        ids = [record.id for record in records]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{label} must have unique ids")
        return set(ids)

    @staticmethod
    def _require_subset(label: str, references: tuple[UUID, ...], valid_ids: set[UUID]) -> None:
        missing = set(references) - valid_ids
        if missing:
            raise ValueError(f"{label} reference unknown ids: {sorted(map(str, missing))}")


def load_seed_catalog(data_root: Path | None = None) -> SeedCatalog:
    """Load and cross-validate the small repository-owned seed catalog."""

    root = data_root or Path(__file__).resolve().parents[4] / "data"
    return SeedCatalog(
        manifest=SeedCatalogManifest.model_validate(_read_json(root / "seed-manifest.json")),
        evidence_claims=tuple(
            EvidenceClaim.model_validate(item)
            for item in _read_json(root / "evidence_seed" / "claims.json")
        ),
        adaptations=tuple(
            Adaptation.model_validate(item)
            for item in _read_json(root / "adaptations" / "catalog.json")
        ),
        equipment=tuple(
            Equipment.model_validate(item)
            for item in _read_json(root / "equipment" / "catalog.json")
        ),
        exercises=tuple(
            Exercise.model_validate(item)
            for item in _read_json(root / "exercises" / "catalog.json")
        ),
        travel_scenario=TravelScenarioSeed.model_validate(
            _read_json(root / "synthetic_athletes" / "travel_scenario.json")
        ),
    )


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)
