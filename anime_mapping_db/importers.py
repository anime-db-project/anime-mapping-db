from __future__ import annotations

import csv
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, Iterator

import ijson

from anime_mapping_db.database import MappingRecord


def _values(value: Any, *, numeric: bool = False) -> tuple[str, ...]:
    if value is None:
        return ()
    raw_values: list[Any]
    if isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    elif isinstance(value, str) and "," in value:
        raw_values = value.split(",")
    else:
        raw_values = [value]

    result: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        text = str(raw or "").strip()
        if numeric and not text.isdigit():
            continue
        if text and text.casefold() not in {
            "none",
            "null",
            "unknown",
            "hentai",
            "-1",
            "0",
        }:
            key = text.casefold()
            if key not in seen:
                seen.add(key)
                result.append(text)
    return tuple(result)


def _record(
    key: str,
    ids: dict[str, tuple[str, ...]],
    *,
    group: str,
    weight: int,
) -> MappingRecord | None:
    cleaned = {provider: values for provider, values in ids.items() if values}
    if len(cleaned) < 2:
        return None
    return MappingRecord(
        record_key=key,
        ids=cleaned,
        evidence_group=group,
        weight=weight,
    )


def import_fribb(path: Path) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            anidb = _values(item.get("anidb_id"), numeric=True)
            if not anidb:
                continue

            manami = _record(
                f"{index}:manami",
                {
                    "anidb": anidb,
                    "anilist": _values(item.get("anilist_id"), numeric=True),
                    "mal": _values(item.get("mal_id"), numeric=True),
                    "kitsu": _values(item.get("kitsu_id")),
                    "animeplanet": _values(item.get("anime-planet_id")),
                    "anisearch": _values(item.get("anisearch_id")),
                    "ann": _values(item.get("animenewsnetwork_id")),
                    "livechart": _values(item.get("livechart_id")),
                    "simkl": _values(item.get("simkl_id")),
                    "animecountdown": _values(item.get("animecountdown_id")),
                },
                group="manami",
                weight=60,
            )
            if manami is not None:
                yield manami

            tmdb = item.get("themoviedb_id") or {}
            if not isinstance(tmdb, dict):
                tmdb = {}
            anime_lists = _record(
                f"{index}:anime-lists",
                {
                    "anidb": anidb,
                    "tvdb": _values(item.get("tvdb_id"), numeric=True),
                    "tmdb_tv": _values(tmdb.get("tv"), numeric=True),
                    "tmdb_movie": _values(tmdb.get("movie"), numeric=True),
                    "imdb": _values(item.get("imdb_id")),
                },
                group="anime-lists",
                weight=60,
            )
            if anime_lists is not None:
                yield anime_lists


def import_kometa(path: Path) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for anidb_key, item in ijson.kvitems(handle, ""):
            if not isinstance(item, dict):
                continue
            anidb = _values(anidb_key, numeric=True)
            if not anidb:
                continue

            groups = (
                (
                    "manami",
                    62,
                    {
                        "anidb": anidb,
                        "mal": _values(item.get("mal_id"), numeric=True),
                        "anilist": _values(item.get("anilist_id"), numeric=True),
                    },
                ),
                (
                    "anime-lists",
                    62,
                    {
                        "anidb": anidb,
                        "tvdb": _values(item.get("tvdb_id"), numeric=True),
                        "imdb": _values(item.get("imdb_id")),
                    },
                ),
                (
                    "animeaggregations",
                    68,
                    {
                        "anidb": anidb,
                        "tmdb_movie": _values(item.get("tmdb_movie_id"), numeric=True),
                        "tmdb_tv": _values(item.get("tmdb_show_id"), numeric=True),
                    },
                ),
            )
            for group, weight, ids in groups:
                record = _record(
                    f"{anidb_key}:{group}", ids, group=group, weight=weight
                )
                if record is not None:
                    yield record


def import_anime_lists(path: Path) -> Iterator[MappingRecord]:
    index = 0
    for _event, element in ET.iterparse(path, events=("end",)):
        if element.tag.rsplit("}", 1)[-1] != "anime":
            continue
        attrs = element.attrib
        anidb = _values(attrs.get("anidbid"), numeric=True)
        if anidb:
            record = _record(
                str(index),
                {
                    "anidb": anidb,
                    "tvdb": _values(attrs.get("tvdbid"), numeric=True),
                    "tmdb_tv": _values(attrs.get("tmdbtv"), numeric=True),
                    "tmdb_movie": _values(attrs.get("tmdbid"), numeric=True),
                    "imdb": _values(attrs.get("imdbid")),
                },
                group="anime-lists",
                weight=82,
            )
            if record is not None:
                yield record
        index += 1
        element.clear()


