"""Permission-gated Annict work ID cross-references."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import httpx

from anime_mapping_db.crawler_policy import PacedClient, load_policy, user_agent
from anime_mapping_db.database import MappingRecord
from anime_mapping_db.native_ids import enrich_native_ids, positive_id

_URL = "https://api.annict.com/v1/works"
_PAGE_SIZE = 50


def fetch_catalog(client: httpx.Client, url: str) -> list[dict]:
    paced = PacedClient(client, load_policy("annict_api"))
    rows = []
    page = 1
    total = None
    last = 0
    while True:
        payload = paced.get(
            url,
            params={
                "fields": "id,mal_anime_id",
                "sort_id": "asc",
                "page": page,
                "per_page": _PAGE_SIZE,
            },
        ).json()
        if not isinstance(payload, dict):
            raise ValueError("Invalid Annict response")
        items = payload.get("works")
        count = payload.get("total_count")
        if (
            not isinstance(items, list)
            or len(items) > _PAGE_SIZE
            or type(count) is not int
            or count <= 0
            or (total is not None and count != total)
            or "next_page" not in payload
        ):
            raise ValueError("Invalid Annict catalogue pagination")
        total = count
        for item in items:
            if not isinstance(item, dict) or "mal_anime_id" not in item:
                raise ValueError("Invalid Annict ID projection")
            native = positive_id(item.get("id"))
            if native is None or int(native) <= last:
                raise ValueError("Annict work IDs did not advance")
            raw = item["mal_anime_id"]
            mal = positive_id(raw)
            if mal is None and raw not in (None, "", 0, "0"):
                raise ValueError("Invalid Annict MAL ID")
            rows.append({"id": native, "mal": mal})
            last = int(native)
        next_page = payload["next_page"]
        if next_page is None:
            if len(rows) != total:
                raise ValueError("Incomplete Annict catalogue")
            break
        if next_page != page + 1 or len(items) != _PAGE_SIZE or len(rows) >= total:
            raise ValueError("Invalid Annict next page")
        page += 1
    if not any(row["mal"] for row in rows):
        raise ValueError("Annict catalogue has no MAL references")
    logging.info("Annict catalogue: %d works, %d requests", len(rows), paced.requests)
    return rows


def download_annict(url: str, target: Path, *, timeout: float) -> None:
    token = os.environ.get("MAPPINGS_ANNICT_ACCESS_TOKEN", "").strip()
    if not token:
        raise ValueError("Annict requires a provider-issued read-only token")
    if url != _URL:
        raise ValueError("Unexpected Annict endpoint")
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={
            "Accept": "application/json",
            "User-Agent": user_agent(),
            "Authorization": f"Bearer {token}",
        },
    ) as client:
        rows = fetch_catalog(client, url)
    target.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")


def import_annict_api(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Empty Annict snapshot")
    yield from enrich_native_ids(
        rows, conn, namespace="annict", lineage="annict-native", weight=85
    )
