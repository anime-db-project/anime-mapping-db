"""Audit the scope of explicitly authorized Kodik catalogue identifiers.

Material IDs are deliberately not imported into the title identity graph.
Only aggregate diagnostic counts are exported, not the provider's catalogue.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

from anime_mapping_db.crawler_policy import PacedClient, load_policy, user_agent
from anime_mapping_db.native_ids import positive_id

_URL = "https://kodik-api.com/list"
_PAGE_SIZE = 100
_MAX_PAGES = 10


def next_cursor(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 8192:
        raise ValueError("Invalid Kodik continuation")
    try:
        parts = urlsplit(value)
        fields = parse_qs(parts.query, max_num_fields=32)
        if (
            parts.scheme != "https"
            or parts.netloc != "kodik-api.com"
            or parts.path != "/list"
            or parts.fragment
        ):
            raise ValueError("Unexpected Kodik continuation endpoint")
        cursors = fields.get("next", [])
        if len(cursors) != 1 or not re.fullmatch(r"[A-Za-z0-9_+/=-]{1,4096}", cursors[0]):
            raise ValueError("Invalid Kodik continuation cursor")
        return cursors[0]
    except ValueError:
        raise ValueError("Invalid Kodik continuation") from None


def project(row: dict) -> tuple[str, str | None, str | None, str | None, str | None]:
    material = row.get("id")
    kind = row.get("type")
    prefix = {"anime": "movie-", "anime-serial": "serial-"}.get(kind)
    if (
        prefix is None
        or not isinstance(material, str)
        or not material.startswith(prefix)
        or positive_id(material.removeprefix(prefix)) is None
    ):
        raise ValueError("Unexpected Kodik anime material ID or type")
    translation = row.get("translation")
    translation_id = (
        positive_id(translation.get("id")) if isinstance(translation, dict) else None
    )
    imdb = row.get("imdb_id")
    return (
        material,
        positive_id(row.get("shikimori_id")),
        positive_id(row.get("kinopoisk_id")),
        imdb if isinstance(imdb, str) and re.fullmatch(r"tt[0-9]+", imdb) else None,
        translation_id,
    )


def audit(client: httpx.Client, token: str, *, max_pages: int = _MAX_PAGES) -> dict:
    if not token.strip() or not 1 <= max_pages <= _MAX_PAGES:
        raise ValueError("Kodik audit requires own token and bounded page count")
    paced = PacedClient(client, load_policy("kodik_audit"))
    rows: dict[str, set[tuple]] = defaultdict(set)
    cursor = None
    seen_cursors = set()
    seen_pages = 0
    for _ in range(max_pages):
        form = {
            "token": token,
            "types": "anime,anime-serial",
            "limit": str(_PAGE_SIZE),
            "with_material_data": "false",
        }
        if cursor:
            form["next"] = cursor
        try:
            payload = paced.post(_URL, data=form).json()
        except (httpx.HTTPError, ValueError):
            # Never surface upstream response text or a URL containing a token.
            raise ValueError("Kodik catalogue request failed") from None
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("results"), list)
            or len(payload["results"]) > _PAGE_SIZE
            or "next_page" not in payload
        ):
            raise ValueError("Invalid Kodik catalogue response")
        seen_pages += 1
        for row in payload["results"]:
            if not isinstance(row, dict):
                raise ValueError("Invalid Kodik catalogue row")
            material, *ids = project(row)
            rows[material].add(tuple(ids))
        cursor = next_cursor(payload["next_page"])
        if cursor is None:
            break
        if cursor in seen_cursors or not payload["results"]:
            raise ValueError("Kodik catalogue cursor did not advance")
        seen_cursors.add(cursor)

    by_title: dict[str, set[str]] = defaultdict(set)
    kinopoisk = set()
    imdb = set()
    translations = set()
    conflicting = 0
    for material, claims in rows.items():
        if len(claims) != 1:
            conflicting += 1
            continue
        shikimori, kp, imdb_id, translation = next(iter(claims))
        if shikimori:
            by_title[shikimori].add(material)
        if kp:
            kinopoisk.add(kp)
        if imdb_id:
            imdb.add(imdb_id)
        if translation:
            translations.add(translation)
    return {
        "audit_only": True,
        "sample_pages": seen_pages,
        "requests": paced.requests,
        "end_of_catalogue_reached": cursor is None,
        "distinct_materials": len(rows),
        "conflicting_materials": conflicting,
        "materials_with_shikimori": sum(map(len, by_title.values())),
        "distinct_shikimori_ids": len(by_title),
        "shikimori_ids_with_multiple_materials": sum(
            len(materials) > 1 for materials in by_title.values()
        ),
        "distinct_kinopoisk_ids": len(kinopoisk),
        "distinct_imdb_ids": len(imdb),
        "distinct_translation_ids": len(translations),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("MAPPINGS_KODIK_API_TOKEN", "").strip()
    if not token or os.environ.get("MAPPINGS_KODIK_PERMISSION_CONFIRMED") != "1":
        parser.error("Kodik audit requires own authorized token and permission")
    with httpx.Client(
        timeout=30.0,
        follow_redirects=False,
        headers={"User-Agent": user_agent(), "Accept": "application/json"},
    ) as client:
        report = audit(client, token)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = json.dumps(report, indent=2) + "\n"
    args.output.write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
