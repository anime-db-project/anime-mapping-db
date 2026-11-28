"""Shared conservative importer for explicit provider-native title references."""

from __future__ import annotations

import logging
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator

from anime_mapping_db.anchors import _union_find_components
from anime_mapping_db.database import MappingRecord

ANCHORS = ("mal", "anilist", "shikimori")


def positive_id(value: object) -> str | None:
    if type(value) not in (str, int):
        return None
    text = str(value)
    if not text.isascii() or not text.isdecimal() or text.startswith("0"):
        return None
    return text


def enrich_native_ids(
    rows: Iterable[dict],
    runtime_conn: sqlite3.Connection,
    *,
    namespace: str,
    lineage: str,
    weight: int = 80,
) -> Iterator[MappingRecord]:
    if namespace in ANCHORS:
        raise ValueError("Target namespace must not be an anchor")
    components = _union_find_components(runtime_conn)
    membership = {
        node: group for group, nodes in enumerate(components) for node in nodes
    }
    lookup = {
        (provider, external): node
        for node, provider, external in runtime_conn.execute(
            "SELECT id, provider, external_id FROM nodes "
            "WHERE provider IN ('mal', 'anilist', 'shikimori', ?)",
            (namespace,),
        )
    }
    group_ids: dict[tuple[int, str], set[str]] = defaultdict(set)
    for (provider, external), node in lookup.items():
        group_ids[membership[node], provider].add(external)
    conflicts = set(
        runtime_conn.execute("SELECT source_node, target_provider FROM conflicts")
    )
    # Include all claims, even rejected rows, when checking one-to-one identity.
    by_id: dict[str, set[tuple[tuple[str, str], ...]]] = defaultdict(set)
    by_group: dict[int, set[str]] = defaultdict(set)
    outcomes: Counter[str] = Counter()
    for row in rows:
        native = positive_id(row.get("id"))
        if native is None:
            raise ValueError("Invalid native ID")
        anchors = tuple(
            (provider, external)
            for provider in ANCHORS
            if (external := positive_id(row.get(provider))) is not None
        )
        by_id[native].add(anchors)
        for anchor in anchors:
            if anchor in lookup:
                by_group[membership[lookup[anchor]]].add(native)

    for native, claims in sorted(by_id.items()):
        if len(claims) != 1:
            outcomes["ambiguous_native"] += 1
            continue
        anchors = next(iter(claims))
        known = [(p, v, lookup[p, v]) for p, v in anchors if (p, v) in lookup]
        groups = {membership[node] for _, _, node in known}
        if len(groups) != 1:
            reason = "conflicting_groups" if groups else "unknown_anchor"
            outcomes[reason if anchors else "no_external_id"] += 1
            continue
        group = next(iter(groups))
        if len(components[group]) < 2:
            outcomes["unconfirmed_anchor"] += 1
            continue
        if any(group_ids.get((group, p), {v}) != {v} for p, v in anchors):
            outcomes["contradictory_anchor"] += 1
            continue
        if len(by_group[group]) != 1:
            outcomes["ambiguous_group"] += 1
            continue
        if (namespace, native) in lookup or (group, namespace) in group_ids:
            outcomes["existing_namespace"] += 1
            continue
        if any((node, namespace) in conflicts for node in components[group]) or any(
            (node, other) in conflicts
            for provider, _, node in known
            for other, _ in anchors
            if provider != other
        ):
            outcomes["directional_conflict"] += 1
            continue
        outcomes["accepted"] += 1
        for provider, external, _ in known:
            yield MappingRecord(
                record_key=f"{native}:{provider}:{external}",
                ids={namespace: (native,), provider: (external,)},
                evidence_group=lineage,
                weight=weight,
            )
    logging.info("%s matching outcomes: %s", namespace, dict(sorted(outcomes.items())))