def import_animap(path: Path) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for index, entry in enumerate(ijson.items(handle, "entries.item")):
            if not isinstance(entry, dict):
                continue
            ids = entry.get("ids") or {}
            if not isinstance(ids, dict):
                ids = {}
            record = _record(
                f"entry:{index}",
                {
                    "anilist": _values(entry.get("anilist_id"), numeric=True),
                    "anidb": _values(ids.get("anidb"), numeric=True),
                    "mal": _values(ids.get("mal"), numeric=True),
                },
                group="animap",
                weight=95,
            )
            if record is not None:
                yield record

    with path.open("rb") as handle:
        for index, anime in enumerate(ijson.items(handle, "anime.item")):
            if not isinstance(anime, dict):
                continue
            tmdb_movies: list[Any] = []
            extra_tvdb: list[Any] = []
            for run in anime.get("episodes") or []:
                if not isinstance(run, dict):
                    continue
                tmdb_movies.extend(run.get("tmdb_movies") or [])
                for target in run.get("tvdb") or []:
                    if isinstance(target, dict) and target.get("series") is not None:
                        extra_tvdb.append(target.get("series"))
            record = _record(
                f"anime:{index}",
                {
                    "anidb": _values(anime.get("anidb_id"), numeric=True),
                    "mal": _values(anime.get("mal_ids"), numeric=True),
                    "tvdb": _values([anime.get("tvdb_id"), *extra_tvdb], numeric=True),
                    "tmdb_movie": _values(tmdb_movies, numeric=True),
                    "imdb": _values(anime.get("imdb_ids")),
                },
                group="animap",
                weight=95,
            )
            if record is not None:
                yield record


_URL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "anidb",
        re.compile(
            r"anidb\.net/(?:anime/|perl-bin/animedb\.pl\?show=anime&aid=)(\d+)", re.I
        ),
    ),
    ("anilist", re.compile(r"anilist\.co/anime/(\d+)", re.I)),
    ("mal", re.compile(r"myanimelist\.net/anime/(\d+)", re.I)),
    ("kitsu", re.compile(r"kitsu\.(?:app|io)/anime/([^/?#]+)", re.I)),
    ("animeplanet", re.compile(r"anime-planet\.com/anime/([^/?#]+)", re.I)),
    ("anisearch", re.compile(r"anisearch\.com/anime/(\d+)", re.I)),
    (
        "ann",
        re.compile(r"animenewsnetwork\.com/encyclopedia/anime\.php\?id=(\d+)", re.I),
    ),
    ("livechart", re.compile(r"livechart\.me/anime/(\d+)", re.I)),
    ("simkl", re.compile(r"simkl\.com/anime/(\d+)", re.I)),
    ("animecountdown", re.compile(r"animecountdown\.com/(\d+)", re.I)),
)


def _ids_from_source_urls(urls: Iterable[Any]) -> dict[str, tuple[str, ...]]:
    collected: dict[str, list[str]] = {}
    for raw_url in urls:
        url = str(raw_url or "").strip()
        if not url:
            continue
        for provider, pattern in _URL_PATTERNS:
            match = pattern.search(url)
            if match:
                collected.setdefault(provider, []).append(match.group(1))
                break
    return {provider: _values(values) for provider, values in collected.items()}


def import_manami(path: Path) -> Iterator[MappingRecord]:
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(item, dict) or not isinstance(item.get("sources"), list):
                continue
            record = _record(
                str(index),
                _ids_from_source_urls(item["sources"]),
                group="manami",
                weight=82,
            )
            if record is not None:
                yield record


def _descriptor(value: object) -> tuple[str, str] | None:
    text = str(value or "").strip()
    parts = text.split(":")
    if len(parts) < 2:
        return None
    raw_provider, external_id = parts[0].casefold(), parts[1].strip()
    aliases = {
        "anidb": "anidb",
        "anilist": "anilist",
        "mal": "mal",
        "tvdb_show": "tvdb",
        "tvdb_movie": "tvdb_movie",
        "tmdb_show": "tmdb_tv",
        "tmdb_movie": "tmdb_movie",
        "imdb_show": "imdb",
        "imdb_movie": "imdb",
    }
    provider = aliases.get(raw_provider)
    if not provider or not external_id:
        return None
    return provider, external_id


