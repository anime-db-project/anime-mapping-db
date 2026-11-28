from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path

from anime_mapping_db.config import SOURCE_SPECS, MappingSourceSpec
from anime_mapping_db.release import source_fingerprint
from anime_mapping_db.updater import _bootstrap_path, _download, _sha256_file, _utc_now


def _filename(spec: MappingSourceSpec) -> str:
    key = hashlib.sha256(spec.name.encode()).hexdigest()[:24]
    return f"{key}.data"


def load_snapshot(
    directory: Path,
    specs: tuple[MappingSourceSpec, ...],
    *,
    allow_spec_changes: bool = False,
) -> dict[str, dict]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest["version"] != 1:
        raise ValueError("Unsupported source snapshot version")
    entries = manifest["sources"]
    if not isinstance(entries, list):
        raise ValueError("Invalid source snapshot manifest")
    if source_fingerprint(entries) != manifest["source_fingerprint"]:
        raise ValueError("Source snapshot fingerprint mismatch")
    configured = {spec.name: spec for spec in specs}
    result = {}
    seen = set()
    for item in entries:
        name = item["name"]
        if name in seen:
            raise ValueError(f"Duplicate source snapshot: {name}")
        seen.add(name)
        spec = configured.get(name)
        if spec is None:
            continue
        if allow_spec_changes and item["url"] != spec.url:
            continue
        if item["file"] != _filename(spec) or item["url"] != spec.url:
            raise ValueError(f"Snapshot source specification mismatch: {name}")
        path = directory / item["file"]
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing source snapshot: {name}")
        if _sha256_file(path) != item["sha256"]:
            raise ValueError(f"Corrupt source snapshot: {name}")
        result[name] = item
    missing = {spec.name for spec in specs if spec.required} - result.keys()
    if missing:
        raise ValueError(f"Missing required source snapshots: {sorted(missing)}")
    return result


