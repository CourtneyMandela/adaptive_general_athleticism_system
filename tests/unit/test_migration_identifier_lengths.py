from importlib import import_module

from sqlalchemy.dialects.postgresql import dialect


def test_initial_planning_index_names_fit_postgresql_identifier_limit() -> None:
    migration = import_module(
        "migrations.versions.a4b6c8d0e2f4_add_initial_planning_context_artifacts"
    )
    index_names = [
        *migration._DRAFT_INDEX_NAMES.values(),
        *migration._CANDIDATE_INDEX_NAMES.values(),
        *migration._REVIEW_INDEX_NAMES.values(),
    ]

    assert len(index_names) == 16
    assert len(index_names) == len(set(index_names))
    assert all(len(index_name) <= dialect().max_identifier_length for index_name in index_names)
