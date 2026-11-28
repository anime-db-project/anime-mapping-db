"""Collect only explicit ID pairs from Anime365's public metadata catalogue."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import httpx

from anime_mapping_db.crawler_policy import PacedClient, load_policy, user_agent
from anime_mapping_db.database import MappingRecord
from anime_mapping_db.importers.native_ids import enrich_native_ids, positive_id

_PAGE_SIZE = 500


def fetch_catalog(client: httpx.Client, url: str) -> list[dict]:
    paced = PacedClient(client, load_policy("anime365"))
    cursor = 0
    rows = []
    while True:
        response = paced.get(
            url,
            params={
                "limit": _PAGE_SIZE,
                "afterId": cursor,
                "order": "id",
                "fields": "id,myAnimeListId",
            },
        )
        payload = response.json()
        if (
            not isinstance(payload, dict)
            or "error" in payload
            or not isinstance(payload.get("data"), list)
            or len(payload["data"]) > _PAGE_SIZE
        ):
            raise ValueError("Invalid Anime365 catalogue response")
        items = payload["data"]
        # A short page is not necessarily the last page. Require the empty terminator.
        if not items:
            break
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Invalid Anime365 catalogue row")
            native = positive_id(item.get("id"))
            if native is None or int(native) <= cursor:
                raise ValueError("Anime365 cursor did not advance strictly")
            if "myAnimeListId" not in item:
                raise ValueError("Anime365 external ID field missing")
            raw_mal = item["myAnimeListId"]
            mal = positive_id(raw_mal)
            if mal is None and raw_mal not in (None, 0, "0", ""):
                raise ValueError("Invalid Anime365 MAL ID")
            cursor = int(native)
            rows.append({"id": native, "mal": mal})
    if not rows or not any(row["mal"] for row in rows):
        raise ValueError("Anime365 returned no usable external IDs")
    logging.info(
        "Anime365 catalogue: %d series, %d with MAL, %d requests",
        len(rows),
        sum(row["mal"] is not None for row in rows),
        paced.requests,
    )
    return rows


def download_anime365(url: str, target: Path, *, timeout: float) -> None:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={"Accept": "application/json", "User-Agent": user_agent()},
    ) as client:
        rows = fetch_catalog(client, url)
    target.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")


def import_anime365_enrichment(
    path: Path, runtime_conn: sqlite3.Connection
) -> Iterator[MappingRecord]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Empty Anime365 snapshot")
    yield from enrich_native_ids(
        rows, runtime_conn, namespace="anime365", lineage="anime365-native", weight=85
    )
