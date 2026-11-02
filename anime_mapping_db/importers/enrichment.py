from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Iterator

import ijson

from anime_mapping_db.database import MappingRecord
from anime_mapping_db.importers.common import values as _values


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


def _find_trusted_pair(
    ids: dict[str, tuple[str, ...]],
    *,
    node_lookup: dict[tuple[str, str], int],
    accepted_edges: set[tuple[int, int]],
    conflicts: set[tuple[int, str]],
) -> tuple[tuple[str, str, int], tuple[str, str, int]] | None:
    anchors: list[tuple[str, str, int]] = []
    for provider, provider_ids in ids.items():
        if len(provider_ids) != 1:
            continue
        external_id = provider_ids[0]
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
                provider_ids = _values(raw, numeric=numeric)
                if provider_ids:
                    anchor_ids[provider] = provider_ids
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
        raw_values = resources.get(source_key)
        numeric = provider in {
            "mal",
            "ann",
            "shoboi",
            "bangumi",
            "allcinema",
            "anison",
        }
        cleaned = _values(raw_values, numeric=numeric)
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
                    provider: provider_ids
                    for provider, provider_ids in ids.items()
                    if provider in _ANIMEAGGREGATIONS_ENRICHMENT_PROVIDERS
                },
                existing_nodes=existing_nodes,
                group="animeaggregations-anchor",
                weight=85,
            )


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


def import_animeapi_enrichment(
    path: Path,
    runtime_conn: sqlite3.Connection,
) -> Iterator[MappingRecord]:
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
                provider_ids = _values(row.get(field), numeric=numeric)
                if not provider_ids:
                    continue
                external_id = provider_ids[0]
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
