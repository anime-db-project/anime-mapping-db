"""Explicit title IDs from MALSync-discovered metadata catalogues.

Only title-scoped catalogue records are supported here. No playback
URLs, test fixtures, episode-derived IDs or guessed title matches are imported.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from anime_mapping_db.database import MappingRecord
from anime_mapping_db.malsync_native import slug_id
from anime_mapping_db.native_ids import ANCHORS, enrich_native_ids, positive_id

PROVIDERS = (
    "animepahe",
    "animeunity",
    "animeonsen",
    "animewho",
    "hinatasoul",
    "witanime",
    "tioanime",
    "miruro",
)

INDEPENDENT_ID_REQUIRED = frozenset({"miruro"})


def _native(provider: str, value: object) -> str | None:
    if provider == "animepahe":
        # Numeric catalogue IDs only, not rotating playback session UUIDs.
        return positive_id(value)
    if provider == "animewho":
        if isinstance(value, str) and re.fullmatch(
            r"anime-[A-Za-z0-9][A-Za-z0-9_-]*", value
        ):
            return value
        return None
    if provider == "miruro":
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{20,64}", value):
            return value
        return None
    return slug_id(value) or positive_id(value)


def _rows(path: Path, provider: str) -> list[dict]:
    if provider not in PROVIDERS:
        raise ValueError("Unknown catalogue provider")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Expected a nonempty title-ID export")
    rows = []
    scope = "title"
    for item in payload:
        if not isinstance(item, dict) or item.get("scope") != scope:
            raise ValueError("Explicit matching identity scope required")
        if (
            provider in INDEPENDENT_ID_REQUIRED
            and item.get("native_id_verified") is not True
        ):
            raise ValueError("Independent stable native ID must be verified")
        native = _native(provider, item.get("id"))
        if native is None:
            raise ValueError("Invalid native title ID")
        row = {"id": native, "scope": scope}
        if provider in INDEPENDENT_ID_REQUIRED:
            row["native_id_verified"] = True
        for anchor, aliases in (
            ("mal", ("mal", "mal_id", "myanimelist_id")),
            ("anilist", ("anilist", "anilist_id")),
            ("shikimori", ("shikimori", "shikimori_id")),
            ("kitsu", ("kitsu", "kitsu_id")),
        ):
            values = set()
            for alias in aliases:
                value = item.get(alias)
                if value is None or (
                    type(value) in (str, int) and value in (0, "0", "")
                ):
                    continue
                normalized = positive_id(value)
                if normalized is None:
                    raise ValueError("Invalid explicit external ID")
                values.add(normalized)
            if len(values) > 1:
                raise ValueError("Conflicting external ID aliases")
            row[anchor] = next(iter(values), None)
        if provider in INDEPENDENT_ID_REQUIRED and native in (
            row["mal"],
            row["anilist"],
            row["shikimori"],
            row["kitsu"],
        ):
            raise ValueError("Potential reuse of external identifier")
        rows.append(row)
    if not any(
        row["mal"] or row["anilist"] or row["shikimori"] or row["kitsu"] for row in rows
    ):
        raise ValueError("No explicit supported external IDs in export")
    return sorted(rows, key=lambda row: (row["id"], json.dumps(row, sort_keys=True)))


def normalize_authorized(path: Path, provider: str) -> None:
    path.write_text(
        json.dumps(_rows(path, provider), sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _importer(provider: str):
    def importer(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
        yield from enrich_native_ids(
            _rows(path, provider),
            conn,
            namespace=provider,
            lineage=f"{provider}-native-metadata",
            native_id=lambda value: _native(provider, value),
            weight=85,
            anchor_providers=(*ANCHORS, "kitsu"),
        )

    return importer


AUTHORIZED_IMPORTERS = {provider: _importer(provider) for provider in PROVIDERS}
