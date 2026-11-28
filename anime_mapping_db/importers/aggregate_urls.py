"""Strict ID-only enrichment from AOD-style aggregate exports."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import ijson

from anime_mapping_db.anchors import _union_find_components
from anime_mapping_db.database import MappingRecord
from anime_mapping_db.importers.enrichment import (
    _anchor_enrichment_records,
    _find_trusted_pair,
    _runtime_graph_state,
)

_CORE = ("mal", "anilist", "anidb", "kitsu", "ann")
_PATTERNS = {
    "myanimelist.net": ("mal", r"/anime/([1-9][0-9]*)/?"),
    "anilist.co": ("anilist", r"/anime/([1-9][0-9]*)/?"),
    "anidb.net": ("anidb", r"/anime/([1-9][0-9]*)/?"),
    "kitsu.app": ("kitsu", r"/anime/([1-9][0-9]*)/?"),
    "kitsu.io": ("kitsu", r"/anime/([1-9][0-9]*)/?"),
    "anime-planet.com": ("animeplanet", r"/anime/([a-z0-9][a-z0-9_-]*)/?"),
    "anisearch.com": ("anisearch", r"/anime/([1-9][0-9]*)/?"),
    "livechart.me": ("livechart", r"/anime/([1-9][0-9]*)/?"),
    "simkl.com": ("simkl", r"/anime/([1-9][0-9]*)/?"),
    "animecountdown.com": ("animecountdown", r"/([1-9][0-9]*)/?"),
}
_PROVIDERS = tuple(sorted({v[0] for v in _PATTERNS.values()} | {"ann"}))


def parse_id(value: object) -> tuple[str, str] | None:
    if not isinstance(value, str):
        return None
    try:
        parts = urlsplit(value)
        if (
            parts.scheme != "https"
            or parts.username
            or parts.password
            or parts.port
            or parts.fragment
        ):
            return None
        if (
            parts.hostname == "animenewsnetwork.com"
            and parts.path == "/encyclopedia/anime.php"
        ):
            query = parse_qs(parts.query, max_num_fields=4)
            ids = query.get("id", [])
            if set(query) == {"id"} and len(ids) == 1:
                if re.fullmatch(r"[1-9][0-9]*", ids[0]):
                    return "ann", ids[0]
            return None
        entry = _PATTERNS.get(parts.hostname or "")
        if entry is None or parts.query:
            return None
        provider, pattern = entry
        matched = re.fullmatch(pattern, parts.path)
        return (provider, matched[1]) if matched else None
    except ValueError:
        return None


def _rows(path: Path) -> Iterator[dict[str, tuple[str, ...]]]:
    with path.open("rb") as handle:
        # Both raw exports and our canonical ID-only snapshots use data[].
        for item in ijson.items(handle, "data.item"):
            if not isinstance(item, dict):
                raise ValueError("Invalid AOD-style row")
            if "sources" in item:
                if not isinstance(item["sources"], list):
                    raise ValueError("Invalid source URL list")
                ids: dict[str, set[str]] = defaultdict(set)
                for url in item["sources"]:
                    pair = parse_id(url)
                    if pair:
                        ids[pair[0]].add(pair[1])
                yield {p: tuple(sorted(values)) for p, values in ids.items()}
            else:
                if not item or any(p not in _PROVIDERS for p in item):
                    raise ValueError("Invalid normalized aggregate row")
                normalized = {}
                for p, values in item.items():
                    pattern = (
                        r"[a-z0-9][a-z0-9_-]*" if p == "animeplanet" else r"[1-9][0-9]*"
                    )
                    if (
                        not isinstance(values, list)
                        or not values
                        or not all(
                            isinstance(v, str) and re.fullmatch(pattern, v)
                            for v in values
                        )
                    ):
                        raise ValueError("Invalid normalized aggregate ID")
                    normalized[p] = tuple(sorted(set(values)))
                yield normalized


def normalize_snapshot(path: Path) -> None:
    rows = {tuple(sorted(row.items())) for row in _rows(path) if row}
    if not rows or not any(len(row) >= 2 for row in rows):
        raise ValueError("Aggregate export has no usable ID rows")
    path.write_text(
        json.dumps(
            {"data": [dict(row) for row in sorted(rows)]},
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


def _enrich(
    path: Path, conn: sqlite3.Connection, *, lineage: str
) -> Iterator[MappingRecord]:
    lookup, edges, conflicts, existing = _runtime_graph_state(conn, _PROVIDERS)
    components = _union_find_components(conn)
    membership = {
        node: group for group, nodes in enumerate(components) for node in nodes
    }
    occupied: dict[int, set[str]] = defaultdict(set)
    for node, provider in conn.execute("SELECT id, provider FROM nodes"):
        occupied[membership[node]].add(provider)
    claims: dict[tuple[str, str], set[int]] = defaultdict(set)
    reverse: dict[tuple[int, str], set[str]] = defaultdict(set)
    candidates = {}
    row_count = 0
    for ids in _rows(path):
        row_count += 1
        known = {
            lookup[p, value]
            for p, values in ids.items()
            for value in values
            if (p, value) in lookup
        }
        groups = {membership[node] for node in known}
        # Register ambiguity even for rows that have only one known anchor.
        for group in groups:
            for p, values in ids.items():
                for value in values:
                    claims[p, value].add(group)
                    reverse[group, p].add(value)
        if len(groups) != 1 or any(len(values) != 1 for values in ids.values()):
            continue
        group = next(iter(groups))
        # Never add a missing ID if the row contradicts an already present
        # provider ID or a directional conflict in this component.
        if any(
            p in occupied[group] and (p, values[0]) not in lookup
            for p, values in ids.items()
        ):
            continue
        if any((node, p) in conflicts for node in known for p in ids):
            continue
        pair = _find_trusted_pair(
            {p: ids[p] for p in _CORE if p in ids},
            node_lookup=lookup,
            accepted_edges=edges,
            conflicts=conflicts,
        )
        if pair is None:
            continue
        for p, values in ids.items():
            target = values[0]
            if (p, target) in existing or p in occupied[group]:
                continue
            if any((node, p) in conflicts for node in components[group]):
                continue
            candidates.setdefault((group, p, target), pair)
    accepted = 0
    for (group, p, target), pair in sorted(candidates.items()):
        if claims[p, target] != {group} or reverse[group, p] != {target}:
            continue
        accepted += 1
        yield from _anchor_enrichment_records(
            key=f"{p}:{target}",
            trusted_pair=pair,
            targets={p: (target,)},
            existing_nodes=existing,
            group=lineage,
            weight=80,
        )
    logging.info("%s: %d rows, %d accepted missing IDs", lineage, row_count, accepted)


def import_animap_id(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    yield from _enrich(path, conn, lineage="animap-id-anchor")


def import_athanasso(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    yield from _enrich(path, conn, lineage="athanasso-anchor")