def import_anibridge(path: Path) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for source_descriptor, targets in ijson.kvitems(handle, ""):
            source = _descriptor(source_descriptor)
            if source is None or not isinstance(targets, dict):
                continue
            for target_descriptor in targets:
                target = _descriptor(target_descriptor)
                if target is None or target[0] == source[0]:
                    continue
                record = _record(
                    f"{source_descriptor}->{target_descriptor}",
                    {
                        source[0]: (source[1],),
                        target[0]: (target[1],),
                    },
                    group="anibridge",
                    weight=92,
                )
                if record is not None:
                    yield record


def import_wikidata_bahamut(path: Path) -> Iterator[MappingRecord]:
    """Stream strict Bahamut animeSn mappings from a deterministic WDQS result."""

    current_item: str | None = None
    collected: dict[str, set[str]] = {}

    def flush() -> MappingRecord | None:
        if not current_item:
            return None
        ids = {
            provider: tuple(sorted(values, key=lambda value: (len(value), value)))
            for provider, values in collected.items()
            if values
        }
        return _record(
            current_item,
            ids,
            group="wikidata-bahamut",
            weight=100,
        )

    with path.open("rb") as handle:
        for binding in ijson.items(handle, "results.bindings.item"):
            if not isinstance(binding, dict):
                continue
            item_value = binding.get("item")
            item_uri = (
                str(item_value.get("value") or "").strip()
                if isinstance(item_value, dict)
                else ""
            )
            item = item_uri.rsplit("/", 1)[-1]
            if not item.startswith("Q"):
                continue
            if current_item is not None and item != current_item:
                record = flush()
                if record is not None:
                    yield record
                collected = {}
            current_item = item

            for provider, field in (
                ("bahamut", "bahamut"),
                ("mal", "mal"),
                ("anilist", "anilist"),
                ("anidb", "anidb"),
            ):
                raw = binding.get(field)
                value = (
                    str(raw.get("value") or "").strip() if isinstance(raw, dict) else ""
                )
                if value.isdigit() and int(value) > 0:
                    collected.setdefault(provider, set()).add(value)

    record = flush()
    if record is not None:
        yield record


def import_notify_rensetsu(path: Path) -> Iterator[MappingRecord]:
    """Import the GitHub-hosted Notify/Rensetsu mapping dump."""
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mappings = item.get("mappings") or {}
            if not isinstance(mappings, dict):
                continue
            kitsu = mappings.get("kitsu")
            kitsu_id = kitsu.get("id") if isinstance(kitsu, dict) else kitsu
            record = _record(
                str(item.get("uuid") or index),
                {
                    "anidb": _values(mappings.get("anidb"), numeric=True),
                    "anilist": _values(mappings.get("anilist"), numeric=True),
                    "kitsu": _values(kitsu_id, numeric=True),
                    "mal": _values(mappings.get("myanimelist"), numeric=True),
                    "notify": _values(mappings.get("notify")),
                },
                group="notify-rensetsu",
                weight=88,
            )
            if record is not None:
                yield record


def import_arm(path: Path) -> Iterator[MappingRecord]:
    """Import kawaiioverflow/arm (MAL/AniList/Annict/Shoboi Calendar)."""
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            record = _record(
                str(index),
                {
                    "mal": _values(item.get("mal_id"), numeric=True),
                    "anilist": _values(item.get("anilist_id"), numeric=True),
                    "annict": _values(item.get("annict_id"), numeric=True),
                    "shoboi": _values(item.get("syobocal_tid"), numeric=True),
                },
                group="arm",
                weight=90,
            )
            if record is not None:
                yield record


def _import_anitrakt(path: Path, *, movie: bool) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mal = item.get("myanimelist") or {}
            trakt = item.get("trakt") or {}
            externals = item.get("externals") or {}
            if (
                not isinstance(mal, dict)
                or not isinstance(trakt, dict)
                or not isinstance(externals, dict)
            ):
                continue
            ids: dict[str, tuple[str, ...]] = {
                "mal": _values(mal.get("id"), numeric=True),
                "trakt": _values(trakt.get("id"), numeric=True),
                "imdb": _values(externals.get("imdb")),
            }
            if movie:
                ids["tmdb_movie"] = _values(externals.get("tmdb"), numeric=True)
                letterboxd = externals.get("letterboxd") or {}
                if isinstance(letterboxd, dict):
                    ids["letterboxd_uid"] = _values(letterboxd.get("uid"), numeric=True)
                    ids["letterboxd_slug"] = _values(letterboxd.get("slug"))
                    ids["letterboxd_lid"] = _values(letterboxd.get("lid"))
            else:
                ids["tvdb"] = _values(externals.get("tvdb"), numeric=True)
                ids["tmdb_tv"] = _values(externals.get("tmdb"), numeric=True)
            record = _record(
                str(index),
                ids,
                group="anitrakt",
                weight=88,
            )
            if record is not None:
                yield record


