from __future__ import annotations

import json
import logging
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterator

import httpx

from anime_mapping_db.anchors import _union_find_components
from anime_mapping_db.database import MappingRecord

_PAGE_SIZE = 50
_MAX_PAGES = 500


def _id(value: object) -> str | None:
    if type(value) not in (str, int):
        return None
    text = str(value)
    if not text.isascii() or not text.isdecimal() or text.startswith("0"):
        return None
    return text


def _external_id(row: dict, field: str) -> str | None:
    value = row.get(field)
    return _id(value.get("id")) if isinstance(value, dict) else None


def _fetch_catalog(client: httpx.Client, url: str) -> list[dict]:
    rows: dict[str, dict] = {}
    expected_total = None
    expected_pages = None
    for page in range(1, _MAX_PAGES + 1):
        if page > 1:
            time.sleep(1.0)
        response = client.get(
            url,
            params={
                "page": page,
                "limit": _PAGE_SIZE,
                "include": "id,mal.id,shikimori.id",
                "f[sorting]": "FRESH_AT_ASC",
            },
        )
        # Do not continue on 403/429 or publish a partial snapshot.
        response.raise_for_status()
        payload = response.json()
        items = payload["data"]
        pagination = payload["meta"]["pagination"]
        total = pagination["total"]
        pages = pagination["total_pages"]
        if (
            type(total) is not int
            or type(pages) is not int
            or not 0 < total <= _MAX_PAGES * _PAGE_SIZE
            or pages != (total + _PAGE_SIZE - 1) // _PAGE_SIZE
            or pagination["current_page"] != page
            or not isinstance(items, list)
            or len(items) != min(_PAGE_SIZE, total - (page - 1) * _PAGE_SIZE)
        ):
            raise ValueError("Invalid AniLiberty catalog pagination")
        if expected_total is None:
            expected_total, expected_pages = total, pages
        if total != expected_total or pages != expected_pages:
            raise ValueError("AniLiberty catalog changed during pagination")
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Invalid AniLiberty catalog row")
            release = _id(item.get("id"))
            if release is None or release in rows:
                raise ValueError("Invalid or duplicate AniLiberty release ID")
            rows[release] = {
                "id": release,
                "mal": _external_id(item, "mal"),
                "shikimori": _external_id(item, "shikimori"),
            }
        if page == pages:
            if len(rows) != total:
                raise ValueError("Incomplete AniLiberty catalog")
            result = sorted(rows.values(), key=lambda row: int(row["id"]))
            if not any(row["mal"] or row["shikimori"] for row in result):
                raise ValueError("AniLiberty catalog contains no external IDs")
            logging.info(
                "AniLiberty catalog: %d releases, %d MAL, %d Shikimori",
                len(result),
                sum(row["mal"] is not None for row in result),
                sum(row["shikimori"] is not None for row in result),
            )
            return result
    raise ValueError("AniLiberty catalog exceeded page limit")


def download_aniliberty(url: str, target: Path, *, timeout: float) -> None:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={
            "Accept": "application/json",
            "User-Agent": "anime-db-project/anime-mapping-db",
        },
    ) as client:
        rows = _fetch_catalog(client, url)
    # Canonical ID-only snapshot: scores, metadata and volatile URLs never enter it.
    target.write_text(
        json.dumps(rows, ensure_ascii=True, separators=(",", ":")),
        encoding="utf-8",
    )


def import_aniliberty_enrichment(
    path: Path, runtime_conn: sqlite3.Connection
) -> Iterator[MappingRecord]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    components = _union_find_components(runtime_conn)
    membership = {
        node: group for group, nodes in enumerate(components) for node in nodes
    }
    lookup = {
        (provider, external): node
        for node, provider, external in runtime_conn.execute(
            "SELECT id, provider, external_id FROM nodes "
            "WHERE provider IN ('mal', 'shikimori', 'aniliberty')"
        )
    }
    conflicts = set(
        runtime_conn.execute("SELECT source_node, target_provider FROM conflicts")
    )
    occupied = {
        membership[node]
        for (provider, _external), node in lookup.items()
        if provider == "aniliberty"
    }
    claims: dict[int, set[str]] = defaultdict(set)
    reverse: dict[str, set[int]] = defaultdict(set)
    candidates = []
    for row in rows:
        release = _id(row.get("id"))
        if release is None:
            continue
        anchors = []
        for provider in ("mal", "shikimori"):
            external = _id(row.get(provider))
            node = lookup.get((provider, external))
            if node is not None:
                anchors.append((provider, external, node))
        groups = {membership[node] for _, _, node in anchors}
        for group in groups:
            claims[group].add(release)
            reverse[release].add(group)
        if len(groups) != 1:
            continue
        group = next(iter(groups))
        if group in occupied or ("aniliberty", release) in lookup:
            continue
        if any((node, "aniliberty") in conflicts for node in components[group]):
            continue
        if any(
            (node, other) in conflicts
            for provider, _, node in anchors
            for other, _, _ in anchors
            if provider != other
        ):
            continue
        candidates.append((release, group, anchors))

    emitted = set()
    for release, group, anchors in candidates:
        if len(claims[group]) != 1 or len(reverse[release]) != 1:
            continue
        for provider, external, _node in anchors:
            key = (release, provider, external)
            if key in emitted:
                continue
            emitted.add(key)
            yield MappingRecord(
                record_key=f"{release}:{provider}:{external}",
                ids={"aniliberty": (release,), provider: (external,)},
                evidence_group="aniliberty-native",
                weight=85,
            )
