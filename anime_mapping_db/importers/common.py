from __future__ import annotations

from typing import Any

from anime_mapping_db.database import MappingRecord


def values(value: Any, *, numeric: bool = False) -> tuple[str, ...]:
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


def record(
    key: str,
    ids: dict[str, tuple[str, ...]],
    *,
    group: str,
    weight: int,
) -> MappingRecord | None:
    cleaned = {
        provider: provider_ids for provider, provider_ids in ids.items() if provider_ids
    }
    if len(cleaned) < 2:
        return None
    return MappingRecord(
        record_key=key,
        ids=cleaned,
        evidence_group=group,
        weight=weight,
    )
