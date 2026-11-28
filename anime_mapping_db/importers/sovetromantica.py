from __future__ import annotations

import json
import logging
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator

from anime_mapping_db.anchors import _union_find_components
from anime_mapping_db.database import MappingRecord

_TARGET = "sovetromantica"


def _positive_id(value: object) -> str:
    if type(value) not in (str, int):
        raise ValueError("Expected a numeric SovetRomantica/Shikimori ID")
    text = str(value)
    if not text.isascii() or not text.isdecimal() or text.startswith("0"):
        raise ValueError("Invalid SovetRomantica/Shikimori ID")
    return text


def _pairs(path: Path) -> set[tuple[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Empty or invalid SovetRomantica snapshot")
    pairs = set()
    for row in payload:
        if not isinstance(row, dict):
            raise ValueError("Invalid SovetRomantica row")
        pairs.add(
            (_positive_id(row.get("idSR")), _positive_id(row.get("idShikimori")))
        )
    return pairs


def normalize_snapshot(path: Path) -> None:
    pairs = _pairs(path)
    path.write_text(
        json.dumps(
            [{"idSR": sr, "idShikimori": shiki} for sr, shiki in sorted(pairs)],
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )


def import_sovetromantica_enrichment(
    path: Path, runtime_conn: sqlite3.Connection
) -> Iterator[MappingRecord]:
    pairs = _pairs(path)
    components = _union_find_components(runtime_conn)
    membership = {
        node: group for group, nodes in enumerate(components) for node in nodes
    }
    lookup = {
        (provider, external): node
        for node, provider, external in runtime_conn.execute(
            "SELECT id, provider, external_id FROM nodes "
            "WHERE provider IN ('shikimori', 'sovetromantica')"
        )
    }
    conflicts = set(
        runtime_conn.execute("SELECT source_node, target_provider FROM conflicts")
    )
    occupied = {
        membership[node]
        for (provider, _), node in lookup.items()
        if provider == _TARGET
    }
    claims: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    group_claims: dict[int, set[str]] = defaultdict(set)
    for sr, shiki in pairs:
        claims[sr].add(shiki)
        reverse[shiki].add(sr)
        node = lookup.get(("shikimori", shiki))
        if node is not None:
            group_claims[membership[node]].add(sr)

    outcomes: Counter[str] = Counter()
    for sr, shiki in sorted(pairs):
        if len(claims[sr]) != 1 or len(reverse[shiki]) != 1:
            outcomes["ambiguous_source"] += 1
            continue
        node = lookup.get(("shikimori", shiki))
        if node is None:
            outcomes["unknown_anchor"] += 1
            continue
        group = membership[node]
        if len(components[group]) < 2:
            outcomes["unconfirmed_anchor"] += 1
            continue
        if len(group_claims[group]) != 1:
            outcomes["ambiguous_group"] += 1
            continue
        if group in occupied or (_TARGET, sr) in lookup:
            outcomes["existing_namespace"] += 1
            continue
        if any((member, _TARGET) in conflicts for member in components[group]):
            outcomes["directional_conflict"] += 1
            continue
        outcomes["accepted"] += 1
        yield MappingRecord(
            record_key=f"{sr}:{shiki}",
            ids={_TARGET: (sr,), "shikimori": (shiki,)},
            evidence_group="sovetromantica-api-historical",
            weight=80,
        )
    logging.info("SovetRomantica matching outcomes: %s", dict(sorted(outcomes.items())))
