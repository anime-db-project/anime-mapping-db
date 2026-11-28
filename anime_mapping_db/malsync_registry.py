"""Inventory MALSync public adapters without executing upstream JavaScript.

Fixture expectations are candidates, never accepted mapping evidence. The
inventory is a collection artifact, separate from release input fingerprints.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from anime_mapping_db.malsync_authorized import PROVIDERS as AUTHORIZED_PROVIDERS

_UPSTREAM = "https://github.com/MALSync/MALSync"
_NON_CATALOGUES = {"emby", "jellyfin", "plex", "myanimelist"}
_ACTIVE = {"Crunchyroll", "Netflix"}
_NATIVE = {"Anime365", "Docchi", "AnimeLib"}
_OPTIONAL = {"ADKami", "Aniyan", "AniDream", "Aninexus"}
# Dated audit observations, not automatic availability or permission checks.
_AUDIT = {
    "AnimeUnity": (
        "access_unavailable",
        "HTTP 403 on robots.txt; no authorized bulk catalogue verified.",
    ),
    "AnimeKO": (
        "catalogue_discovery_only",
        "126 catalogue pages observed; no explicit external IDs in checked catalogue/overview.",
    ),
    "FireAnime": (
        "permission_required",
        "Public API reference limits use to private non-commercial integrations.",
    ),
    "AnimeOnsen": (
        "access_unavailable",
        "HTTP 403 on robots.txt; no authorized bulk export confirmed.",
    ),
    "AnimeWho": (
        "access_unavailable",
        "Domain lookup failed during audit; explicit page references in adapter only.",
    ),
    "Animeworld": (
        "permission_required",
        "Explicit MAL/AniList page links verified; site asks users not to scrape.",
    ),
    "AniKoto": (
        "episode_scoped_reference",
        "MAL reference is selected per episode; no full-title equivalence established.",
    ),
    "HinataSoul": (
        "page_reference_only",
        "MAL reference in overview adapter; no bulk ID export verified.",
    ),
    "WitAnime": (
        "access_unavailable",
        "TLS connection failed; overview MAL link exists in adapter.",
    ),
    "tioanime": (
        "page_reference_only",
        "Jikan link in page markup; no verified bulk ID export.",
    ),
    "YummyAni": (
        "permission_required",
        "Prepared paginated native collector; personal-use terms and application token required.",
    ),
    "AnimeStream": (
        "permission_required",
        "Public catalogue crawl allowed but backend API excluded in robots.txt; season reference is derived.",
    ),
    "Gojo": (
        "access_unavailable",
        "Adapter domain failed DNS lookup; no verified separate ID catalogue.",
    ),
    "Miruro": (
        "page_reference_only",
        "Overview adapter exposes MAL/AniList links; internal API excluded in robots.txt.",
    ),
    "animepahe": (
        "page_reference_only",
        "Adapter exposes numeric MAL, AniList and Kitsu metadata; bulk ID export not verified.",
    ),
    "Kaguya": (
        "existing_namespace_alias",
        "Adapter identifier is AniList aniId; no separate native title ID established.",
    ),
}
_IMPORT = re.compile(r"from\s+['\"](\./[^'\"]+/main)['\"]")
_NAME = re.compile(r"\bname:\s*['\"]([^'\"]+)['\"]")
_ID = re.compile(r"\bgetIdentifier\s*(?:\(|:)")
_ANCHOR = re.compile(r"\bgetMalUrl\s*(?:\(|:)")
_DATABASE = re.compile(r"\bdatabase:\s*['\"]([^'\"]+)['\"]")


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


class _Pages(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.section = ""
        self.heading = False
        self.row = False
        self.cell = False
        self.cells: list[str] = []
        self.current = ""
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h1":
            self.heading = True
            self.section = ""
        elif tag == "tr":
            self.row = True
            self.cells = []
        elif tag == "td" and self.row:
            self.cell = True
            self.current = ""

    def handle_data(self, data: str) -> None:
        if self.heading:
            self.section += data
        if self.cell:
            self.current += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self.heading = False
        elif tag == "td" and self.cell:
            self.cells.append(self.current.strip())
            self.cell = False
        elif tag == "tr":
            if self.section.strip() == "Anime" and len(self.cells) == 6:
                self.rows.append(self.cells)
            self.row = False


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _anchor(url: object) -> tuple[str, str] | None:
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return None
    if parts.scheme != "https" or parts.username or parts.password:
        return None
    providers = {
        "myanimelist.net": "mal",
        "www.myanimelist.net": "mal",
        "anilist.co": "anilist",
        "www.anilist.co": "anilist",
    }
    match = re.fullmatch(r"/anime/([1-9][0-9]*)(?:/[^/]*)?/?", parts.path)
    if host in providers and match:
        return providers[host], match[1]
    return None


def _implementations(root: Path) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = defaultdict(list)
    for layout in ("pages", "pages-chibi"):
        registry = root / "src" / layout / "pages.ts"
        text = registry.read_text(encoding="utf-8-sig")
        for relative in _IMPORT.findall(text):
            path = registry.parent / (relative + ".ts")
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError("MALSync adapter path escapes checkout")
            code = path.read_text(encoding="utf-8-sig")
            fixtures = _read_json(path.with_name("tests.json"))
            names = {_key(path.parent.name)}
            match = _NAME.search(code)
            if match:
                names.add(_key(match[1]))
            if isinstance(fixtures.get("title"), str):
                names.add(_key(fixtures["title"]))
            candidates = set()
            cases = fixtures.get("testCases", [])
            if not isinstance(cases, list):
                cases = []
            for case in cases:
                if not isinstance(case, dict):
                    continue
                expected = case.get("expected", {})
                if not isinstance(expected, dict):
                    continue
                anchor = _anchor(expected.get("malUrl"))
                identifier = expected.get("identifier")
                if (
                    anchor
                    and type(identifier) in (str, int)
                    and str(identifier).strip()
                    and len(str(identifier)) <= 256
                ):
                    candidates.add((str(identifier), *anchor))
            database = _DATABASE.search(code)
            entry = {
                "implementation": path.relative_to(root).as_posix(),
                "engine": "chibi" if layout == "pages-chibi" else "legacy",
                "identifier_hook": bool(_ID.search(code)),
                "external_id_hook": bool(_ANCHOR.search(code)),
                "database_key": database[1] if database else None,
                "test_cases": len(cases),
                "tests_enabled": fixtures.get("enabled", True),
                "fixture_candidates": [
                    {"id": key, "anchor_provider": provider, "anchor_id": external}
                    for key, provider, external in sorted(candidates)
                ],
            }
            for name in names:
                if name:
                    result[name].append(entry)
    return result


def inventory(root: Path, revision: str) -> dict:
    pages = _Pages()
    pages.feed((root / "pages.md").read_text(encoding="utf-8-sig"))
    if not pages.rows:
        raise ValueError("MALSync anime support table is empty")
    implementations = _implementations(root)
    sources = []
    seen = set()
    for row in pages.rows:
        name = row[0]
        key = _key(name)
        if not key or key in seen:
            raise ValueError(f"Duplicate or invalid MALSync source: {name}")
        seen.add(key)
        entries = implementations.get(key, [])
        if key in _NON_CATALOGUES:
            status = "not_global_catalogue"
        elif name in _ACTIVE:
            status = "partial_release_import"
        elif name in _NATIVE:
            status = "native_catalog_collector"
        elif name in _OPTIONAL:
            status = "authorized_snapshot_only"
        elif key in AUTHORIZED_PROVIDERS:
            status = "authorized_snapshot_only"
        elif name in _AUDIT:
            status = _AUDIT[name][0]
        elif any(entry["external_id_hook"] for entry in entries):
            status = "explicit_hook_requires_verification"
        elif entries:
            status = "identifier_only_or_indirect"
        else:
            status = "implementation_unresolved"
        sources.append(
            {
                "name": name,
                "key": key,
                "languages": row[1],
                "upstream_database_support": "heavy_check_mark" in row[4],
                "status": status,
                "audit": (
                    {"checked_on": "2026-11-28", "reason": _AUDIT[name][1]}
                    if name in _AUDIT
                    else None
                ),
                "implementations": entries,
            }
        )
    return {
        "upstream": _UPSTREAM,
        "revision": revision,
        "anime_integrations": len(sources),
        "status_counts": dict(Counter(source["status"] for source in sources)),
        "sources": sources,
        "fixture_candidates_are_release_evidence": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = inventory(args.upstream, args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"## MALSync source inventory ({report['anime_integrations']} anime integrations)"
    )
    print()
    print(f"Upstream revision: `{args.revision}`")
    print()
    print("| Site | Status | Adapter | Fixture ID candidates |")
    print("| --- | --- | --- | ---: |")
    for source in report["sources"]:
        entries = source["implementations"]
        engines = ", ".join(sorted({entry["engine"] for entry in entries})) or "—"
        count = sum(len(entry["fixture_candidates"]) for entry in entries)
        name = source["name"].replace("|", "\\|")
        print(f"| {name} | {source['status']} | {engines} | {count} |")


if __name__ == "__main__":
    main()
