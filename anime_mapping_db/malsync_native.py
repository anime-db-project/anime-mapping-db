"""Native metadata collectors identified during the MALSync adapter audit."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from anime_mapping_db.crawler_policy import PacedClient, load_policy, user_agent
from anime_mapping_db.database import MappingRecord
from anime_mapping_db.native_ids import enrich_native_ids, positive_id


def slug_id(value: object) -> str | None:
    if (
        isinstance(value, str)
        and 0 < len(value) <= 256
        and value not in {".", ".."}
        and all(c.isprintable() and not c.isspace() for c in value)
        and not any(c in value for c in "/\\?#%")
    ):
        return value
    return None


def adkami_id(value: object) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[1-9]\d*-[1-9]\d*-1", value, re.ASCII):
        return value
    return None


def _external(value: object) -> str | None:
    if value is None or (type(value) in (str, int) and value in (0, "0", "")):
        return None
    result = positive_id(value)
    if result is None:
        raise ValueError("Invalid external ID")
    return result


def _link(value: object, hosts: set[str], path: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("Invalid external URL")
    parts = urlsplit(value)
    if (
        parts.scheme != "https"
        or parts.hostname not in hosts
        or parts.username
        or parts.password
    ):
        raise ValueError("Unexpected external URL")
    match = re.fullmatch(path, parts.path)
    if not match:
        raise ValueError("Unexpected external ID path")
    return match[1]


def _write(target: Path, rows: list[dict]) -> None:
    if not rows or not any(
        row.get("mal") or row.get("anilist") or row.get("shikimori") for row in rows
    ):
        raise ValueError("Catalogue contains no usable external IDs")
    target.write_text(
        json.dumps(
            sorted(rows, key=lambda row: (row["id"], json.dumps(row, sort_keys=True))),
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def fetch_docchi(client: httpx.Client, url: str) -> list[dict]:
    payload = PacedClient(client, load_policy("docchi")).get(url).json()
    if not isinstance(payload, list) or not payload:
        raise ValueError("Invalid Docchi catalogue")
    rows = []
    for item in payload:
        if not isinstance(item, dict) or "mal_id" not in item:
            raise ValueError("Invalid Docchi row")
        native = slug_id(item.get("slug"))
        if native is None:
            raise ValueError("Invalid Docchi slug")
        rows.append({"id": native, "mal": _external(item["mal_id"])})
    logging.info("Docchi catalogue: %d records", len(rows))
    return rows


def fetch_animelib(client: httpx.Client, url: str) -> list[dict]:
    paced = PacedClient(client, load_policy("animelib"))
    rows = []
    seen = set()
    per_page = None
    page = 1
    while True:
        payload = paced.get(
            url,
            params={
                "page": page,
                "site_id[]": 5,
                "sort_by": "name",
                "sort_type": "asc",
            },
        ).json()
        items = payload["data"]
        meta = payload["meta"]
        links = payload["links"]
        size = meta["per_page"]
        if (
            not isinstance(items, list)
            or meta["current_page"] != page
            or type(size) is not int
            or not 1 <= size <= 1000
            or len(items) > size
            or "next" not in links
            or (per_page is not None and per_page != size)
        ):
            raise ValueError("Invalid AnimeLib pagination")
        per_page = size
        if links["next"] and len(items) != size:
            raise ValueError("Incomplete intermediate AnimeLib page")
        for item in items:
            if not isinstance(item, dict) or item.get("model") != "anime":
                raise ValueError("Unexpected AnimeLib row")
            native = positive_id(item.get("id"))
            if native is None or native in seen:
                raise ValueError("Invalid or duplicate AnimeLib ID")
            if "anilist_id" not in item and "anilist_href" not in item:
                raise ValueError("AnimeLib external ID projection missing")
            seen.add(native)
            ani = _external(item.get("anilist_id"))
            ani_url = _link(
                item.get("anilist_href"),
                {"anilist.co", "www.anilist.co"},
                r"/anime/([1-9]\d*)(?:/[^/]*)?/?",
            )
            if ani and ani_url and ani != ani_url:
                raise ValueError("Contradictory AnimeLib AniList ID")
            shiki = _link(
                item.get("shikimori_href"),
                {"shikimori.one", "shikimori.me", "shikimori.org", "shikimori.io"},
                r"/animes/[az]?([1-9]\d*)(?:-[^/]*)?/?",
            )
            rows.append({"id": native, "anilist": ani or ani_url, "shikimori": shiki})
        if not links["next"]:
            break
        page += 1
    logging.info("AnimeLib catalogue: %d records in %d pages", len(rows), page)
    return rows


def _download(
    url: str,
    target: Path,
    timeout: float,
    fetch: Callable[[httpx.Client, str], list[dict]],
    headers: dict[str, str] | None = None,
) -> None:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={
            "Accept": "application/json",
            "User-Agent": user_agent(),
            **(headers or {}),
        },
    ) as client:
        rows = fetch(client, url)
    _write(target, rows)


def download_docchi(url: str, target: Path, *, timeout: float) -> None:
    _download(url, target, timeout, fetch_docchi)


def download_animelib(url: str, target: Path, *, timeout: float) -> None:
    _download(
        url,
        target,
        timeout,
        fetch_animelib,
        {"Site-Id": "5", "Referer": "https://v5.animelib.org/"},
    )


def _read(path: Path) -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(rows, list)
        or not rows
        or not all(isinstance(row, dict) for row in rows)
    ):
        raise ValueError("Invalid native ID snapshot")
    return rows


def normalize_adkami(path: Path) -> None:
    # Accept an authorized export of the syncData objects, not scraped media.
    rows = []
    for item in _read(path):
        native = adkami_id(item.get("id"))
        if native is None:
            raise ValueError("Invalid ADKami season ID")
        rows.append(
            {
                "id": native,
                "mal": _external(item.get("mal_id", item.get("mal"))),
                "anilist": _external(item.get("anilist_id", item.get("anilist"))),
            }
        )
    _write(path, rows)


def import_docchi(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    yield from enrich_native_ids(
        _read(path),
        conn,
        namespace="docchi",
        lineage="docchi-native",
        native_id=slug_id,
        weight=85,
    )


def import_animelib(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    yield from enrich_native_ids(
        _read(path), conn, namespace="animelib", lineage="animelib-native", weight=85
    )


def import_adkami(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    yield from enrich_native_ids(
        _read(path),
        conn,
        namespace="adkami_season",
        lineage="adkami-native",
        native_id=adkami_id,
        weight=85,
    )


_SYNCDATA_VALIDATORS = {
    "aniyan": positive_id,
    "anidream": slug_id,
    "aninexus": positive_id,
}


def normalize_syncdata(path: Path, provider: str) -> None:
    validate = _SYNCDATA_VALIDATORS[provider]
    rows = []
    for item in _read(path):
        native = validate(item.get("anime_id", item.get("id")))
        if native is None:
            raise ValueError(f"Invalid {provider} native ID")
        mal_values = {
            value
            for key in ("myanimelist_id", "mal_id", "mal")
            if (value := _external(item.get(key))) is not None
        }
        ani_values = {
            value
            for key in ("anilist_id", "anilist")
            if (value := _external(item.get(key))) is not None
        }
        if len(mal_values) > 1 or len(ani_values) > 1:
            raise ValueError(f"Contradictory {provider} snapshot row")
        rows.append(
            {
                "id": native,
                "mal": next(iter(mal_values), None),
                "anilist": next(iter(ani_values), None),
            }
        )
    _write(path, rows)


def _import_syncdata(
    path: Path, conn: sqlite3.Connection, provider: str
) -> Iterator[MappingRecord]:
    yield from enrich_native_ids(
        _read(path),
        conn,
        namespace=provider,
        lineage=f"{provider}-native",
        native_id=_SYNCDATA_VALIDATORS[provider],
        weight=85,
    )


def import_aniyan(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    yield from _import_syncdata(path, conn, "aniyan")


def import_anidream(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    yield from _import_syncdata(path, conn, "anidream")


def import_aninexus(path: Path, conn: sqlite3.Connection) -> Iterator[MappingRecord]:
    yield from _import_syncdata(path, conn, "aninexus")
