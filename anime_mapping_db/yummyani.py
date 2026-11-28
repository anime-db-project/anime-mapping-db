"""Permission-gated metadata-only collector for YummyAnime's documented API."""

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
from anime_mapping_db.malsync_native import slug_id
from anime_mapping_db.native_ids import enrich_native_ids, positive_id

_PAGE_SIZE = 100
_URL = "https://api.yani.tv/anime"


def _external_id(value: object) -> str | None:
    if value is None or (type(value) in (int, str) and value in (0, "0", "")):
        return None
    result = positive_id(value)
    if result is None:
        raise ValueError("Invalid YummyAnime external ID")
    return result


def fetch_catalog(client: httpx.Client, url: str) -> list[dict]:
    paced = PacedClient(client, load_policy("yummyani"))
    rows = []
    last_id = 0
    slugs = set()
    while True:
        payload = paced.get(
            url,
            params={
                "sort": "id",
                "sort_forward": "true",
                "limit": _PAGE_SIZE,
                "offset": len(rows),
            },
        ).json()
        if (
            not isinstance(payload, dict)
            or "error" in payload
            or not isinstance(payload.get("response"), list)
            or len(payload["response"]) > _PAGE_SIZE
        ):
            raise ValueError("Invalid YummyAnime response")
        items = payload["response"]
        if not items:
            break
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Invalid YummyAnime row")
            native = positive_id(item.get("anime_id"))
            slug = slug_id(item.get("anime_url"))
            if native is None or int(native) <= last_id:
                raise ValueError("YummyAnime catalogue order did not advance")
            if slug is None or slug in slugs:
                raise ValueError("Invalid or duplicate YummyAnime slug")
            remote = item.get("remote_ids")
            if not isinstance(remote, dict):
                raise ValueError("YummyAnime remote_ids projection missing")
            rows.append(
                {
                    "id": native,
                    "slug": slug,
                    "mal": _external_id(remote.get("myanimelist_id")),
                    "shikimori": _external_id(remote.get("shikimori_id")),
                }
            )
            last_id = int(native)
            slugs.add(slug)
    if not rows or not any(row["mal"] or row["shikimori"] for row in rows):
        raise ValueError("YummyAnime returned no usable external IDs")
    logging.info(
        "YummyAnime catalogue: %d titles, %d requests", len(rows), paced.requests
    )
    return rows


def download_yummyani(url: str, target: Path, *, timeout: float) -> None:
    token = os.environ.get("MAPPINGS_YUMMYANI_APPLICATION_TOKEN", "").strip()
    if not token:
        raise ValueError("YummyAnime requires an authorized application token")
    if url != _URL:
        raise ValueError("Unexpected YummyAnime API URL")
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={
            "Accept": "application/json",
            "User-Agent": user_agent(),
            "X-Application": token,
        },
    ) as client:
        rows = fetch_catalog(client, url)
    target.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")


def import_yummyani(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("Empty YummyAnime snapshot")
    numeric = list(
        enrich_native_ids(
            rows, conn, namespace="yummyani_id", lineage="yummyani-native", weight=85
        )
    )
    # Only expose the MALSync-compatible slug for numeric identities accepted
    # in this same snapshot. Both identifiers share the same evidence lineage.
    accepted = {record.ids["yummyani_id"][0] for record in numeric}
    yield from numeric
    yield from enrich_native_ids(
        ({**row, "id": row["slug"]} for row in rows if row["id"] in accepted),
        conn,
        namespace="yummyani",
        lineage="yummyani-native",
        native_id=slug_id,
        weight=85,
    )