def import_anitrakt_tv(path: Path) -> Iterator[MappingRecord]:
    yield from _import_anitrakt(path, movie=False)


def import_anitrakt_movie(path: Path) -> Iterator[MappingRecord]:
    yield from _import_anitrakt(path, movie=True)


def import_silveryasha(path: Path) -> Iterator[MappingRecord]:
    """Import the CC0 SilverYasha public dump without scraping SilverYasha itself."""
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "data.item")):
            if not isinstance(item, dict):
                continue
            record = _record(
                str(item.get("id") or index),
                {
                    "mal": _values(item.get("mal_id"), numeric=True),
                    "silveryasha": _values(item.get("id"), numeric=True),
                },
                group="silveryasha",
                weight=88,
            )
            if record is not None:
                yield record


def import_animethemes(path: Path) -> Iterator[MappingRecord]:
    """Import the CC0 AnimeThemes mapping dump mirrored by Rensetsu."""
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mappings = item.get("mappings") or {}
            if not isinstance(mappings, dict):
                continue
            kitsu = mappings.get("kitsu")
            themes = mappings.get("animethemes")
            kitsu_id = kitsu.get("id") if isinstance(kitsu, dict) else kitsu
            themes_id = themes.get("id") if isinstance(themes, dict) else themes
            record = _record(
                str(item.get("uuid") or index),
                {
                    "anidb": _values(mappings.get("anidb"), numeric=True),
                    "anilist": _values(mappings.get("anilist"), numeric=True),
                    "ann": _values(mappings.get("animenewsnetwork"), numeric=True),
                    "animeplanet": _values(mappings.get("animeplanet")),
                    "animethemes": _values(themes_id, numeric=True),
                    "kitsu": _values(kitsu_id, numeric=True),
                    "mal": _values(mappings.get("myanimelist"), numeric=True),
                },
                group="animethemes",
                weight=90,
            )
            if record is not None:
                yield record


def import_anime_and_manga_lists(path: Path) -> Iterator[MappingRecord]:
    """Import the public AniList/MAL/AniDB anime mapping list."""
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            record = _record(
                str(index),
                {
                    "anilist": _values(item.get("idAL"), numeric=True),
                    "anidb": _values(item.get("idAniDB"), numeric=True),
                    "mal": _values(item.get("idMal"), numeric=True),
                },
                group="anime-and-manga-lists",
                weight=78,
            )
            if record is not None:
                yield record


def import_shinkro(path: Path) -> Iterator[MappingRecord]:
    """Import only title-level Shinkro MAL↔TVDB/TMDB mappings.

    Shinkro contains detailed TVDB season/episode routing. Those fields deliberately
    never enter this title identity graph. The generated JSON also contains AniDB IDs,
    but those are not used here because the useful independent contribution is the
    community-maintained MAL↔TVDB/TMDB mapping layer.
    """
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mal = _values(item.get("malid"), numeric=True)
            if not mal:
                continue
            tvdb = _values(item.get("tvdbid"), numeric=True)
            if tvdb:
                record = _record(
                    f"{index}:tvdb",
                    {"mal": mal, "tvdb": tvdb},
                    group="shinkro",
                    weight=78,
                )
                if record is not None:
                    yield record
            tmdb_movie = _values(item.get("tmdbid"), numeric=True)
            if tmdb_movie:
                record = _record(
                    f"{index}:tmdb-movie",
                    {"mal": mal, "tmdb_movie": tmdb_movie},
                    group="shinkro",
                    weight=78,
                )
                if record is not None:
                    yield record


def _runtime_graph_state(
    runtime_conn: sqlite3.Connection,
    providers: Iterable[str],
) -> tuple[
    dict[tuple[str, str], int],
    set[tuple[int, int]],
    set[tuple[int, str]],
    set[tuple[str, str]],
]:
    provider_tuple = tuple(dict.fromkeys(str(provider) for provider in providers))
    if provider_tuple:
        placeholders = ",".join("?" for _ in provider_tuple)
        node_lookup = {
            (str(provider), str(external_id)): int(node_id)
            for node_id, provider, external_id in runtime_conn.execute(
                f"SELECT id, provider, external_id FROM nodes WHERE provider IN ({placeholders})",
                provider_tuple,
            )
        }
    else:
        node_lookup = {}
    accepted_edges = {
        tuple(sorted((int(a_node), int(b_node))))
        for a_node, b_node in runtime_conn.execute(
            "SELECT a_node, b_node FROM edges WHERE status='accepted'"
        )
    }
    conflicts = {
        (int(source_node), str(target_provider))
        for source_node, target_provider in runtime_conn.execute(
            "SELECT source_node, target_provider FROM conflicts"
        )
    }
    existing_nodes = {
        (str(provider), str(external_id))
        for provider, external_id in runtime_conn.execute(
            "SELECT provider, external_id FROM nodes"
        )
    }
    return node_lookup, accepted_edges, conflicts, existing_nodes


