from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Iterator

import ijson

from anime_mapping_db.anchors import _union_find_components
from anime_mapping_db.database import MappingRecord
from anime_mapping_db.importers.enrichment import (
    _anchor_enrichment_records,
    _find_trusted_pair,
    _runtime_graph_state,
)

_ANCHORS = ("anilist", "mal", "anidb", "kitsu", "simkl")
_TARGETS = ("bangumi", "kitsu", "simkl")
_BANGUMI_CONFIDENCE = frozenset({"STRONG", "SEED", "OVERRIDE"})


def _id(raw: object) -> tuple[str, ...]:
    # IDs must be a single positive integer, never booleans, arrays or floats.
    if type(raw) not in (int, str):
        return ()
    value = str(raw)
    if not value.isascii() or not value.isdecimal() or value.startswith("0"):
        return ()
    return (value,)


def import_media_index_enrichment(
    path: Path, runtime_conn: sqlite3.Connection
) -> Iterator[MappingRecord]:
    lookup, edges, conflicts, existing = _runtime_graph_state(runtime_conn, _ANCHORS)
    components = _union_find_components(runtime_conn)
    membership = {
        node: index for index, nodes in enumerate(components) for node in nodes
    }
    occupied: dict[int, set[str]] = defaultdict(set)
    for node, provider in runtime_conn.execute("SELECT id, provider FROM nodes"):
        occupied[membership[node]].add(provider)

    # Validate the entire snapshot before yielding: two rows must not claim the
    # same new ID for different components, nor two IDs for one provider/component.
    claims: dict[tuple[str, str], set[int]] = defaultdict(set)
    reverse: dict[tuple[int, str], set[str]] = defaultdict(set)
    candidates = {}
    with path.open("rb") as handle:
        for key, row in ijson.kvitems(handle, ""):
            if not isinstance(row, dict) or not _id(key):
                continue
            ids = {provider: _id(row.get(provider)) for provider in _ANCHORS[1:]}
            ids["anilist"] = _id(key)
            known = {
                lookup[(provider, values[0])]
                for provider, values in ids.items()
                if values and (provider, values[0]) in lookup
            }
            groups = {membership[node] for node in known}
            if len(groups) != 1 or ("anilist", key) not in lookup:
                continue
            group = next(iter(groups))
            pair = _find_trusted_pair(
                ids, node_lookup=lookup, accepted_edges=edges, conflicts=conflicts
            )
            if pair is None:
                continue
            for provider in _TARGETS:
                target = _id(row.get(provider))
                if not target:
                    continue
                target_id = target[0]
                # Existing target IDs, competing IDs in an established component,
                # and directional conflicts are never reinterpreted.
                if (provider, target_id) in existing or provider in occupied[group]:
                    continue
                if any((node, provider) in conflicts for node in components[group]):
                    continue
                claims[(provider, target_id)].add(group)
                reverse[(group, provider)].add(target_id)
                if (
                    provider == "bangumi"
                    and row.get("bangumi_confidence") not in _BANGUMI_CONFIDENCE
                ):
                    continue
                candidates.setdefault((group, provider, target_id), (key, pair))

    for (group, provider, target_id), (key, pair) in sorted(candidates.items()):
        if len(claims[(provider, target_id)]) != 1:
            continue
        if len(reverse[(group, provider)]) != 1:
            continue
        yield from _anchor_enrichment_records(
            key=key,
            trusted_pair=pair,
            targets={provider: (target_id,)},
            existing_nodes=existing,
            group="media-index-anchor",
            weight=80,
        )
