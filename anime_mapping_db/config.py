from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class MappingSourceSpec:
    name: str
    url: str
    importer: str
    required: bool
    license_note: str
    checksum_url: str | None = None
    check_interval: str = "default"
    supplemental: bool = False
    fallback_urls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MappingSettings:
    db_path: Path
    evidence_db_path: Path
    update_max_age_hours: float = 24.0
    wikidata_check_interval_hours: float = 168.0
    request_timeout_seconds: float = 300.0
    keep_downloads: bool = False
    keep_previous: bool = True


def _env_path(name: str, default: str) -> Path:
    raw = str(os.environ.get(name, default) or default).strip()
    path = Path(raw)
    return path if path.is_absolute() else ROOT_DIR / path


def _env_float(name: str, default: float, minimum: float) -> float:
    try:
        value = float(str(os.environ.get(name, default)).strip())
    except ValueError:
        value = default
    return max(minimum, value)


def _env_bool(name: str, default: bool) -> bool:
    value = str(os.environ.get(name, "1" if default else "0") or "").strip().casefold()
    return value not in {"", "0", "false", "no", "off"}


def get_settings() -> MappingSettings:
    return MappingSettings(
        db_path=_env_path("MAPPINGS_DB_PATH", "data/mappings/mappings.db"),
        evidence_db_path=_env_path(
            "MAPPINGS_EVIDENCE_DB_PATH", "data/mappings/mappings-evidence.db"
        ),
        update_max_age_hours=_env_float("MAPPINGS_UPDATE_MAX_AGE_HOURS", 24.0, 0.25),
        wikidata_check_interval_hours=_env_float(
            "MAPPINGS_WIKIDATA_CHECK_INTERVAL_HOURS", 168.0, 1.0
        ),
        request_timeout_seconds=_env_float(
            "MAPPINGS_REQUEST_TIMEOUT_SECONDS", 300.0, 30.0
        ),
        keep_downloads=_env_bool("MAPPINGS_KEEP_DOWNLOADS", False),
        keep_previous=_env_bool("MAPPINGS_KEEP_PREVIOUS", True),
    )


_WIKIDATA_BAHAMUT_QUERY = """
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT ?item ?bahamut ?mal ?anilist ?anidb WHERE {
  ?item wdt:P13424 ?bahamut .
  OPTIONAL { ?item wdt:P4086 ?mal . }
  OPTIONAL { ?item wdt:P8729 ?anilist . }
  OPTIONAL { ?item wdt:P5646 ?anidb . }
  FILTER(BOUND(?mal) || BOUND(?anilist) || BOUND(?anidb))
}
ORDER BY ?item ?bahamut ?mal ?anilist ?anidb
""".strip()

_WIKIDATA_MULTI_QUERY = """
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
SELECT DISTINCT ?item ?prop ?id WHERE {
  VALUES ?anchorProp {
    wdt:P4086 wdt:P8729 wdt:P5646 wdt:P11495 wdt:P12477
    wdt:P1985 wdt:P11349 wdt:P12489 wdt:P12427
  }
  ?item ?anchorProp ?anchorId .
  VALUES ?prop {
    wdt:P4086 wdt:P8729 wdt:P5646 wdt:P11495 wdt:P12477
    wdt:P1985 wdt:P11349 wdt:P12489 wdt:P12427 wdt:P13424
    wdt:P5732 wdt:P5733 wdt:P11330 wdt:P5845 wdt:P12005
    wdt:P7017 wdt:P9573 wdt:P11039 wdt:P7886 wdt:P11551 wdt:P11176
  }
  ?item ?prop ?id .
}
ORDER BY ?item ?prop ?id
LIMIT 500000
""".strip()


def _sparql_url(endpoint: str, query: str) -> str:
    return endpoint.rstrip("?") + "?format=json&query=" + quote(query, safe="")


