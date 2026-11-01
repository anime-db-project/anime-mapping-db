"""Build and consume the anime-db-project cross-database mapping dataset."""

from anime_mapping_db.database import (
    SCHEMA_VERSION,
    MappingBuildStats,
    MappingDatabaseBuilder,
    MappingRecord,
)
from anime_mapping_db.resolver import MappingResolver

__all__ = [
    "SCHEMA_VERSION",
    "MappingBuildStats",
    "MappingDatabaseBuilder",
    "MappingRecord",
    "MappingResolver",
]