def _find_trusted_pair(
    ids: dict[str, tuple[str, ...]],
    *,
    node_lookup: dict[tuple[str, str], int],
    accepted_edges: set[tuple[int, int]],
    conflicts: set[tuple[int, str]],
) -> tuple[tuple[str, str, int], tuple[str, str, int]] | None:
    anchors: list[tuple[str, str, int]] = []
    for provider, values in ids.items():
        if len(values) != 1:
            continue
        external_id = values[0]
        node_id = node_lookup.get((provider, external_id))
        if node_id is not None:
            anchors.append((provider, external_id, node_id))
    for left_index, left in enumerate(anchors):
        for right in anchors[left_index + 1 :]:
            if _safe_accepted_pair(
                left,
                right,
                accepted_edges=accepted_edges,
                conflicts=conflicts,
            ):
                return left, right
    return None


def _anchor_enrichment_records(
    *,
    key: str,
    trusted_pair: tuple[tuple[str, str, int], tuple[str, str, int]],
    targets: dict[str, tuple[str, ...]],
    existing_nodes: set[tuple[str, str]],
    group: str,
    weight: int,
) -> Iterator[MappingRecord]:
    anchor_providers = {trusted_pair[0][0], trusted_pair[1][0]}
    for target_provider, target_values in targets.items():
        # Multiple IDs for one provider on the same source item are ambiguous at the
        # title layer. Do not guess which one is the canonical target.
        if len(target_values) != 1 or target_provider in anchor_providers:
            continue
        target_id = target_values[0]
        if (target_provider, target_id) in existing_nodes:
            continue
        for anchor_provider, anchor_id, _anchor_node in trusted_pair:
            yield MappingRecord(
                record_key=f"{key}:{target_provider}:{target_id}:{anchor_provider}",
                ids={
                    anchor_provider: (anchor_id,),
                    target_provider: (target_id,),
                },
                evidence_group=group,
                weight=weight,
            )


_ANIMETHEMES_ANCHOR_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("anidb", "anidb", True),
    ("anilist", "anilist", True),
    ("animenewsnetwork", "ann", True),
    ("animeplanet", "animeplanet", False),
    ("kitsu", "kitsu", True),
    ("myanimelist", "mal", True),
)


def import_animethemes_enrichment(
    path: Path,
    runtime_conn: sqlite3.Connection,
) -> Iterator[MappingRecord]:
    """Attach only AnimeThemes IDs after two trusted base anchors agree."""
    anchor_providers = tuple(
        provider for _field, provider, _numeric in _ANIMETHEMES_ANCHOR_FIELDS
    )
    node_lookup, accepted_edges, conflicts, existing_nodes = _runtime_graph_state(
        runtime_conn, anchor_providers
    )
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mappings = item.get("mappings") or {}
            if not isinstance(mappings, dict):
                continue
            anchor_ids: dict[str, tuple[str, ...]] = {}
            for field, provider, numeric in _ANIMETHEMES_ANCHOR_FIELDS:
                raw = mappings.get(field)
                if field == "kitsu" and isinstance(raw, dict):
                    raw = raw.get("id")
                values = _values(raw, numeric=numeric)
                if values:
                    anchor_ids[provider] = values
            trusted_pair = _find_trusted_pair(
                anchor_ids,
                node_lookup=node_lookup,
                accepted_edges=accepted_edges,
                conflicts=conflicts,
            )
            if trusted_pair is None:
                continue
            themes = mappings.get("animethemes")
            themes_id = themes.get("id") if isinstance(themes, dict) else themes
            target = _values(themes_id, numeric=True)
            if not target:
                continue
            yield from _anchor_enrichment_records(
                key=str(item.get("uuid") or index),
                trusted_pair=trusted_pair,
                targets={"animethemes": target},
                existing_nodes=existing_nodes,
                group="animethemes-anchor",
                weight=90,
            )


_ANIMEAGGREGATIONS_ANCHOR_KEYS: tuple[tuple[str, str], ...] = (
    ("MAL", "mal"),
    ("ANN", "ann"),
    ("IMDB", "imdb"),
    ("SYOBOI", "shoboi"),
)

