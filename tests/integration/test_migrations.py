from pathlib import Path
from uuid import uuid4

import pytest
from agas_api.settings import get_settings
from agas_domain.persistence.models import Base
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_baseline_migration_matches_current_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = Path(f".test-migration-{uuid4().hex}.db").resolve()
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("AGAS_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = create_engine(database_url)
    try:
        command.upgrade(config, "head")

        inspector = inspect(engine)
        expected_tables = set(Base.metadata.tables)
        actual_tables = set(inspector.get_table_names())
        assert actual_tables == expected_tables | {"alembic_version"}
        assert "intensity_targets" in {
            column["name"] for column in inspector.get_columns("session_prescriptions")
        }
        assert "session_template_id" in {
            column["name"] for column in inspector.get_columns("planned_sessions")
        }
        assert "session_item_executions" in actual_tables
        assert "laterality" in {column["name"] for column in inspector.get_columns("exercises")}
        assert "allowed_lateralities" in {
            column["name"] for column in inspector.get_columns("stimulus_requirements")
        }
        assert "laterality_weight" in {
            column["name"] for column in inspector.get_columns("exercise_resolver_policies")
        }
        assert "allow_partial_exercise_resolution" in {
            column["name"] for column in inspector.get_columns("weekly_scheduling_policies")
        }
        strategy_columns = {
            column["name"] for column in inspector.get_columns("long_range_strategies")
        }
        assert "supersedes_strategy_id" in strategy_columns
        assert "triggering_block_review_id" in strategy_columns

        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()
        get_settings.cache_clear()
        database_path.unlink(missing_ok=True)
