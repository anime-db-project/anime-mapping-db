from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, Iterator

import ijson

from anime_mapping_db.database import MappingRecord
from anime_mapping_db.importers.common import record as _record
from anime_mapping_db.importers.common import values as _values


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
                ("manami", 62, {
                    "anidb": anidb,
                    "mal": _values(item.get("mal_id"), numeric=True),
                    "anilist": _values(item.get("anilist_id"), numeric=True),
                }),
                ("anime-lists", 62, {
                    "anidb": anidb,
                    "tvdb": _values(item.get("tvdb_id"), numeric=True),
                    "imdb": _values(item.get("imdb_id")),
                }),
                ("animeaggregations", 68, {
                    "anidb": anidb,
                    "tmdb_movie": _values(item.get("tmdb_movie_id"), numeric=True),
                    "tmdb_tv": _values(item.get("tmdb_show_id"), numeric=True),
                }),
            )
            for group, weight, ids in groups:
                mapped = _record(f"{anidb_key}:{group}", ids, group=group, weight=weight)
                if mapped is not None:
                    yield mapped


def import_anime_lists(path: Path) -> Iterator[MappingRecord]:
    index = 0
    for _event, element in ET.iterparse(path, events=("end",)):
        if element.tag.rsplit("}", 1)[-1] != "anime":
            continue
        attrs = element.attrib
        anidb = _values(attrs.get("anidbid"), numeric=True)
        if anidb:
            mapped = _record(
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
            if mapped is not None:
                yield mapped
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
            mapped = _record(
                f"entry:{index}",
                {
                    "anilist": _values(entry.get("anilist_id"), numeric=True),
                    "anidb": _values(ids.get("anidb"), numeric=True),
                    "mal": _values(ids.get("mal"), numeric=True),
                },
                group="animap",
                weight=95,
            )
            if mapped is not None:
                yield mapped

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
            mapped = _record(
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
            if mapped is not None:
                yield mapped


_URL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("anidb", re.compile(r"anidb\.net/(?:anime/|perl-bin/animedb\.pl\?show=anime&aid=)(\d+)", re.I)),
    ("anilist", re.compile(r"anilist\.co/anime/(\d+)", re.I)),
    ("mal", re.compile(r"myanimelist\.net/anime/(\d+)", re.I)),
    ("kitsu", re.compile(r"kitsu\.(?:app|io)/anime/([^/?#]+)", re.I)),
    ("animeplanet", re.compile(r"anime-planet\.com/anime/([^/?#]+)", re.I)),
    ("anisearch", re.compile(r"anisearch\.com/anime/(\d+)", re.I)),
    ("ann", re.compile(r"animenewsnetwork\.com/encyclopedia/anime\.php\?id=(\d+)", re.I)),
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
    return {provider: _values(items) for provider, items in collected.items()}


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
            mapped = _record(
                str(index), _ids_from_source_urls(item["sources"]), group="manami", weight=82
            )
            if mapped is not None:
                yield mapped


def _descriptor(value: object) -> tuple[str, str] | None:
    text = str(value or "").strip()
    parts = text.split(":")
    if len(parts) < 2:
        return None
    raw_provider, external_id = parts[0].casefold(), parts[1].strip()
    aliases = {
        "anidb": "anidb", "anilist": "anilist", "mal": "mal",
        "tvdb_show": "tvdb", "tvdb_movie": "tvdb_movie",
        "tmdb_show": "tmdb_tv", "tmdb_movie": "tmdb_movie",
        "imdb_show": "imdb", "imdb_movie": "imdb",
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
                mapped = _record(
                    f"{source_descriptor}->{target_descriptor}",
                    {source[0]: (source[1],), target[0]: (target[1],)},
                    group="anibridge",
                    weight=92,
                )
                if mapped is not None:
                    yield mapped


def import_notify_rensetsu(path: Path) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mappings = item.get("mappings") or {}
            if not isinstance(mappings, dict):
                continue
            kitsu = mappings.get("kitsu")
            kitsu_id = kitsu.get("id") if isinstance(kitsu, dict) else kitsu
            mapped = _record(
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
            if mapped is not None:
                yield mapped


def import_arm(path: Path) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mapped = _record(
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
            if mapped is not None:
                yield mapped


def _import_anitrakt(path: Path, *, movie: bool) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mal = item.get("myanimelist") or {}
            trakt = item.get("trakt") or {}
            externals = item.get("externals") or {}
            if not isinstance(mal, dict) or not isinstance(trakt, dict) or not isinstance(externals, dict):
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
            mapped = _record(str(index), ids, group="anitrakt", weight=88)
            if mapped is not None:
                yield mapped


def import_anitrakt_tv(path: Path) -> Iterator[MappingRecord]:
    yield from _import_anitrakt(path, movie=False)


def import_anitrakt_movie(path: Path) -> Iterator[MappingRecord]:
    yield from _import_anitrakt(path, movie=True)


def import_silveryasha(path: Path) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "data.item")):
            if not isinstance(item, dict):
                continue
            mapped = _record(
                str(item.get("id") or index),
                {
                    "mal": _values(item.get("mal_id"), numeric=True),
                    "silveryasha": _values(item.get("id"), numeric=True),
                },
                group="silveryasha",
                weight=88,
            )
            if mapped is not None:
                yield mapped


def import_animethemes(path: Path) -> Iterator[MappingRecord]:
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
            mapped = _record(
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
            if mapped is not None:
                yield mapped


def import_anime_and_manga_lists(path: Path) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mapped = _record(
                str(index),
                {
                    "anilist": _values(item.get("idAL"), numeric=True),
                    "anidb": _values(item.get("idAniDB"), numeric=True),
                    "mal": _values(item.get("idMal"), numeric=True),
                },
                group="anime-and-manga-lists",
                weight=78,
            )
            if mapped is not None:
                yield mapped


def import_shinkro(path: Path) -> Iterator[MappingRecord]:
    with path.open("rb") as handle:
        for index, item in enumerate(ijson.items(handle, "item")):
            if not isinstance(item, dict):
                continue
            mal = _values(item.get("malid"), numeric=True)
            if not mal:
                continue
            tvdb = _values(item.get("tvdbid"), numeric=True)
            if tvdb:
                mapped = _record(
                    f"{index}:tvdb", {"mal": mal, "tvdb": tvdb},
                    group="shinkro", weight=78,
                )
                if mapped is not None:
                    yield mapped
            tmdb_movie = _values(item.get("tmdbid"), numeric=True)
            if tmdb_movie:
                mapped = _record(
                    f"{index}:tmdb-movie", {"mal": mal, "tmdb_movie": tmdb_movie},
                    group="shinkro", weight=78,
                )
                if mapped is not None:
                    yield mapped