_ANIMEAGGREGATIONS_SIMPLE_TARGETS: dict[str, str] = {
    "MAL": "mal",
    "ANN": "ann",
    "IMDB": "imdb",
    "SYOBOI": "shoboi",
    "ALL_CINEMA": "allcinema",
    "ANISON": "anison",
    "ANIME_NFO": "animenfo",
    "CRUNCHY_ROLL": "crunchyroll",
    "BANGUMI": "bangumi",
    "DOUBAN": "douban",
    "BILI_BILI": "bilibili",
    "FUNIMATION": "funimation",
    "HIDIVE": "hidive",
    "NETFLIX": "netflix",
    "MEDIA_ART_DATABASE": "mediaarts",
    "LAIN": "lain",
    "ANIMEMORIAL": "animemorial",
    "MARUMEGANEL": "marumeganel",
    "TV_ANIMATION_MUSEUM": "tv_animation_museum",
}

_ANIMEAGGREGATIONS_ENRICHMENT_PROVIDERS = frozenset(
    {
        "allcinema",
        "anison",
        "animenfo",
        "crunchyroll",
        "bangumi",
        "douban",
        "bilibili",
        "funimation",
        "hidive",
        "netflix",
        "mediaarts",
        "lain",
        "animemorial",
        "marumeganel",
        "tv_animation_museum",
    }
)


def _animeaggregations_ids(
    anidb_id: object,
    resources: dict[str, Any],
) -> dict[str, tuple[str, ...]]:
    ids: dict[str, tuple[str, ...]] = {"anidb": _values(anidb_id, numeric=True)}
    for source_key, provider in _ANIMEAGGREGATIONS_SIMPLE_TARGETS.items():
        values = resources.get(source_key)
        numeric = provider in {"mal", "ann", "shoboi", "bangumi", "allcinema", "anison"}
        cleaned = _values(values, numeric=numeric)
        if provider == "funimation":
            cleaned = tuple(value.strip("/") for value in cleaned if value.strip("/"))
        if cleaned:
            ids[provider] = cleaned

    tmdb_tv: list[str] = []
    tmdb_movie: list[str] = []
    for value in _values(resources.get("TMDB")):
        kind, sep, external_id = value.partition("/")
        if not sep or not external_id.isdigit():
            continue
        if kind.casefold() == "tv":
            tmdb_tv.append(external_id)
        elif kind.casefold() == "movie":
            tmdb_movie.append(external_id)
    if tmdb_tv:
        ids["tmdb_tv"] = _values(tmdb_tv, numeric=True)
    if tmdb_movie:
        ids["tmdb_movie"] = _values(tmdb_movie, numeric=True)
    return ids


def import_animeaggregations_enrichment(
    path: Path,
    runtime_conn: sqlite3.Connection,
) -> Iterator[MappingRecord]:
    """Use AnimeAggregations only to attach missing IDs to trusted base anchors."""
    anchor_providers = (
        "anidb",
        "mal",
        "ann",
        "imdb",
        "shoboi",
        "tmdb_tv",
        "tmdb_movie",
    )
    node_lookup, accepted_edges, conflicts, existing_nodes = _runtime_graph_state(
        runtime_conn, anchor_providers
    )
    with path.open("rb") as handle:
        for anidb_id, item in ijson.kvitems(handle, "animes"):
            if not isinstance(item, dict):
                continue
            resources = item.get("resources") or {}
            if not isinstance(resources, dict):
                continue
            ids = _animeaggregations_ids(anidb_id, resources)
            trusted_pair = _find_trusted_pair(
                {provider: ids.get(provider, ()) for provider in anchor_providers},
                node_lookup=node_lookup,
                accepted_edges=accepted_edges,
                conflicts=conflicts,
            )
            if trusted_pair is None:
                continue
            yield from _anchor_enrichment_records(
                key=str(anidb_id),
                trusted_pair=trusted_pair,
                targets={
                    provider: values
                    for provider, values in ids.items()
                    if provider in _ANIMEAGGREGATIONS_ENRICHMENT_PROVIDERS
                },
                existing_nodes=existing_nodes,
                group="animeaggregations-anchor",
                weight=85,
            )


