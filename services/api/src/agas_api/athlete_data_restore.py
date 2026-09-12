from __future__ import annotations

import argparse
import base64
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from agas_domain.persistence.models import Base
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Table, and_, func, insert, select
from sqlalchemy.orm import Session

from agas_api.athlete_data_export import (
    EXPORT_VERSION,
    AthleteDataExport,
    AthleteDataExporter,
    AthleteExportExternalReference,
    AthleteExportTable,
    calculate_export_content_digest,
)
from agas_api.database import database_session

RESTORE_VERSION = "athlete-data-clean-restore@1.0.0"
SUPPORTED_EXPORT_VERSIONS = frozenset({"athlete-data-export@1.0.0", EXPORT_VERSION})


class AthleteDataRestoreBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    table_name: str | None = None


class AthleteDataRestorePreflight(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    restore_version: str = RESTORE_VERSION
    export_version: str
    athlete_id: UUID
    content_digest: str
    record_count: int
    external_reference_count: int
    target_has_no_athletes: bool
    can_restore: bool
    blockers: tuple[AthleteDataRestoreBlocker, ...]


class AthleteDataRestoreResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    restore_version: str = RESTORE_VERSION
    athlete_id: UUID
    content_digest: str
    owner_account_id: UUID
    inserted_table_counts: dict[str, int]
    round_trip_digest_verified: bool


class AthleteDataRestoreBlockedError(ValueError):
    def __init__(self, preflight: AthleteDataRestorePreflight) -> None:
        self.preflight = preflight
        super().__init__("athlete data restore preflight is blocked")


def _blocker(code: str, message: str, table_name: str | None = None) -> AthleteDataRestoreBlocker:
    return AthleteDataRestoreBlocker(code=code, message=message, table_name=table_name)


def _reference_key(
    source_table: str,
    source_column: str,
    target_table: str,
    target_column: str,
    target_value: object,
) -> tuple[str, str, str, str, str]:
    return (
        source_table,
        source_column,
        target_table,
        target_column,
        json.dumps(target_value, sort_keys=True, separators=(",", ":")),
    )


def _archive_reference_key(
    reference: AthleteExportExternalReference,
) -> tuple[str, str, str, str, str]:
    return _reference_key(
        reference.source_table,
        reference.source_column,
        reference.target_table,
        reference.target_column,
        reference.target_value,
    )


def _decode_value(column: Column[Any], value: object) -> object:
    if value is None:
        return None
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        return value
    if python_type is UUID:
        return UUID(str(value))
    if python_type is datetime:
        if not isinstance(value, str):
            raise ValueError("datetime value must be an ISO-8601 string")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("datetime value must include a timezone")
        return parsed.astimezone(UTC)
    if python_type is date:
        if not isinstance(value, str):
            raise ValueError("date value must be an ISO-8601 string")
        return date.fromisoformat(value)
    if python_type is Decimal:
        return Decimal(str(value))
    if python_type is bytes:
        if not isinstance(value, str):
            raise ValueError("binary value must be base64 text")
        return base64.urlsafe_b64decode(value.encode("ascii"))
    return value


def _decoded_row(table: Table, row: Mapping[str, object]) -> dict[str, object]:
    return {name: _decode_value(table.c[name], value) for name, value in row.items()}


def _row_pk(table: Table, row: dict[str, object]) -> tuple[object, ...]:
    return tuple(row[column.name] for column in table.primary_key.columns)


def _athlete_owned_table_names() -> set[str]:
    owned = {"athletes"}
    owned.update(table.name for table in Base.metadata.tables.values() if "athlete_id" in table.c)
    changed = True
    while changed:
        changed = False
        for table in Base.metadata.tables.values():
            if table.name in owned:
                continue
            if any(foreign_key.column.table.name in owned for foreign_key in table.foreign_keys):
                owned.add(table.name)
                changed = True
    return owned


def _ordered_rows(
    table: Table, rows: tuple[dict[str, object], ...]
) -> tuple[dict[str, object], ...]:
    """Order self-referencing rows so archived predecessors are inserted first."""

    pending = list(rows)
    emitted: list[dict[str, object]] = []
    emitted_keys: set[tuple[object, ...]] = set()
    self_foreign_keys = tuple(
        foreign_key
        for foreign_key in table.foreign_keys
        if foreign_key.column.table.name == table.name
    )
    while pending:
        ready: list[dict[str, object]] = []
        for row in pending:
            dependencies: set[tuple[object, ...]] = set()
            for foreign_key in self_foreign_keys:
                value = row[foreign_key.parent.name]
                if value is None:
                    continue
                dependencies.update(
                    _row_pk(table, candidate)
                    for candidate in rows
                    if candidate[foreign_key.column.name] == value
                )
            if dependencies.issubset(emitted_keys):
                ready.append(row)
        if not ready:
            raise ValueError(f"{table.name} contains cyclic self-references")
        for row in ready:
            pending.remove(row)
            emitted.append(row)
            emitted_keys.add(_row_pk(table, row))
    return tuple(emitted)


class AthleteDataRestorer:
    """Validate and restore one owner archive only into an athlete-empty database."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def preflight(
        self,
        archive: AthleteDataExport,
        *,
        owner_issuer: str,
        owner_subject: str,
    ) -> AthleteDataRestorePreflight:
        blockers: list[AthleteDataRestoreBlocker] = []
        issuer = owner_issuer.strip()
        subject = owner_subject.strip()
        if not issuer or not subject:
            blockers.append(
                _blocker("owner_identity_missing", "owner issuer and subject are required")
            )
        if archive.export_version not in SUPPORTED_EXPORT_VERSIONS:
            blockers.append(
                _blocker(
                    "unsupported_export_version",
                    f"unsupported archive version {archive.export_version}",
                )
            )
        calculated_digest = calculate_export_content_digest(
            archive.athlete_id,
            archive.tables,
            archive.external_references,
            export_version=archive.export_version,
        )
        if archive.manifest.content_digest != calculated_digest:
            blockers.append(_blocker("digest_mismatch", "archive content digest does not match"))

        entries = self._table_entries(archive.tables, blockers)
        decoded_rows = self._decode_rows(entries, archive.athlete_id, blockers)
        actual_counts = {name: len(entry.rows) for name, entry in entries.items()}
        if archive.manifest.record_count != sum(actual_counts.values()):
            blockers.append(_blocker("record_count_mismatch", "manifest record count is incorrect"))
        if archive.manifest.table_counts != actual_counts:
            blockers.append(_blocker("table_count_mismatch", "manifest table counts are incorrect"))

        athlete_rows = decoded_rows.get("athletes", ())
        if len(athlete_rows) != 1 or (
            athlete_rows and athlete_rows[0].get("id") != archive.athlete_id
        ):
            blockers.append(
                _blocker(
                    "athlete_identity_mismatch",
                    "archive must contain exactly its declared athlete row",
                    "athletes",
                )
            )

        expected_references = self._expected_external_references(decoded_rows)
        archive_references = {_archive_reference_key(item) for item in archive.external_references}
        if expected_references != archive_references:
            blockers.append(
                _blocker(
                    "external_reference_mismatch",
                    "external references do not exactly describe missing parent rows",
                )
            )

        owned_tables = _athlete_owned_table_names()
        for reference in archive.external_references:
            if reference.target_table in owned_tables:
                blockers.append(
                    _blocker(
                        "external_athlete_reference",
                        "athlete-owned dependencies must be inside the archive",
                        reference.source_table,
                    )
                )

        self._validate_row_reachability(decoded_rows, blockers)
        owner_account_id = self._owner_account_id(decoded_rows, blockers)
        target_has_no_athletes = (
            self.session.scalar(select(func.count()).select_from(Base.metadata.tables["athletes"]))
            == 0
        )
        if not target_has_no_athletes:
            blockers.append(
                _blocker(
                    "target_contains_athletes",
                    "restore is permitted only when the target athlete store is empty",
                    "athletes",
                )
            )

        self._validate_target_identity(owner_account_id, issuer, subject, blockers)
        self._validate_external_targets(archive.external_references, owner_account_id, blockers)
        self._validate_target_collisions(decoded_rows, blockers)

        return AthleteDataRestorePreflight(
            export_version=archive.export_version,
            athlete_id=archive.athlete_id,
            content_digest=archive.manifest.content_digest,
            record_count=archive.manifest.record_count,
            external_reference_count=len(archive.external_references),
            target_has_no_athletes=target_has_no_athletes,
            can_restore=not blockers,
            blockers=tuple(blockers),
        )

    def restore(
        self,
        archive: AthleteDataExport,
        *,
        owner_issuer: str,
        owner_subject: str,
        restored_at: datetime | None = None,
    ) -> AthleteDataRestoreResult:
        preflight = self.preflight(archive, owner_issuer=owner_issuer, owner_subject=owner_subject)
        if not preflight.can_restore:
            raise AthleteDataRestoreBlockedError(preflight)
        instant = restored_at or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("restore time must include a timezone")
        entries = {entry.table_name: entry for entry in archive.tables}
        decoded_rows = {
            name: tuple(_decoded_row(Base.metadata.tables[name], row) for row in entry.rows)
            for name, entry in entries.items()
        }
        blockers: list[AthleteDataRestoreBlocker] = []
        owner_account_id = self._owner_account_id(decoded_rows, blockers)
        if owner_account_id is None or blockers:
            raise RuntimeError("validated archive owner identity became unavailable")

        inserted_counts: dict[str, int] = {}
        with self.session.begin_nested():
            account_table = Base.metadata.tables["accounts"]
            existing_account = self.session.scalar(
                select(account_table.c.id).where(account_table.c.id == owner_account_id)
            )
            if existing_account is None:
                self.session.execute(
                    insert(account_table).values(
                        id=owner_account_id,
                        schema_version="1.0.0",
                        created_at=instant,
                        issuer=owner_issuer.strip(),
                        subject=owner_subject.strip(),
                    )
                )
            for table in Base.metadata.sorted_tables:
                rows = decoded_rows.get(table.name, ())
                if not rows:
                    continue
                ordered = _ordered_rows(table, rows)
                for row in ordered:
                    self.session.execute(insert(table).values(**row))
                inserted_counts[table.name] = len(ordered)
            self.session.flush()
            restored = AthleteDataExporter(self.session).export(
                archive.athlete_id, generated_at=instant
            )
            if restored.manifest.content_digest != archive.manifest.content_digest:
                raise RuntimeError("restored athlete data failed the round-trip digest check")

        return AthleteDataRestoreResult(
            athlete_id=archive.athlete_id,
            content_digest=archive.manifest.content_digest,
            owner_account_id=owner_account_id,
            inserted_table_counts=inserted_counts,
            round_trip_digest_verified=True,
        )

    @staticmethod
    def _table_entries(
        tables: tuple[AthleteExportTable, ...],
        blockers: list[AthleteDataRestoreBlocker],
    ) -> dict[str, AthleteExportTable]:
        entries: dict[str, AthleteExportTable] = {}
        for entry in tables:
            if entry.table_name in entries:
                blockers.append(
                    _blocker(
                        "duplicate_table",
                        "archive table appears more than once",
                        entry.table_name,
                    )
                )
            entries[entry.table_name] = entry
        return entries

    @staticmethod
    def _decode_rows(
        entries: dict[str, AthleteExportTable],
        athlete_id: UUID,
        blockers: list[AthleteDataRestoreBlocker],
    ) -> dict[str, tuple[dict[str, object], ...]]:
        decoded_rows: dict[str, tuple[dict[str, object], ...]] = {}
        for name, entry in entries.items():
            table = Base.metadata.tables.get(name)
            if table is None:
                blockers.append(
                    _blocker("unknown_table", "archive table is not in this schema", name)
                )
                continue
            expected_pk = tuple(column.name for column in table.primary_key.columns)
            if entry.primary_key_columns != expected_pk:
                blockers.append(
                    _blocker("primary_key_mismatch", "primary key metadata differs", name)
                )
            expected_columns = {column.name for column in table.columns}
            seen_keys: set[tuple[object, ...]] = set()
            decoded: list[dict[str, object]] = []
            for row in entry.rows:
                if set(row) != expected_columns:
                    blockers.append(
                        _blocker("column_mismatch", "row columns differ from schema", name)
                    )
                    continue
                try:
                    converted = _decoded_row(table, row)
                    key = _row_pk(table, converted)
                except (TypeError, ValueError) as error:
                    blockers.append(_blocker("invalid_value", str(error), name))
                    continue
                if key in seen_keys:
                    blockers.append(
                        _blocker("duplicate_primary_key", "duplicate row identity", name)
                    )
                seen_keys.add(key)
                decoded.append(converted)
                if "athlete_id" in table.c and converted["athlete_id"] != athlete_id:
                    blockers.append(
                        _blocker("cross_athlete_row", "row belongs to another athlete", name)
                    )
            decoded_rows[name] = tuple(decoded)
        return decoded_rows

    @staticmethod
    def _expected_external_references(
        decoded_rows: dict[str, tuple[dict[str, object], ...]],
    ) -> set[tuple[str, str, str, str, str]]:
        expected: set[tuple[str, str, str, str, str]] = set()
        for table_name, rows in decoded_rows.items():
            table = Base.metadata.tables[table_name]
            for foreign_key in table.foreign_keys:
                targets = decoded_rows.get(foreign_key.column.table.name, ())
                included = {row[foreign_key.column.name] for row in targets}
                for row in rows:
                    value = row[foreign_key.parent.name]
                    if value is None or value in included:
                        continue
                    encoded = str(value) if isinstance(value, UUID) else value
                    expected.add(
                        _reference_key(
                            table_name,
                            foreign_key.parent.name,
                            foreign_key.column.table.name,
                            foreign_key.column.name,
                            encoded,
                        )
                    )
        return expected

    @staticmethod
    def _validate_row_reachability(
        decoded_rows: dict[str, tuple[dict[str, object], ...]],
        blockers: list[AthleteDataRestoreBlocker],
    ) -> None:
        reachable: dict[str, set[tuple[object, ...]]] = {}
        for name, rows in decoded_rows.items():
            table = Base.metadata.tables[name]
            if name == "athletes" or "athlete_id" in table.c:
                reachable[name] = {_row_pk(table, row) for row in rows}
        changed = True
        while changed:
            changed = False
            for name, rows in decoded_rows.items():
                table = Base.metadata.tables[name]
                destination = reachable.setdefault(name, set())
                for row in rows:
                    key = _row_pk(table, row)
                    if key in destination:
                        continue
                    if any(
                        any(
                            parent[foreign_key.column.name] == row[foreign_key.parent.name]
                            and _row_pk(foreign_key.column.table, parent)
                            in reachable.get(foreign_key.column.table.name, set())
                            for parent in decoded_rows.get(foreign_key.column.table.name, ())
                        )
                        for foreign_key in table.foreign_keys
                    ):
                        destination.add(key)
                        changed = True
        for name, rows in decoded_rows.items():
            table = Base.metadata.tables[name]
            if len(reachable.get(name, set())) != len(rows):
                blockers.append(
                    _blocker(
                        "unreachable_row",
                        "archive contains a row outside the athlete dependency graph",
                        table.name,
                    )
                )

    @staticmethod
    def _owner_account_id(
        decoded_rows: dict[str, tuple[dict[str, object], ...]],
        blockers: list[AthleteDataRestoreBlocker],
    ) -> UUID | None:
        ownerships = decoded_rows.get("athlete_ownerships", ())
        if len(ownerships) != 1 or not isinstance(
            ownerships[0].get("account_id") if ownerships else None, UUID
        ):
            blockers.append(
                _blocker(
                    "owner_lineage_missing",
                    "archive must contain exactly one athlete ownership record",
                    "athlete_ownerships",
                )
            )
            return None
        return UUID(str(ownerships[0]["account_id"]))

    def _validate_target_identity(
        self,
        owner_account_id: UUID | None,
        issuer: str,
        subject: str,
        blockers: list[AthleteDataRestoreBlocker],
    ) -> None:
        if owner_account_id is None or not issuer or not subject:
            return
        accounts = Base.metadata.tables["accounts"]
        by_id = (
            self.session.execute(select(accounts).where(accounts.c.id == owner_account_id))
            .mappings()
            .one_or_none()
        )
        by_identity = (
            self.session.execute(
                select(accounts).where(
                    and_(accounts.c.issuer == issuer, accounts.c.subject == subject)
                )
            )
            .mappings()
            .one_or_none()
        )
        if by_id is not None and (by_id["issuer"] != issuer or by_id["subject"] != subject):
            blockers.append(
                _blocker(
                    "owner_account_conflict",
                    "archived owner account ID belongs to another identity",
                    "accounts",
                )
            )
        if by_identity is not None and by_identity["id"] != owner_account_id:
            blockers.append(
                _blocker(
                    "owner_identity_conflict",
                    "target owner identity has a different account ID",
                    "accounts",
                )
            )

    def _validate_external_targets(
        self,
        references: Iterable[AthleteExportExternalReference],
        owner_account_id: UUID | None,
        blockers: list[AthleteDataRestoreBlocker],
    ) -> None:
        checked: set[tuple[str, str, str]] = set()
        for reference in references:
            key = (
                reference.target_table,
                reference.target_column,
                json.dumps(reference.target_value, sort_keys=True),
            )
            if key in checked:
                continue
            checked.add(key)
            table = Base.metadata.tables.get(reference.target_table)
            if table is None or reference.target_column not in table.c:
                continue
            try:
                value = _decode_value(table.c[reference.target_column], reference.target_value)
            except (TypeError, ValueError):
                continue
            if (
                table.name == "accounts"
                and reference.target_column == "id"
                and value == owner_account_id
            ):
                continue
            exists = self.session.scalar(
                select(func.count())
                .select_from(table)
                .where(table.c[reference.target_column] == value)
            )
            if not exists:
                blockers.append(
                    _blocker(
                        "missing_external_reference",
                        f"required {reference.target_column}={reference.target_value!s} is absent",
                        table.name,
                    )
                )

    def _validate_target_collisions(
        self,
        decoded_rows: dict[str, tuple[dict[str, object], ...]],
        blockers: list[AthleteDataRestoreBlocker],
    ) -> None:
        for name, rows in decoded_rows.items():
            table = Base.metadata.tables[name]
            for row in rows:
                predicate = and_(
                    *(column == row[column.name] for column in table.primary_key.columns)
                )
                if self.session.scalar(select(func.count()).select_from(table).where(predicate)):
                    blockers.append(
                        _blocker(
                            "target_record_collision",
                            "target already contains an archived record identity",
                            name,
                        )
                    )
                    break


def _load_archive(path: Path) -> AthleteDataExport:
    return AthleteDataExport.model_validate_json(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preflight or restore one AGAS athlete archive into an empty athlete store."
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--owner-issuer", required=True)
    parser.add_argument("--owner-subject", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply only after a successful preflight; omission performs a read-only check.",
    )
    parser.add_argument(
        "--expected-digest",
        help="Required with --apply; must exactly match the preflighted archive digest.",
    )
    arguments = parser.parse_args()
    if arguments.expected_digest and not arguments.apply:
        parser.error("--expected-digest is used only with --apply")
    exit_code = 0
    try:
        archive = _load_archive(arguments.archive)
        if arguments.apply and arguments.expected_digest != archive.manifest.content_digest:
            parser.error("--apply requires the archive's exact --expected-digest value")
        with database_session() as session:
            restorer = AthleteDataRestorer(session)
            if arguments.apply:
                result: BaseModel = restorer.restore(
                    archive,
                    owner_issuer=arguments.owner_issuer,
                    owner_subject=arguments.owner_subject,
                )
                session.commit()
            else:
                result = restorer.preflight(
                    archive,
                    owner_issuer=arguments.owner_issuer,
                    owner_subject=arguments.owner_subject,
                )
                if not result.can_restore:
                    exit_code = 2
    except AthleteDataRestoreBlockedError as error:
        parser.error(json.dumps(error.preflight.model_dump(mode="json"), sort_keys=True))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
