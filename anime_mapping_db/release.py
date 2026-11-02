from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
from collections import defaultdict
from contextlib import closing, contextmanager
from pathlib import Path

import zstandard as zstd

from anime_mapping_db.database import SCHEMA_VERSION
from anime_mapping_db.distribution import (
    STORAGE_PROFILE,
    compact_evidence_database,
    compact_runtime_database,
)

REPOSITORY = "anime-db-project/anime-mapping-db"
TEXT_EXPORT_SCHEMA_VERSION = 1
TEXT_EXPORT_FIELDS = (
    "source_provider",
    "source_id",
    "target_provider",
    "target_id",
    "confidence",
    "evidence_count",
    "evidence_group_count",
    "max_weight",
    "origin",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata(path: Path) -> dict[str, str]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=5.0)) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed for {path}: {integrity}")
        return {
            str(key): str(value)
            for key, value in conn.execute(
                "SELECT key, value FROM metadata ORDER BY key"
            )
        }


def _sources(evidence_path: Path) -> list[dict[str, object]]:
    uri = f"file:{evidence_path.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=5.0)) as conn:
        rows = conn.execute(
            """
            SELECT name, source_url, importer, license_note, sha256, downloaded_at,
                   record_count
            FROM datasets ORDER BY name
            """
        ).fetchall()
    return [
        {
            "name": str(name),
            "source_url": str(source_url),
            "importer": str(importer),
            "license_note": str(license_note),
            "sha256": str(sha256),
            "downloaded_at": str(downloaded_at),
            "record_count": int(record_count),
        }
        for name, source_url, importer, license_note, sha256, downloaded_at, record_count in rows
    ]


def _providers(runtime_path: Path) -> dict[str, int]:
    uri = f"file:{runtime_path.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=5.0)) as conn:
        rows = conn.execute(
            "SELECT provider, COUNT(*) FROM nodes GROUP BY provider ORDER BY provider"
        ).fetchall()
    return {str(provider): int(count) for provider, count in rows}


def source_fingerprint(sources: list[dict[str, object]]) -> str:
    payload = [
        [str(item["name"]), str(item["sha256"])]
        for item in sorted(sources, key=lambda item: str(item["name"]))
    ]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _compress(source: Path, destination: Path, *, level: int = 9) -> None:
    compressor = zstd.ZstdCompressor(level=level, threads=-1)
    with source.open("rb") as src, destination.open("wb") as dst:
        compressor.copy_stream(src, dst, size=source.stat().st_size)


@contextmanager
def _zstd_text_writer(path: Path, *, level: int = 9):
    compressor = zstd.ZstdCompressor(level=level, threads=-1)
    with path.open("wb") as raw:
        with compressor.stream_writer(raw, closefd=False) as compressed:
            text = io.TextIOWrapper(compressed, encoding="utf-8", newline="")
            try:
                yield text
            finally:
                text.flush()
                text.detach()


def _load_overrides(
    conn: sqlite3.Connection,
) -> dict[tuple[str, str, str], dict[str, set[str]]]:
    routes: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(
        lambda: {"accept": set(), "reject": set()}
    )
    try:
        rows = conn.execute(
            """
            SELECT source_provider, source_id, target_provider, target_id, action
            FROM mapping_overrides
            ORDER BY source_provider, source_id, target_provider, target_id
            """
        )
    except sqlite3.OperationalError:
        return {}
    for source_provider, source_id, target_provider, target_id, action in rows:
        action = str(action)
        if action not in {"accept", "reject"}:
            continue
        routes[(str(source_provider), str(source_id), str(target_provider))][
            action
        ].add(str(target_id))
    return dict(routes)


def _load_override_metrics(
    conn: sqlite3.Connection,
) -> dict[tuple[str, str, str, str], tuple[int, int, int, int]]:
    try:
        rows = conn.execute(
            """
            SELECT
                o.source_provider, o.source_id, o.target_provider, o.target_id,
                e.confidence, e.evidence_count, e.evidence_group_count, e.max_weight
            FROM mapping_overrides AS o
            JOIN nodes AS source
              ON source.provider=o.source_provider AND source.external_id=o.source_id
            JOIN nodes AS target
              ON target.provider=o.target_provider AND target.external_id=o.target_id
            JOIN edges AS e
              ON e.a_node=min(source.id, target.id)
             AND e.b_node=max(source.id, target.id)
            WHERE o.action='accept'
            ORDER BY o.source_provider, o.source_id, o.target_provider, o.target_id
            """
        )
    except sqlite3.OperationalError:
        return {}
    return {
        (str(source_provider), str(source_id), str(target_provider), str(target_id)): (
            int(confidence),
            int(evidence_count),
            int(evidence_group_count),
            int(max_weight),
        )
        for (
            source_provider,
            source_id,
            target_provider,
            target_id,
            confidence,
            evidence_count,
            evidence_group_count,
            max_weight,
        ) in rows
    }


