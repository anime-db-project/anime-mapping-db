"""Read explicit public MALSync season overrides, not tracking heuristics."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator

from anime_mapping_db.anchors import _union_find_components
from anime_mapping_db.database import MappingRecord

_TARGETS = {
    "malsync_crunchyroll": "crunchyroll_season",
    "malsync_netflix": "netflix_season",
}


def _id(value: object, provider: str) -> str:
    if type(value) not in (str, int):
        raise ValueError(f"Invalid {provider} ID")
    text = str(value)
    pattern = r"[A-Z0-9]{8,32}" if provider == "crunchyroll_season" else r"[1-9][0-9]*"
    if not re.fullmatch(pattern, text):
        raise ValueError(f"Invalid {provider} ID")
    return text


def _pairs(path: Path, importer: str) -> set[tuple[str, str]]:
    provider = _TARGETS[importer]
    payload = json.loads(path.read_text(encoding="utf-8"))
    pairs = set()
    if isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict):
                raise ValueError("Invalid MALSync snapshot row")
            pairs.add((_id(row["id"], provider), _id(row["mal"], "mal")))
    else:
        if not isinstance(payload, dict):
            raise ValueError("Invalid MALSync catalog")
        if importer == "malsync_crunchyroll":
            seasons = (
                (key, value)
                for series in payload["series"].values()
                for key, value in series["seasons"].items()
            )
        else:
            seasons = payload["seasons"].items()
        for key, value in seasons:
            override = value.get("override")
            if not isinstance(override, dict) or "malId" not in override:
                continue
            # Partial episode routes or renumbered seasons are not title IDs.
            if override.get("offset", 0) != 0 or "season" in override:
                continue
            pairs.add((_id(key, provider), _id(override["malId"], "mal")))
    if not pairs:
        raise ValueError("No eligible explicit MALSync overrides")
    return pairs


def normalize_snapshot(path: Path, importer: str) -> None:
    path.write_text(
        json.dumps(
            [{"id": key, "mal": mal} for key, mal in sorted(_pairs(path, importer))],
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


def _enrich(
    path: Path, runtime_conn: sqlite3.Connection, importer: str
) -> Iterator[MappingRecord]:
    provider = _TARGETS[importer]
    pairs = _pairs(path, importer)
    components = _union_find_components(runtime_conn)
    membership = {
        node: group for group, nodes in enumerate(components) for node in nodes
    }
    lookup = {
        (namespace, external): node
        for node, namespace, external in runtime_conn.execute(
            "SELECT id, provider, external_id FROM nodes WHERE provider IN ('mal', ?)",
            (provider,),
        )
    }
    conflicts = set(
        runtime_conn.execute("SELECT source_node, target_provider FROM conflicts")
    )
    occupied = {
        membership[node]
        for (namespace, _), node in lookup.items()
        if namespace == provider
    }
    claims: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    for season, mal in pairs:
        claims[season].add(mal)
        reverse[mal].add(season)

    outcomes: Counter[str] = Counter()
    for season, mal in sorted(pairs):
        if len(claims[season]) != 1 or len(reverse[mal]) != 1:
            outcomes["ambiguous_source"] += 1
            continue
        node = lookup.get(("mal", mal))
        if node is None:
            outcomes["unknown_anchor"] += 1
            continue
        group = membership[node]
        if len(components[group]) < 2:
            outcomes["unconfirmed_anchor"] += 1
            continue
        if group in occupied or (provider, season) in lookup:
            outcomes["existing_namespace"] += 1
            continue
        if any((member, provider) in conflicts for member in components[group]):
            outcomes["directional_conflict"] += 1
            continue
        outcomes["accepted"] += 1
        yield MappingRecord(
            record_key=f"{season}:{mal}",
            ids={provider: (season,), "mal": (mal,)},
            evidence_group="malsync-explicit-season-override",
            weight=80,
        )
    logging.info("MALSync %s outcomes: %s", provider, dict(sorted(outcomes.items())))


def import_malsync_crunchyroll(
    path: Path, runtime_conn: sqlite3.Connection
) -> Iterator[MappingRecord]:
    yield from _enrich(path, runtime_conn, "malsync_crunchyroll")


def import_malsync_netflix(
    path: Path, runtime_conn: sqlite3.Connection
) -> Iterator[MappingRecord]:
    yield from _enrich(path, runtime_conn, "malsync_netflix")