def _normalize_media_index(path: Path) -> None:
    # The upstream updated_at field changes every refresh even when IDs do not.
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("Invalid media-index snapshot")
    fields = ("mal", "anidb", "kitsu", "simkl", "bangumi", "bangumi_confidence")
    normalized = {
        key: {field: row.get(field) for field in fields}
        for key, row in data.items()
        if isinstance(row, dict)
    }
    if not normalized:
        raise ValueError("Empty media-index projection")
    path.write_text(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _normalize_wikidata(path: Path, importer: str) -> None:
    # Only binding values are used by the importers. Ignore endpoint-specific
    # head/diagnostics and ordering, but keep rows grouped by QID.
    fields = (
        ("item", "bahamut", "mal", "anilist", "anidb")
        if importer == "wikidata_bahamut"
        else ("item", "prop", "id")
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    bindings = payload["results"]["bindings"]
    if not isinstance(bindings, list) or not bindings:
        raise ValueError("Empty Wikidata bindings")
    rows = set()
    for binding in bindings:
        if not isinstance(binding, dict):
            raise ValueError("Invalid Wikidata binding")
        values = tuple(
            str(binding.get(field, {}).get("value", "")).strip() for field in fields
        )
        if not values[0]:
            raise ValueError("Missing Wikidata item")
        rows.add(values)
    normalized = {
        "head": {"vars": list(fields)},
        "results": {
            "bindings": [
                {
                    field: {"value": value}
                    for field, value in zip(fields, row, strict=True)
                    if value
                }
                for row in sorted(rows)
            ]
        },
    }
    path.write_text(
        json.dumps(normalized, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def _validate_payload(spec: MappingSourceSpec, path: Path) -> None:
    # Reject malformed successful HTTP responses before replacing the last
    # known good snapshot. Full graph validation remains in the release job.
    from anime_mapping_db.importers import IMPORTERS

    if not spec.supplemental:
        if next(iter(IMPORTERS[spec.importer](path)), None) is None:
            raise ValueError("Source contains no mapping records")
    if spec.importer == "animeapi":
        with path.open(encoding="utf-8") as handle:
            if "myanimelist" not in handle.readline().strip().split("\t"):
                raise ValueError("Unexpected AnimeAPI TSV header")
    elif spec.supplemental or spec.url.endswith(".json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, (dict, list)) or not payload:
            raise ValueError("Empty or invalid JSON source")
    elif spec.url.endswith(".xml"):
        from xml.etree.ElementTree import iterparse

        for _, element in iterparse(path, events=("end",)):
            element.clear()
    elif spec.url.endswith(".jsonl"):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    json.loads(line)


def collect(directory: Path, specs: tuple[MappingSourceSpec, ...]) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    previous = {}
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        # New required sources may not exist in the old collection yet.
        from dataclasses import replace

        previous = load_snapshot(
            directory,
            tuple(replace(spec, required=False) for spec in specs),
            allow_spec_changes=True,
        )
    entries = []
    outcomes = []
    for spec in specs:
        filename = _filename(spec)
        target = directory / filename
        temp = directory / (filename + ".tmp")
        status = "unavailable"
        try:
            _download(spec, temp)
            if spec.importer == "media_index":
                _normalize_media_index(temp)
            elif spec.importer.startswith("wikidata_"):
                _normalize_wikidata(temp, spec.importer)
            elif spec.importer == "sovetromantica":
                from anime_mapping_db.importers.sovetromantica import normalize_snapshot

                normalize_snapshot(temp)
            elif spec.importer == "adkami":
                from anime_mapping_db.malsync_native import normalize_adkami

                normalize_adkami(temp)
            elif spec.importer.startswith("malsync_"):
                from anime_mapping_db.importers.malsync import normalize_snapshot

                normalize_snapshot(temp, spec.importer)
            if not temp.stat().st_size:
                raise ValueError("Empty source download")
            _validate_payload(spec, temp)
            sha = _sha256_file(temp)
            old = previous.get(spec.name)
            if old and old["sha256"] == sha:
                entries.append(old)
                status = "unchanged"
            else:
                os.replace(temp, target)
                status = "updated"
                entries.append(
                    {
                        "name": spec.name,
                        "url": spec.url,
                        "file": filename,
                        "sha256": sha,
                        "downloaded_at": _utc_now(),
                    }
                )
        except Exception as exc:
            logging.warning("Collection failed for %s: %s", spec.name, exc)
            if spec.name in previous:
                entries.append(previous[spec.name])
                status = "retained"
            elif spec.required:
                raise
            else:
                bootstrap = _bootstrap_path(spec)
                if bootstrap is not None:
                    target.write_bytes(bootstrap.read_bytes())
                    status = "bootstrap"
                    entries.append(
                        {
                            "name": spec.name,
                            "url": spec.url,
                            "file": filename,
                            "sha256": _sha256_file(target),
                            "downloaded_at": _utc_now(),
                        }
                    )
        finally:
            temp.unlink(missing_ok=True)
            outcomes.append(
                {
                    "source": spec.name,
                    "status": status,
                    "bytes": target.stat().st_size if target.exists() else 0,
                }
            )
    manifest = {
        "version": 1,
        "sources": sorted(entries, key=lambda item: item["name"]),
        "source_fingerprint": source_fingerprint(entries),
    }
    temporary_manifest = directory / "manifest.tmp"
    temporary_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary_manifest, manifest_path)
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
            handle.write("## Source collection\n\n| Source | Status | Bytes |\n")
            handle.write("| --- | --- | ---: |\n")
            for item in outcomes:
                handle.write(
                    f"| {item['source']} | {item['status']} | {item['bytes']:,} |\n"
                )
    return manifest


def compare(directory: Path, previous: dict, *, force: bool = False) -> bool:
    entries = load_snapshot(directory, SOURCE_SPECS)
    configured = {spec.name for spec in SOURCE_SPECS}
    published = {item["name"] for item in previous.get("sources", [])}
    missing = (published & configured) - entries.keys()
    if missing:
        raise ValueError(
            f"Refusing release with missing published sources: {sorted(missing)}"
        )
    current = source_fingerprint(list(entries.values()))
    return force or current != previous.get("source_fingerprint")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect and validate mapping snapshots"
    )
    parser.add_argument("command", choices=("collect", "compare", "verify-release"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--release", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.command == "collect":
        manifest = collect(args.directory, SOURCE_SPECS)
        print(manifest["source_fingerprint"])
    elif args.command == "compare":
        previous = json.loads(args.previous.read_text(encoding="utf-8"))
        force = os.environ.get("FORCE_RELEASE", "").casefold() == "true"
        build = compare(args.directory, previous, force=force)
        print(f"build={'true' if build else 'false'}")
    else:
        entries = load_snapshot(args.directory, SOURCE_SPECS)
        release = json.loads(args.release.read_text(encoding="utf-8"))
        if release["source_fingerprint"] != source_fingerprint(list(entries.values())):
            raise ValueError("Packaged release does not match collected snapshots")


if __name__ == "__main__":
    main()
