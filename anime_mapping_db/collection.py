"""Fan out source collection and assemble one validated release input snapshot."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from anime_mapping_db.catalogue_report import catalogue_stats, shrink_reason
from anime_mapping_db.config import SOURCE_SPECS, MappingSourceSpec
from anime_mapping_db.release import source_fingerprint
from anime_mapping_db.snapshots import _filename, collect, load_snapshot
from anime_mapping_db.updater import _utc_now


def source_key(spec: MappingSourceSpec) -> str:
    return _filename(spec).removesuffix(".data")


def _previous_outcomes(directory: Path | None) -> dict:
    if directory is None or not (directory / "collection-report.json").exists():
        return {}
    report = json.loads((directory / "collection-report.json").read_text("utf-8"))
    return {
        item["source"]: {
            **item,
            "last_attempted_at": item.get("last_attempted_at", report["checked_at"]),
        }
        for item in report["sources"]
    }


def _due(spec: MappingSourceSpec, old: dict, now: datetime) -> bool:
    if not old or not spec.collection_interval_hours:
        return True
    if old.get("source_url", spec.url) != spec.url:
        return True
    last = old.get("last_attempted_at")
    if not last:
        return True
    try:
        checked = datetime.fromisoformat(last.replace("Z", "+00:00"))
        age = (now - checked).total_seconds()
    except (ValueError, TypeError, AttributeError):
        return True
    return age < 0 or age >= spec.collection_interval_hours * 3600


def matrix(
    specs: tuple[MappingSourceSpec, ...],
    previous: Path | None = None,
    *,
    force: bool = False,
    now: datetime | None = None,
) -> dict:
    old = _previous_outcomes(previous)
    now = now or datetime.now(timezone.utc)
    return {
        "include": [
            {
                "name": spec.name,
                "key": source_key(spec),
                "mode": spec.collection_mode,
                "due": force or _due(spec, old.get(spec.name, {}), now),
                "interval_hours": spec.collection_interval_hours,
            }
            for spec in specs
        ]
    }


def collect_one(
    directory: Path, spec: MappingSourceSpec, *, deferred: bool = False
) -> dict:
    if deferred:
        directory.mkdir(parents=True, exist_ok=True)
        manifest = {
            "version": 1,
            "sources": [],
            "source_fingerprint": source_fingerprint([]),
        }
        (directory / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        (directory / "collection-report.json").write_text(
            json.dumps(
                {
                    "checked_at": _utc_now(),
                    "sources": [
                        {"source": spec.name, "status": "deferred", "bytes": 0}
                    ],
                }
            ),
            encoding="utf-8",
        )
        return manifest
    # A network failure is an outcome, not a failed matrix job. The assembler
    # enforces required sources after it has access to the previous snapshot.
    return collect(directory, (replace(spec, required=False),))


def assemble(
    directory: Path,
    parts: Path,
    specs: tuple[MappingSourceSpec, ...],
    *,
    allow_shrink: frozenset[str] = frozenset(),
) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    previous = {}
    if (directory / "manifest.json").exists():
        previous = load_snapshot(
            directory,
            tuple(replace(spec, required=False) for spec in specs),
            allow_spec_changes=True,
        )

    previous_outcomes = _previous_outcomes(directory)

    # Validate every part before making any changes to the combined snapshot.
    entries = []
    outcomes = []
    copies = []
    for spec in specs:
        part = parts / f"mapping-source-{source_key(spec)}"
        report = json.loads((part / "collection-report.json").read_text("utf-8"))
        result = report["sources"]
        if len(result) != 1 or result[0]["source"] != spec.name:
            raise ValueError(f"Unexpected source report for {spec.name}")
        status = result[0]["status"]
        if status not in {
            "updated",
            "unchanged",
            "bootstrap",
            "unavailable",
            "deferred",
        }:
            raise ValueError(f"Invalid collection status for {spec.name}")
        fresh = load_snapshot(part, (replace(spec, required=False),)).get(spec.name)
        if (fresh is None) != (status in {"unavailable", "deferred"}):
            raise ValueError(f"Collection report disagrees with data: {spec.name}")
        old = previous.get(spec.name)
        fresh_metrics = catalogue_stats(
            spec.importer, part / fresh["file"] if fresh is not None else None
        )
        old_metrics = catalogue_stats(
            spec.importer, directory / old["file"] if old is not None else None
        )
        warning = shrink_reason(old_metrics, fresh_metrics)
        reason = None
        if status == "deferred":
            if not previous_outcomes.get(spec.name, {}).get("last_attempted_at"):
                raise ValueError(f"No previous attempt for deferred source: {spec.name}")
            selected = old
            reason = "collection_interval"
        elif old is not None and (fresh is None or status == "bootstrap"):
            reason = "source_unavailable" if fresh is None else "bootstrap_fallback"
            selected = old
            status = "retained"
        elif warning and spec.importer not in allow_shrink:
            selected = old
            status = "retained"
            reason = warning
            logging.warning("Retaining %s: %s", spec.name, warning)
        elif old is not None and fresh is not None and old["sha256"] == fresh["sha256"]:
            selected = old
            status = "unchanged"
        elif fresh is not None:
            selected = fresh
            copies.append((part / fresh["file"], directory / fresh["file"]))
        else:
            selected = None
        if selected is None and spec.required:
            raise RuntimeError(f"Required source has no valid snapshot: {spec.name}")
        if selected is not None:
            entries.append(selected)
        metrics = old_metrics if selected is old else fresh_metrics
        outcomes.append(
            {
                **result[0],
                "status": status,
                "collection_mode": spec.collection_mode,
                "collection_interval_hours": spec.collection_interval_hours,
                "source_url": spec.url,
                "last_attempted_at": (
                    previous_outcomes[spec.name]["last_attempted_at"]
                    if status == "deferred"
                    else report["checked_at"]
                ),
                "catalogue": metrics,
                "attempted_catalogue": fresh_metrics,
                "retention_reason": reason,
                "shrink_warning": warning,
                "bytes": (
                    (directory / selected["file"]).stat().st_size
                    if selected is old and old is not None
                    else (result[0]["bytes"] if selected is not None else 0)
                ),
            }
        )

    for source, target in copies:
        temp = target.with_suffix(".tmp")
        shutil.copyfile(source, temp)
        os.replace(temp, target)
    manifest = {
        "version": 1,
        "sources": sorted(entries, key=lambda item: item["name"]),
        "source_fingerprint": source_fingerprint(entries),
    }
    temp = directory / "manifest.tmp"
    temp.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temp, directory / "manifest.json")
    active = {item["file"] for item in entries}
    for path in directory.glob("*.data"):
        if path.name not in active:
            path.unlink()
    load_snapshot(directory, specs)
    report = {"checked_at": _utc_now(), "sources": outcomes}
    (directory / "collection-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(
                "## Combined source collection\n\n"
                "| Source | Mode | Status | Bytes | Native IDs | With external ID |\n"
            )
            handle.write("| --- | --- | --- | ---: | ---: | ---: |\n")
            for item in outcomes:
                metrics = item["catalogue"] or {}
                handle.write(
                    f"| {item['source']} | {item['collection_mode']} | "
                    f"{item['status']} | {item['bytes']:,} | "
                    f"{metrics.get('native_ids', '—')} | "
                    f"{metrics.get('with_external_id', '—')} |\n"
                )
            for item in outcomes:
                if item["shrink_warning"]:
                    handle.write(f"\n- {item['source']}: {item['shrink_warning']}")
                    handle.write(f" ({item['status']})\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("matrix", "collect", "assemble"))
    parser.add_argument("--source")
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--parts", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--defer", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.command == "matrix":
        planned = matrix(SOURCE_SPECS, args.previous, force=args.force)
        print("matrix=" + json.dumps(planned, separators=(",", ":")))
    elif args.command == "collect":
        spec = next(
            (spec for spec in SOURCE_SPECS if source_key(spec) == args.source), None
        )
        if spec is None or args.directory is None:
            parser.error("collect requires a known --source and --directory")
        collect_one(args.directory, spec, deferred=args.defer)
    else:
        if args.directory is None or args.parts is None:
            parser.error("assemble requires --parts and --directory")
        allow_shrink = frozenset(
            item.strip()
            for item in os.environ.get("MAPPINGS_ALLOW_CATALOGUE_SHRINK", "").split(",")
            if item.strip()
        )
        known = {spec.importer for spec in SOURCE_SPECS}
        if allow_shrink - known:
            parser.error("Unknown importer in MAPPINGS_ALLOW_CATALOGUE_SHRINK")
        manifest = assemble(
            args.directory, args.parts, SOURCE_SPECS, allow_shrink=allow_shrink
        )
        print(manifest["source_fingerprint"])


if __name__ == "__main__":
    main()
