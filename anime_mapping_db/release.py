from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import zstandard as zstd

from anime_mapping_db.database import SCHEMA_VERSION

REPOSITORY = "anime-db-project/anime-mapping-db"


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
    shutil.copy2(runtime_path, runtime_asset)
    _compress(runtime_path, runtime_zst)
    _compress(evidence_path, evidence_zst)

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
        "providers": _providers(runtime_path),
        "assets": assets,
        "sources": sources,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    checksum_paths = [runtime_asset, runtime_zst, evidence_zst, manifest_path]
    checksums = "".join(
        f"{sha256_file(path)}  {path.name}\n" for path in checksum_paths
    )
    (output_dir / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    return manifest
