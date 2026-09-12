from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import cast
from uuid import UUID

from agas_domain.persistence.models import Base
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator
from sqlalchemy import ColumnElement, Table, select
from sqlalchemy.orm import Session

EXPORT_VERSION = "athlete-data-export@1.0.0"


class AthleteExportTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    table_name: str = Field(min_length=1)
    primary_key_columns: tuple[str, ...]
    rows: tuple[dict[str, JsonValue], ...]


class AthleteExportExternalReference(BaseModel):
    """A referenced shared record intentionally outside the owner-data archive."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_table: str
    source_column: str
    target_table: str
    target_column: str
    target_value: JsonValue


class AthleteExportManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_count: int = Field(ge=1)
    table_counts: dict[str, int]
    content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scope: str = "athlete-owned rows and their non-athlete dependent rows"
    restore_status: str = "restore requires a separately validated procedure"


class AthleteDataExport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    export_version: str = EXPORT_VERSION
    generated_at: datetime
    athlete_id: UUID
    tables: tuple[AthleteExportTable, ...]
    external_references: tuple[AthleteExportExternalReference, ...]
    manifest: AthleteExportManifest

    @field_validator("generated_at")
    @classmethod
    def require_aware_generation_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("export generation time must include a timezone")
        return value


class AthleteDataExportNotFoundError(LookupError):
    pass


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return cast(JsonValue, value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return _json_value(value.value)
    if isinstance(value, bytes):
        return base64.urlsafe_b64encode(value).decode("ascii")
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    raise TypeError(f"unsupported export value type: {type(value).__name__}")


def _primary_key(table: Table, row: dict[str, object]) -> tuple[object, ...]:
    columns = tuple(column.name for column in table.primary_key.columns)
    if not columns:
        raise RuntimeError(f"export table {table.name} has no primary key")
    return tuple(row[column] for column in columns)


class AthleteDataExporter:
    """Create a deterministic owner-data archive without copying unrelated athletes."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def export(
        self, athlete_id: UUID, *, generated_at: datetime | None = None
    ) -> AthleteDataExport:
        instant = generated_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("export generation time must include a timezone")

        tables = tuple(Base.metadata.sorted_tables)
        athlete_table = Base.metadata.tables["athletes"]
        athlete_rows = self._rows(athlete_table, athlete_table.c.id == athlete_id)
        if not athlete_rows:
            raise AthleteDataExportNotFoundError("athlete does not exist")

        rows_by_table: dict[str, dict[tuple[object, ...], dict[str, object]]] = {}
        self._merge(rows_by_table, athlete_table, athlete_rows)
        for table in tables:
            if table.name == athlete_table.name or "athlete_id" not in table.c:
                continue
            self._merge(rows_by_table, table, self._rows(table, table.c.athlete_id == athlete_id))

        changed = True
        while changed:
            changed = False
            for table in tables:
                if "athlete_id" in table.c:
                    continue
                for foreign_key in table.foreign_keys:
                    target_table = foreign_key.column.table
                    target_rows = rows_by_table.get(target_table.name, {})
                    if not target_rows:
                        continue
                    target_values = {row[foreign_key.column.name] for row in target_rows.values()}
                    matching = self._rows(table, foreign_key.parent.in_(target_values))
                    changed = self._merge(rows_by_table, table, matching) or changed

        exported_tables = tuple(
            self._export_table(table, rows_by_table[table.name])
            for table in tables
            if rows_by_table.get(table.name)
        )
        external_references = self._external_references(tables, rows_by_table)
        digest_payload = {
            "export_version": EXPORT_VERSION,
            "athlete_id": str(athlete_id),
            "tables": [item.model_dump(mode="json") for item in exported_tables],
            "external_references": [item.model_dump(mode="json") for item in external_references],
        }
        canonical = json.dumps(digest_payload, sort_keys=True, separators=(",", ":"))
        digest = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
        table_counts = {item.table_name: len(item.rows) for item in exported_tables}
        return AthleteDataExport(
            generated_at=instant,
            athlete_id=athlete_id,
            tables=exported_tables,
            external_references=external_references,
            manifest=AthleteExportManifest(
                record_count=sum(table_counts.values()),
                table_counts=table_counts,
                content_digest=digest,
            ),
        )

    def _rows(self, table: Table, predicate: ColumnElement[bool]) -> tuple[dict[str, object], ...]:
        return tuple(
            dict(row)
            for row in self.session.execute(select(table).where(predicate)).mappings().all()
        )

    @staticmethod
    def _merge(
        rows_by_table: dict[str, dict[tuple[object, ...], dict[str, object]]],
        table: Table,
        rows: tuple[dict[str, object], ...],
    ) -> bool:
        destination = rows_by_table.setdefault(table.name, {})
        before = len(destination)
        for row in rows:
            destination[_primary_key(table, row)] = row
        return len(destination) != before

    @staticmethod
    def _export_table(
        table: Table, rows: dict[tuple[object, ...], dict[str, object]]
    ) -> AthleteExportTable:
        encoded = tuple(
            sorted(
                ({key: _json_value(value) for key, value in row.items()} for row in rows.values()),
                key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
            )
        )
        return AthleteExportTable(
            table_name=table.name,
            primary_key_columns=tuple(column.name for column in table.primary_key.columns),
            rows=encoded,
        )

    @staticmethod
    def _external_references(
        tables: tuple[Table, ...],
        rows_by_table: dict[str, dict[tuple[object, ...], dict[str, object]]],
    ) -> tuple[AthleteExportExternalReference, ...]:
        references: dict[tuple[str, str, str, str, str], AthleteExportExternalReference] = {}
        for table in tables:
            source_rows = rows_by_table.get(table.name, {})
            for foreign_key in table.foreign_keys:
                target_rows = rows_by_table.get(foreign_key.column.table.name, {})
                included_target_values = {
                    row[foreign_key.column.name] for row in target_rows.values()
                }
                for row in source_rows.values():
                    value = row[foreign_key.parent.name]
                    if value is None or value in included_target_values:
                        continue
                    encoded = _json_value(value)
                    key = (
                        table.name,
                        foreign_key.parent.name,
                        foreign_key.column.table.name,
                        foreign_key.column.name,
                        json.dumps(encoded, sort_keys=True),
                    )
                    references[key] = AthleteExportExternalReference(
                        source_table=table.name,
                        source_column=foreign_key.parent.name,
                        target_table=foreign_key.column.table.name,
                        target_column=foreign_key.column.name,
                        target_value=encoded,
                    )
        return tuple(references[key] for key in sorted(references))
