"""Count collected native IDs before the offline mapping graph is built."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from anime_mapping_db.native_ids import ANCHORS, positive_id

_NATIVE = {
    "aniliberty",
    "anime365",
    "docchi",
    "animelib",
    "adkami",
    "aniyan",
    "anidream",
    "aninexus",
}


def catalogue_stats(importer: str, path: Path | None) -> dict | None:
    if importer not in _NATIVE or path is None:
        return None
    rows = json.loads(path.read_text(encoding="utf-8"))
    # Snapshots are already projected and validated by their collectors.
    if not isinstance(rows, list):
        raise ValueError("Expected native ID snapshot")
    anchors: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        native = row["id"]
        if not isinstance(native, str) or not native:
            raise ValueError("Invalid native snapshot ID")
        anchors[native].update(
            provider for provider in ANCHORS if positive_id(row.get(provider))
        )
    with_id = sum(bool(values) for values in anchors.values())
    return {
        "rows": len(rows),
        "native_ids": len(anchors),
        "with_external_id": with_id,
        "without_external_id": len(anchors) - with_id,
        "with_anchor_by_namespace": {
            provider: sum(provider in values for values in anchors.values())
            for provider in ANCHORS
        },
    }