_WIKIDATA_QLEVER = "https://qlever.dev/api/wikidata"
_WIKIDATA_WDQS = "https://query.wikidata.org/sparql"
_WIKIDATA_BAHAMUT_URL = _sparql_url(_WIKIDATA_QLEVER, _WIKIDATA_BAHAMUT_QUERY)
_WIKIDATA_BAHAMUT_FALLBACK = _sparql_url(_WIKIDATA_WDQS, _WIKIDATA_BAHAMUT_QUERY)
_WIKIDATA_MULTI_URL = _sparql_url(_WIKIDATA_QLEVER, _WIKIDATA_MULTI_QUERY)
_WIKIDATA_MULTI_FALLBACK = _sparql_url(_WIKIDATA_WDQS, _WIKIDATA_MULTI_QUERY)

SOURCE_SPECS: tuple[MappingSourceSpec, ...] = (
    MappingSourceSpec(
        name="Fribb/anime-lists",
        url="https://raw.githubusercontent.com/Fribb/anime-lists/master/anime-list-full.json",
        importer="fribb",
        required=True,
        license_note="No explicit repository dataset license; runtime download only.",
    ),
    MappingSourceSpec(
        name="Kometa-Team/Anime-IDs",
        url="https://raw.githubusercontent.com/Kometa-Team/Anime-IDs/master/anime_ids.json",
        importer="kometa",
        required=True,
        license_note="Repository MIT; generated data contains upstream mappings.",
    ),
    MappingSourceSpec(
        name="Anime-Lists/anime-lists",
        url="https://raw.githubusercontent.com/Anime-Lists/anime-lists/master/anime-list-full.xml",
        importer="anime_lists",
        required=True,
        license_note="No explicit repository dataset license; runtime download only.",
    ),
    MappingSourceSpec(
        name="cplieger/animap",
        url="https://github.com/cplieger/animap/releases/latest/download/animap.json",
        importer="animap",
        required=True,
        license_note="ODbL-1.0 + DbCL-1.0 data; Apache-2.0 code.",
        checksum_url="https://github.com/cplieger/animap/releases/latest/download/animap.json.sha256",
    ),
    MappingSourceSpec(
        name="cedya77/anime-offline-database",
        url="https://github.com/cedya77/anime-offline-database/releases/latest/download/anime-offline-database.jsonl",
        importer="manami",
        required=False,
        license_note="ODbL-1.0 + DbCL-1.0; maintained fork of manami-project/anime-offline-database.",
    ),
    MappingSourceSpec(
        name="anibridge/anibridge-mappings",
        url="https://github.com/anibridge/anibridge-mappings/releases/download/v3/mappings.min.json",
        importer="anibridge",
        required=False,
        license_note="MIT repository; generated mapping data inherits upstream obligations.",
    ),
    MappingSourceSpec(
        name="Wikidata/Bahamut Animation Crazy",
        url=_WIKIDATA_BAHAMUT_URL,
        importer="wikidata_bahamut",
        required=False,
        license_note="Wikidata structured data is CC0 1.0.",
        check_interval="wikidata",
        fallback_urls=(_WIKIDATA_BAHAMUT_FALLBACK,),
    ),
    MappingSourceSpec(
        name="rensetsu/db.notify.rensetsu-mirai",
        url="https://raw.githubusercontent.com/rensetsu/db.notify.rensetsu-mirai/main/notify_min.json",
        importer="notify_rensetsu",
        required=False,
        license_note="MIT repository; Notify-derived mapping data is consumed from the GitHub dump only.",
    ),
    MappingSourceSpec(
        name="kawaiioverflow/arm",
        url="https://raw.githubusercontent.com/kawaiioverflow/arm/master/arm.json",
        importer="arm",
        required=False,
        license_note="MIT package metadata; public GitHub JSON mapping dump.",
    ),
    MappingSourceSpec(
        name="rensetsu/db.trakt.extended-anitrakt TV",
        url="https://raw.githubusercontent.com/rensetsu/db.trakt.extended-anitrakt/main/json/output/tv_ex.json",
        importer="anitrakt_tv",
        required=False,
        license_note="MIT repository; public GitHub JSON mapping dump.",
    ),
    MappingSourceSpec(
        name="rensetsu/db.trakt.extended-anitrakt Movies",
        url="https://raw.githubusercontent.com/rensetsu/db.trakt.extended-anitrakt/main/json/output/movies_ex.json",
        importer="anitrakt_movie",
        required=False,
        license_note="MIT repository; public GitHub JSON mapping dump.",
    ),
    MappingSourceSpec(
        name="rensetsu/db.rensetsu.public-dump SilverYasha",
        url="https://raw.githubusercontent.com/rensetsu/db.rensetsu.public-dump/main/Silveryasha/silveryasha_raw.json",
        importer="silveryasha",
        required=False,
        license_note="CC0-1.0 public GitHub dump.",
    ),
    MappingSourceSpec(
        name="rensetsu/db.rensetsu.public-dump AnimeThemes",
        url="https://raw.githubusercontent.com/rensetsu/db.rensetsu.public-dump/main/AnimeThemes/animethemes_min.json",
        importer="animethemes",
        required=False,
        license_note="CC0-1.0 public GitHub dump; converted AnimeThemes mappings, consumed as anchor-validated supplemental enrichment.",
        supplemental=True,
    ),
    MappingSourceSpec(
        name="anime-and-manga/lists",
        url="https://raw.githubusercontent.com/anime-and-manga/lists/main/anime.json",
        importer="anime_and_manga_lists",
        required=False,
        license_note="Public GitHub mapping dump; repository has no explicit dataset license.",
    ),
    MappingSourceSpec(
        name="shinkro/community-mapping",
        url="https://raw.githubusercontent.com/shinkro/community-mapping/main/shinkrodb/malid-anidbid-tvdbid-tmdbid.json",
        importer="shinkro",
        required=False,
        license_note="MIT repository; corroborating title-level MAL/TVDB/TMDB mappings only, season and episode fields are excluded.",
    ),
    MappingSourceSpec(
        name="notseteve/AnimeAggregations",
        url="https://raw.githubusercontent.com/notseteve/AnimeAggregations/main/aggregate/AnimeToExternal.json",
        importer="animeaggregations",
        required=False,
        license_note="Unlicense repository; aggregate external IDs are consumed only as anchor-validated supplemental enrichment.",
        supplemental=True,
    ),
    MappingSourceSpec(
        name="Wikidata multi-ID",
        url=_WIKIDATA_MULTI_URL,
        importer="wikidata_multi",
        required=False,
        license_note="Wikidata structured data is CC0 1.0; QLever is the primary bulk query backend with WDQS fallback.",
        check_interval="wikidata",
        supplemental=True,
        fallback_urls=(_WIKIDATA_MULTI_FALLBACK,),
    ),
    MappingSourceSpec(
        name="nattadasu/animeApi",
        url="https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv",
        importer="animeapi",
        required=False,
        license_note="Compiled database: ODbL-1.0 + DbCL-1.0; consumed as a GitHub-hosted TSV, never via the AnimeAPI HTTP service.",
        supplemental=True,
    ),
)


def mappings_db_path() -> Path:
    return get_settings().db_path


def mappings_evidence_db_path() -> Path:
    return get_settings().evidence_db_path


def mappings_update_max_age_hours() -> float:
    return get_settings().update_max_age_hours


def mappings_wikidata_check_interval_hours() -> float:
    return get_settings().wikidata_check_interval_hours


def mappings_request_timeout_seconds() -> float:
    return get_settings().request_timeout_seconds


def mappings_keep_downloads() -> bool:
    return get_settings().keep_downloads


def mappings_keep_previous() -> bool:
    return get_settings().keep_previous