def _write_text_exports(
    runtime_path: Path,
    tsv_path: Path,
    jsonl_path: Path,
) -> int:
    """Write resolver-safe directed routes as compressed TSV and JSONL.

    The export mirrors single-seed resolver behavior: accepted graph edges are
    filtered by directional conflicts, then directional manual overrides are
    applied. Only routes with exactly one effective target ID are exported.
    """

    uri = f"file:{runtime_path.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=5.0)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA temp_store=FILE")
        overrides = _load_overrides(conn)
        override_metrics = _load_override_metrics(conn)
        rows = conn.execute(
            """
            WITH directed AS (
                SELECT
                    e.a_node AS source_node,
                    e.b_node AS target_node,
                    e.confidence,
                    e.evidence_count,
                    e.evidence_group_count,
                    e.max_weight
                FROM edges AS e
                WHERE e.status='accepted'
                UNION ALL
                SELECT
                    e.b_node AS source_node,
                    e.a_node AS target_node,
                    e.confidence,
                    e.evidence_count,
                    e.evidence_group_count,
                    e.max_weight
                FROM edges AS e
                WHERE e.status='accepted'
            )
            SELECT
                source.provider,
                source.external_id,
                target.provider,
                target.external_id,
                d.confidence,
                d.evidence_count,
                d.evidence_group_count,
                d.max_weight
            FROM directed AS d
            JOIN nodes AS source ON source.id=d.source_node
            JOIN nodes AS target ON target.id=d.target_node
            LEFT JOIN conflicts AS c
              ON c.source_node=d.source_node
             AND c.target_provider=target.provider
            WHERE c.source_node IS NULL
            ORDER BY
                source.provider, source.external_id,
                target.provider, target.external_id
            """
        )

        with (
            _zstd_text_writer(tsv_path) as tsv_handle,
            _zstd_text_writer(jsonl_path) as jsonl_handle,
        ):
            tsv_writer = csv.writer(
                tsv_handle,
                delimiter="\t",
                lineterminator="\n",
                quoting=csv.QUOTE_MINIMAL,
            )
            tsv_writer.writerow(TEXT_EXPORT_FIELDS)
            route_count = 0
            processed: set[tuple[str, str, str]] = set()
            current_key: tuple[str, str, str] | None = None
            candidates: dict[str, tuple[int, int, int, int]] = {}

            def emit(
                key: tuple[str, str, str] | None,
                route_candidates: dict[str, tuple[int, int, int, int]],
            ) -> None:
                nonlocal route_count
                if key is None:
                    return
                processed.add(key)
                route_override = overrides.get(key, {})
                accepts = route_override.get("accept", set())
                rejects = route_override.get("reject", set())
                origin = "evidence"
                metrics: tuple[int, int, int, int] | None

                if accepts:
                    if len(accepts) != 1:
                        return
                    target_id = next(iter(accepts))
                    metrics = route_candidates.get(target_id) or override_metrics.get(
                        (*key, target_id)
                    )
                    origin = "override"
                else:
                    effective = {
                        target_id: item
                        for target_id, item in route_candidates.items()
                        if target_id not in rejects
                    }
                    if len(effective) != 1:
                        return
                    target_id, metrics = next(iter(effective.items()))

                source_provider, source_id, target_provider = key
                numeric = metrics or (None, None, None, None)
                values = (
                    source_provider,
                    source_id,
                    target_provider,
                    target_id,
                    *numeric,
                    origin,
                )
                tsv_writer.writerow(
                    ["" if value is None else value for value in values]
                )
                jsonl_handle.write(
                    json.dumps(
                        dict(zip(TEXT_EXPORT_FIELDS, values, strict=True)),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                route_count += 1

            for row in rows:
                source_provider, source_id, target_provider, target_id = map(
                    str, row[:4]
                )
                key = (source_provider, source_id, target_provider)
                if current_key is not None and key != current_key:
                    emit(current_key, candidates)
                    candidates = {}
                current_key = key
                candidates[target_id] = tuple(int(value) for value in row[4:8])

            emit(current_key, candidates)
            for key in sorted(overrides):
                if key not in processed:
                    emit(key, {})

    return route_count


def package_release(
    runtime_path: Path,
    evidence_path: Path,
    output_dir: Path,
    *,
    release_tag: str,
) -> dict[str, object]:
    runtime_path = Path(runtime_path)
    evidence_path = Path(evidence_path)
    output_dir = Path(output_dir)
    if not runtime_path.is_file() or not evidence_path.is_file():
        raise FileNotFoundError("Both runtime and evidence databases are required")

    runtime_meta = _metadata(runtime_path)
    evidence_meta = _metadata(evidence_path)
    if runtime_meta.get("database_role") != "runtime":
        raise RuntimeError("mappings.db is not a runtime mapping database")
    if evidence_meta.get("database_role") != "evidence":
        raise RuntimeError("mappings-evidence.db is not an evidence database")
    if int(runtime_meta.get("schema_version", 0)) != SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported runtime schema {runtime_meta.get('schema_version')}; expected {SCHEMA_VERSION}"
        )
    if evidence_meta.get("schema_version") != runtime_meta.get("schema_version"):
        raise RuntimeError("Runtime and evidence schema versions differ")

    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.is_file():
            child.unlink()

    runtime_asset = output_dir / "mappings.db"
    runtime_zst = output_dir / "mappings.db.zst"
    evidence_zst = output_dir / "mappings-evidence.db.zst"
    compact_evidence = output_dir / ".mappings-evidence.compact.db"
    tsv_zst = output_dir / "mappings.tsv.zst"
    jsonl_zst = output_dir / "mappings.jsonl.zst"

    compact_runtime_database(runtime_path, runtime_asset)
    compact_evidence_database(evidence_path, compact_evidence)
    try:
        _compress(runtime_asset, runtime_zst)
        _compress(compact_evidence, evidence_zst)
    finally:
        compact_evidence.unlink(missing_ok=True)
    # Text exports retain the complete build-time edge metrics and are therefore
    # produced from the audited staging database rather than the compact copy.
    text_route_count = _write_text_exports(runtime_path, tsv_zst, jsonl_zst)

    sources = _sources(evidence_path)
    assets = {
        "runtime": {
            "name": runtime_asset.name,
            "size": runtime_asset.stat().st_size,
            "sha256": sha256_file(runtime_asset),
        },
        "runtime_zstd": {
            "name": runtime_zst.name,
            "size": runtime_zst.stat().st_size,
            "sha256": sha256_file(runtime_zst),
        },
        "evidence_zstd": {
            "name": evidence_zst.name,
            "size": evidence_zst.stat().st_size,
            "sha256": sha256_file(evidence_zst),
        },
        "runtime_tsv_zstd": {
            "name": tsv_zst.name,
            "size": tsv_zst.stat().st_size,
            "sha256": sha256_file(tsv_zst),
            "format": "tsv",
            "compression": "zstd",
            "schema_version": TEXT_EXPORT_SCHEMA_VERSION,
            "rows": text_route_count,
        },
        "runtime_jsonl_zstd": {
            "name": jsonl_zst.name,
            "size": jsonl_zst.stat().st_size,
            "sha256": sha256_file(jsonl_zst),
            "format": "jsonl",
            "compression": "zstd",
            "schema_version": TEXT_EXPORT_SCHEMA_VERSION,
            "rows": text_route_count,
        },
    }
    counts = {
        key: int(runtime_meta.get(key, 0))
        for key in (
            "datasets",
            "records",
            "evidence",
            "edges",
            "accepted_edges",
            "conflicts",
            "overrides",
        )
    }
    manifest: dict[str, object] = {
        "repository": REPOSITORY,
        "release_tag": release_tag,
        "schema_version": SCHEMA_VERSION,
        "built_at": runtime_meta.get("built_at", ""),
        "last_source_check_at": runtime_meta.get("last_source_check_at", ""),
        "source_fingerprint": source_fingerprint(sources),
        "counts": counts,
        "providers": _providers(runtime_asset),
        "storage": {
            "profile": STORAGE_PROFILE,
            "runtime_edge_lookup": "pk-plus-reverse-accepted",
            "evidence_edge_storage": "record_nodes-view",
        },
        "text_export": {
            "schema_version": TEXT_EXPORT_SCHEMA_VERSION,
            "semantics": "directed single-seed resolver routes",
            "fields": list(TEXT_EXPORT_FIELDS),
            "rows": text_route_count,
        },
        "assets": assets,
        "sources": sources,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checksum_paths = [
        runtime_asset,
        runtime_zst,
        evidence_zst,
        tsv_zst,
        jsonl_zst,
        manifest_path,
    ]
    checksums = "".join(
        f"{sha256_file(path)}  {path.name}\n" for path in checksum_paths
    )
    (output_dir / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    return manifest