_WIKIDATA_PROPERTY_FIELDS: dict[str, tuple[str, bool]] = {
    "P4086": ("mal", True),
    "P8729": ("anilist", True),
    "P5646": ("anidb", True),
    "P11495": ("kitsu", True),
    "P12477": ("anisearch", True),
    "P1985": ("ann", True),
    "P11349": ("animeplanet", False),
    "P12489": ("livechart", True),
    "P12427": ("notify", False),
    "P13424": ("bahamut", True),
    "P5732": ("bangumi", True),
    "P5733": ("bilibili", False),
    "P11330": ("crunchyroll", False),
    "P5845": ("animeclick", False),
    "P12005": ("anikore", False),
    "P7017": ("animecharacters", False),
    "P9573": ("animefillerlist", False),
    "P11039": ("animetaizen", False),
    "P7886": ("mediaarts", False),
    "P11551": ("nanime", False),
    "P11176": ("niconico", False),
}
_WIKIDATA_ANCHOR_PROVIDERS: tuple[str, ...] = (
    "mal",
    "anilist",
    "anidb",
    "kitsu",
    "anisearch",
    "ann",
    "animeplanet",
    "livechart",
    "notify",
)
_WIKIDATA_ENRICHMENT_PROVIDERS = frozenset(
    {
        "bangumi",
        "bilibili",
        "crunchyroll",
        "animeclick",
        "anikore",
        "animecharacters",
        "animefillerlist",
        "animetaizen",
        "mediaarts",
        "nanime",
        "niconico",
    }
)


def _wikidata_property_code(binding: dict[str, Any]) -> str | None:
    raw = binding.get("prop")
    uri = str(raw.get("value") or "") if isinstance(raw, dict) else ""
    match = re.search(r"P\d+", uri)
    return match.group(0) if match else None


def import_wikidata_enrichment(
    path: Path,
    runtime_conn: sqlite3.Connection,
) -> Iterator[MappingRecord]:
    """Anchor-validate bulk Wikidata IDs before enriching the title graph."""
    node_lookup, accepted_edges, conflicts, existing_nodes = _runtime_graph_state(
        runtime_conn, _WIKIDATA_ANCHOR_PROVIDERS
    )
    current_item: str | None = None
    collected: dict[str, set[str]] = {}

    def emit_item(item: str, values: dict[str, set[str]]) -> Iterator[MappingRecord]:
        ids = {
            provider: tuple(
                sorted(provider_values, key=lambda value: (len(value), value))
            )
            for provider, provider_values in values.items()
            if provider_values
        }
        trusted_pair = _find_trusted_pair(
            {
                provider: ids.get(provider, ())
                for provider in _WIKIDATA_ANCHOR_PROVIDERS
            },
            node_lookup=node_lookup,
            accepted_edges=accepted_edges,
            conflicts=conflicts,
        )
        if trusted_pair is None:
            return
        targets = {
            provider: values
            for provider, values in ids.items()
            if provider in _WIKIDATA_ENRICHMENT_PROVIDERS
        }
        targets["wikidata"] = (item,)
        yield from _anchor_enrichment_records(
            key=item,
            trusted_pair=trusted_pair,
            targets=targets,
            existing_nodes=existing_nodes,
            group="wikidata-anchor",
            weight=90,
        )

    with path.open("rb") as handle:
        for binding in ijson.items(handle, "results.bindings.item"):
            if not isinstance(binding, dict):
                continue
            item_slot = binding.get("item")
            item_uri = (
                str(item_slot.get("value") or "").strip()
                if isinstance(item_slot, dict)
                else ""
            )
            item = item_uri.rsplit("/", 1)[-1]
            if not re.fullmatch(r"Q\d+", item):
                continue
            if current_item is not None and item != current_item:
                yield from emit_item(current_item, collected)
                collected = {}
            current_item = item

            prop_code = _wikidata_property_code(binding)
            field = _WIKIDATA_PROPERTY_FIELDS.get(prop_code or "")
            if field is None:
                continue
            provider, numeric = field
            raw = binding.get("id")
            raw_value = (
                str(raw.get("value") or "").strip() if isinstance(raw, dict) else ""
            )
            values = _values(raw_value, numeric=numeric)
            if values:
                collected.setdefault(provider, set()).update(values)

    if current_item is not None:
        yield from emit_item(current_item, collected)


_ANIMEAPI_ANCHOR_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("myanimelist", "mal", True),
    ("anilist", "anilist", True),
    ("anidb", "anidb", True),
    ("kitsu", "kitsu", True),
    ("anisearch", "anisearch", True),
    ("animeplanet", "animeplanet", False),
    ("animenewsnetwork", "ann", True),
    ("livechart", "livechart", True),
    ("simkl", "simkl", True),
)

