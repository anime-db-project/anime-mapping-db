from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Iterator

import ijson

from anime_mapping_db.database import MappingRecord
from anime_mapping_db.importers.common import record as _record
from anime_mapping_db.importers.common import values as _values
from anime_mapping_db.importers.enrichment import (
    _anchor_enrichment_records,
    _find_trusted_pair,
    _runtime_graph_state,
)


def import_wikidata_bahamut(path: Path) -> Iterator[MappingRecord]:
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
        return _record(current_item, ids, group="wikidata-bahamut", weight=100)

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
                mapped = flush()
                if mapped is not None:
                    yield mapped
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
                    str(raw.get("value") or "").strip()
                    if isinstance(raw, dict)
                    else ""
                )
                if value.isdigit() and int(value) > 0:
                    collected.setdefault(provider, set()).add(value)

    mapped = flush()
    if mapped is not None:
        yield mapped


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
            provider: provider_ids
            for provider, provider_ids in ids.items()
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
                str(raw.get("value") or "").strip()
                if isinstance(raw, dict)
                else ""
            )
            provider_ids = _values(raw_value, numeric=numeric)
            if provider_ids:
                collected.setdefault(provider, set()).update(provider_ids)

    if current_item is not None:
        yield from emit_item(current_item, collected)
