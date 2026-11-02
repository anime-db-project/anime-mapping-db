"""Build and consume the anime-db-project cross-database mapping dataset."""

from anime_mapping_db.anchors import (
    ANCHOR_NAMESPACE,
    ANCHOR_SCHEMA_VERSION,
    AnchorBuildStats,
    AnchorIdentity,
    AnchorResolver,
    format_anchor,
    materialize_anchor_index,
    parse_anchor,
)
from anime_mapping_db.database import (
    SCHEMA_VERSION,
    MappingBuildStats,
    MappingDatabaseBuilder,
    MappingRecord,
)
from anime_mapping_db.resolver import MappingResolver

__all__ = [
    "ANCHOR_NAMESPACE",
    "ANCHOR_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "AnchorBuildStats",
    "AnchorIdentity",
    "AnchorResolver",
    "MappingBuildStats",
    "MappingDatabaseBuilder",
    "MappingRecord",
    "MappingResolver",
    "format_anchor",
    "materialize_anchor_index",
    "parse_anchor",
]