_ANIMEAPI_TARGET_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("annict", "annict", True),
    ("hikka", "hikka", False),
    ("kaize", "kaize", False),
    ("kaize_id", "kaize_id", True),
    ("letterboxd_lid", "letterboxd_lid", False),
    ("letterboxd_slug", "letterboxd_slug", False),
    ("letterboxd_uid", "letterboxd_uid", True),
    ("nautiljon", "nautiljon", False),
    ("nautiljon_id", "nautiljon_id", True),
    ("notify", "notify", False),
    ("otakotaku", "otakotaku", True),
    ("shikimori", "shikimori", True),
    ("shoboi", "shoboi", True),
    ("silveryasha", "silveryasha", True),
    ("trakt", "trakt", True),
)


def _safe_accepted_pair(
    left: tuple[str, str, int],
    right: tuple[str, str, int],
    *,
    accepted_edges: set[tuple[int, int]],
    conflicts: set[tuple[int, str]],
) -> bool:
    left_provider, _left_id, left_node = left
    right_provider, _right_id, right_node = right
    edge = tuple(sorted((left_node, right_node)))
    return (
        edge in accepted_edges
        and (left_node, right_provider) not in conflicts
        and (right_node, left_provider) not in conflicts
    )


def import_animeapi_enrichment(
    path: Path,
    runtime_conn: sqlite3.Connection,
) -> Iterator[MappingRecord]:
    """Import AnimeAPI only as anchor-validated supplemental namespace enrichment.

    Existing provider-to-provider relationships are deliberately not emitted. A row
    must first contain at least two anime-native IDs that already form an accepted,
    conflict-free direct edge in the provisional runtime database. New namespace IDs
    are then linked separately to those two anchors, so AnimeAPI cannot become a
    second correlated vote for an existing edge.
    """

    anchor_providers = tuple(
        provider for _field, provider, _numeric in _ANIMEAPI_ANCHOR_FIELDS
    )
    node_lookup, accepted_edges, conflicts, existing_nodes = _runtime_graph_state(
        runtime_conn, anchor_providers
    )

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for index, row in enumerate(reader):
            anchors: list[tuple[str, str, int]] = []
            for field, provider, numeric in _ANIMEAPI_ANCHOR_FIELDS:
                values = _values(row.get(field), numeric=numeric)
                if not values:
                    continue
                external_id = values[0]
                node_id = node_lookup.get((provider, external_id))
                if node_id is not None:
                    anchors.append((provider, external_id, node_id))

            trusted_pair: tuple[tuple[str, str, int], tuple[str, str, int]] | None = (
                None
            )
            for left_index, left in enumerate(anchors):
                for right in anchors[left_index + 1 :]:
                    if _safe_accepted_pair(
                        left,
                        right,
                        accepted_edges=accepted_edges,
                        conflicts=conflicts,
                    ):
                        trusted_pair = (left, right)
                        break
                if trusted_pair is not None:
                    break
            if trusted_pair is None:
                continue

            for field, target_provider, numeric in _ANIMEAPI_TARGET_FIELDS:
                if target_provider == "trakt" and str(
                    row.get("trakt_may_invalid") or ""
                ).strip().casefold() in {"1", "true", "yes"}:
                    continue
                target_values = _values(row.get(field), numeric=numeric)
                if not target_values:
                    continue
                target_id = target_values[0]
                if (target_provider, target_id) in existing_nodes:
                    # The base graph already knows this exact target ID. AnimeAPI is
                    # correlated with several base sources, so do not add another vote
                    # for an already represented node. Missing IDs in the same namespace
                    # may still be added after anchor validation.
                    continue
                for anchor_provider, anchor_id, _anchor_node in trusted_pair:
                    yield MappingRecord(
                        record_key=f"{index}:{target_provider}:{target_id}:{anchor_provider}",
                        ids={
                            anchor_provider: (anchor_id,),
                            target_provider: (target_id,),
                        },
                        evidence_group="animeapi-anchor",
                        weight=85,
                    )


IMPORTERS = {
    "fribb": import_fribb,
    "kometa": import_kometa,
    "anime_lists": import_anime_lists,
    "animap": import_animap,
    "manami": import_manami,
    "anibridge": import_anibridge,
    "wikidata_bahamut": import_wikidata_bahamut,
    "notify_rensetsu": import_notify_rensetsu,
    "arm": import_arm,
    "anitrakt_tv": import_anitrakt_tv,
    "anitrakt_movie": import_anitrakt_movie,
    "silveryasha": import_silveryasha,
    "animethemes": import_animethemes,
    "anime_and_manga_lists": import_anime_and_manga_lists,
    "shinkro": import_shinkro,
}

SUPPLEMENTAL_IMPORTERS = {
    "animeapi": import_animeapi_enrichment,
    "animethemes": import_animethemes_enrichment,
    "animeaggregations": import_animeaggregations_enrichment,
    "wikidata_multi": import_wikidata_enrichment,
}
