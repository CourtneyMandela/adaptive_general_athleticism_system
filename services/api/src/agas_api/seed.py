from __future__ import annotations

import json

from agas_domain.persistence.repository import DomainRepository
from agas_seed_data import SeedCatalogImporter, load_seed_catalog

from agas_api.database import database_session


def main() -> None:
    catalog = load_seed_catalog()
    with database_session() as session:
        result = SeedCatalogImporter(DomainRepository(session)).import_catalog(catalog)
        session.commit()
    print(
        json.dumps(
            {
                "catalog_version": result.catalog_import.catalog_version,
                "content_digest": result.catalog_import.content_digest,
                "created": result.created,
                "inserted": {
                    "evidence_claims": result.inserted_evidence_claims,
                    "adaptations": result.inserted_adaptations,
                    "equipment": result.inserted_equipment,
                    "exercises": result.inserted_exercises,
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
