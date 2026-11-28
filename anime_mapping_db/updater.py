from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from contextlib import closing

import httpx

from anime_mapping_db.anchors import materialize_anchor_index
from anime_mapping_db.aniliberty import download_aniliberty
from anime_mapping_db.annict_api import download_annict
from anime_mapping_db.anime365 import download_anime365
from anime_mapping_db.malsync_native import download_animelib, download_docchi
from anime_mapping_db.malsync_web import WEB_SOURCES, download_web_catalogue
from anime_mapping_db.tioanime import download_tioanime
from anime_mapping_db.yummyani import download_yummyani
from anime_mapping_db.config import (
    SOURCE_SPECS,
    MappingSourceSpec,
    mappings_db_path,
    mappings_evidence_db_path,
    mappings_keep_downloads,
    mappings_keep_previous,
    mappings_request_timeout_seconds,
    mappings_update_max_age_hours,
    mappings_wikidata_check_interval_hours,
    source_preflight,
)
from anime_mapping_db.database import (
    MappingBuildStats,
    MappingDatabase,
    MappingDatabaseBuilder,
)
from anime_mapping_db.importers import IMPORTERS, SUPPLEMENTAL_IMPORTERS
from anime_mapping_db.resolver import copy_mapping_overrides

from anime_mapping_db.crawler_policy import retry_after, user_agent

USER_AGENT = user_agent()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bootstrap_path(spec: MappingSourceSpec) -> Path | None:
    if spec.importer != "wikidata_bahamut":
        return None
    path = Path(__file__).resolve().parent / "bootstrap" / "wikidata-bahamut.json"
    return path if path.is_file() else None


_NATIVE_DOWNLOADERS = {
    "docchi": ("single", download_docchi),
    "animelib": ("paginated", download_animelib),
    "yummyani": ("paginated", download_yummyani),
    "annict_api": ("paginated", download_annict),
    "anime365": ("paginated", download_anime365),
    "aniliberty": ("paginated", download_aniliberty),
}


def _download(spec: MappingSourceSpec, target: Path) -> str:
    reason = source_preflight(spec)
    if reason:
        raise ValueError(f"Source preflight: {reason}")
    if spec.importer in WEB_SOURCES:
        download_web_catalogue(
            spec.importer, spec.url, target, timeout=mappings_request_timeout_seconds()
        )
        return _sha256_file(target)
    if spec.importer == "tioanime" and spec.collection_mode == "paginated":
        download_tioanime(spec.url, target, timeout=mappings_request_timeout_seconds())
        return _sha256_file(target)
    registration = _NATIVE_DOWNLOADERS.get(spec.importer)
    if registration:
        mode, downloader = registration
        if spec.collection_mode != mode:
            raise ValueError(f"Incorrect collection mode for {spec.name}: {mode}")
        downloader(spec.url, target, timeout=mappings_request_timeout_seconds())
        return _sha256_file(target)
    if spec.collection_mode != "single":
        raise ValueError(f"No paginated collector for {spec.name}")
    timeout = httpx.Timeout(
        connect=30.0,
        read=mappings_request_timeout_seconds(),
        write=30.0,
        pool=30.0,
    )
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/sparql-results+json"
        if spec.importer.startswith("wikidata_")
        else "*/*",
    }
    urls = (spec.url, *spec.fallback_urls)
    with httpx.Client(
        timeout=timeout, follow_redirects=True, headers=headers
    ) as client:
        errors: list[str] = []
        actual = ""
        for url_index, url in enumerate(urls):
            last_error: Exception | None = None
            for attempt in range(3):
                digest = hashlib.sha256()
                target.unlink(missing_ok=True)
                try:
                    with client.stream("GET", url) as response:
                        response.raise_for_status()
                        with target.open("wb") as handle:
                            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                                if not chunk:
                                    continue
                                digest.update(chunk)
                                handle.write(chunk)
                    actual = digest.hexdigest()
                    last_error = None
                    break
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    status = exc.response.status_code
                    retryable = status == 429 or 500 <= status < 600
                    if not retryable or attempt == 2:
                        break
                    delay = retry_after(
                        exc.response, 65.0 if status == 429 else 5.0 * (attempt + 1)
                    )
                    if status == 429 and (attempt > 0 or delay > 65.0):
                        break
                    delay = max(1.0, min(delay, 65.0))
                    logging.warning(
                        "Mapping source returned HTTP %d; retrying %s endpoint %d/%d in %.1fs",
                        status,
                        spec.name,
                        url_index + 1,
                        len(urls),
                        delay,
                    )
                    time.sleep(delay)
                except Exception as exc:
                    last_error = exc
                    break
            if last_error is None and actual:
                if url_index:
                    logging.warning(
                        "Mapping source fallback endpoint used: %s (%d/%d)",
                        spec.name,
                        url_index + 1,
                        len(urls),
                    )
                break
            target.unlink(missing_ok=True)
            errors.append(f"{url}: {type(last_error).__name__}: {last_error}")
        else:
            raise RuntimeError(
                f"All endpoints failed for {spec.name}: " + " | ".join(errors)
            )

        if spec.checksum_url:
            checksum_response = client.get(spec.checksum_url)
            checksum_response.raise_for_status()
            expected = checksum_response.text.strip().split()[0].casefold()
            if expected and actual.casefold() != expected:
                raise RuntimeError(
                    f"Checksum mismatch for {spec.name}: expected {expected}, got {actual}"
                )
    return actual


def _dataset_state(path: Path) -> dict[str, tuple[str, str]]:
    if not path.is_file():
        return {}
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=5.0)) as conn:
            return {
                str(name): (str(sha256), str(downloaded_at))
                for name, sha256, downloaded_at in conn.execute(
                    "SELECT name, sha256, downloaded_at FROM datasets"
                )
            }
    except sqlite3.DatabaseError:
        return {}


def _checked_at_timestamp(value: str) -> float | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _source_interval_hours(spec: MappingSourceSpec) -> float:
    if spec.check_interval == "wikidata":
        return mappings_wikidata_check_interval_hours()
    return mappings_update_max_age_hours()


def _source_due(
    spec: MappingSourceSpec,
    state: dict[str, tuple[str, str]],
    *,
    now: float | None = None,
) -> bool:
    current = state.get(spec.name)
    if current is None:
        return True
    checked_at = _checked_at_timestamp(current[1])
    if checked_at is None:
        return True
    current_time = time.time() if now is None else float(now)
    age_seconds = max(0.0, current_time - checked_at)
    return age_seconds >= _source_interval_hours(spec) * 3600.0


def _is_stale(path: Path) -> bool:
    state = _dataset_state(path)
    return not state or any(_source_due(spec, state) for spec in SOURCE_SPECS)


def _acquire_lock(lock_path: Path) -> int | None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            if time.time() - lock_path.stat().st_mtime > 6 * 3600:
                lock_path.unlink(missing_ok=True)
                return os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except OSError:
            pass
        return None


def _touch_checked_sources(path: Path, names: set[str], checked_at: str) -> None:
    if not names or not path.is_file():
        return
    with closing(sqlite3.connect(path, timeout=5.0)) as conn:
        conn.executemany(
            "UPDATE datasets SET downloaded_at=? WHERE name=?",
            [(checked_at, name) for name in sorted(names)],
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('last_source_check_at', ?)",
            (checked_at,),
        )
        conn.commit()


def _touch_runtime_check(path: Path, checked_at: str) -> None:
    if not path.is_file():
        return
    try:
        with closing(sqlite3.connect(path, timeout=5.0)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES('last_source_check_at', ?)",
                (checked_at,),
            )
            conn.commit()
    except sqlite3.DatabaseError:
        logging.exception("Could not update mappings runtime check timestamp")


def _download_path(work_dir: Path, index: int, spec: MappingSourceSpec) -> Path:
    suffix = Path(spec.url.split("?", 1)[0]).suffix or ".data"
    return work_dir / f"{index:02d}-{spec.importer}{suffix}"


def update_mapping_database(
    *, force: bool = False, snapshot_dir: Path | None = None
) -> MappingBuildStats | None:
    if snapshot_dir is not None:
        force = True
    db_path = mappings_db_path()
    evidence_path = mappings_evidence_db_path()
    state = _dataset_state(evidence_path)
    due_specs = (
        list(SOURCE_SPECS)
        if force or not state
        else [spec for spec in SOURCE_SPECS if _source_due(spec, state)]
    )
    runtime_rebuild_only = not db_path.is_file() and bool(state)
    if not due_specs and not runtime_rebuild_only:
        return None

    db_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = db_path.with_suffix(db_path.suffix + ".lock")
    lock_fd = _acquire_lock(lock_path)
    if lock_fd is None:
        logging.info("Mapping update skipped: another updater holds %s", lock_path)
        return None
    os.close(lock_fd)

    new_path = db_path.with_suffix(db_path.suffix + ".new")
    evidence_new_path = evidence_path.with_suffix(evidence_path.suffix + ".new")
    previous_path = db_path.with_suffix(db_path.suffix + ".previous")
    evidence_previous_path = evidence_path.with_suffix(
        evidence_path.suffix + ".previous"
    )
    downloads_dir = db_path.parent / "downloads"
    work_dir = db_path.parent / ".update"
    work_dir.mkdir(parents=True, exist_ok=True)
    checked_at = _utc_now()
    staged: dict[str, tuple[Path, str]] = {}
    failed_optional: dict[str, str] = {}
    changed_sources: set[str] = set()
    snapshot_dates: dict[str, str] = {}

    try:
        if snapshot_dir is not None:
            from anime_mapping_db.snapshots import load_snapshot

            manifest = load_snapshot(snapshot_dir, SOURCE_SPECS)
            for spec in SOURCE_SPECS:
                item = manifest.get(spec.name)
                if item is None:
                    failed_optional[spec.name] = "No collected snapshot"
                    continue
                path = _download_path(work_dir, SOURCE_SPECS.index(spec), spec)
                shutil.copyfile(snapshot_dir / item["file"], path)
                staged[spec.name] = (path, item["sha256"])
                snapshot_dates[spec.name] = item["downloaded_at"]
                if state.get(spec.name, ("", ""))[0] != item["sha256"]:
                    changed_sources.add(spec.name)
            base_changed = any(
                spec.name in changed_sources and not spec.supplemental
                for spec in SOURCE_SPECS
            )
        else:
            for spec in due_specs:
                index = SOURCE_SPECS.index(spec)
                download_path = _download_path(work_dir, index, spec)
                download_path.unlink(missing_ok=True)
                logging.info("Mapping source check: %s", spec.name)
                try:
                    sha256 = _download(spec, download_path)
                    staged[spec.name] = (download_path, sha256)
                    previous = state.get(spec.name)
                    if previous is None or previous[0].casefold() != sha256.casefold():
                        changed_sources.add(spec.name)
                except Exception as exc:
                    download_path.unlink(missing_ok=True)
                    if spec.required:
                        raise RuntimeError(
                            f"Required mapping source failed: {spec.name}: {exc}"
                        ) from exc
                    failed_optional[spec.name] = f"{type(exc).__name__}: {exc}"
                    logging.warning(
                        "Optional mapping source unavailable during check: %s: %s",
                        spec.name,
                        exc,
                    )

            # Supplemental aggregates depend on the accepted base graph. If any direct
            # source changed, refresh/reprocess them even when their normal check interval
            # has not expired so anchor validation always uses the current graph.
            base_changed = any(
                spec.name in changed_sources and not spec.supplemental
                for spec in SOURCE_SPECS
            )
            if base_changed:
                for spec in SOURCE_SPECS:
                    if not spec.supplemental or spec.name in staged:
                        continue
                    index = SOURCE_SPECS.index(spec)
                    download_path = _download_path(work_dir, index, spec)
                    download_path.unlink(missing_ok=True)
                    logging.info("Supplemental mapping source refresh: %s", spec.name)
                    try:
                        sha256 = _download(spec, download_path)
                        staged[spec.name] = (download_path, sha256)
                        previous = state.get(spec.name)
                        if (
                            previous is None
                            or previous[0].casefold() != sha256.casefold()
                        ):
                            changed_sources.add(spec.name)
                    except Exception as exc:
                        download_path.unlink(missing_ok=True)
                        failed_optional[spec.name] = f"{type(exc).__name__}: {exc}"
                        logging.warning(
                            "Supplemental mapping source unavailable during base refresh: %s: %s",
                            spec.name,
                            exc,
                        )

        successful_checks = set(staged)
        if (
            db_path.is_file()
            and evidence_path.is_file()
            and not force
            and not changed_sources
        ):
            anchor_stats = materialize_anchor_index(db_path)
            logging.info(
                "Mapping anchor index current: entities=%d nodes=%d redirects=%d",
                anchor_stats.entities,
                anchor_stats.nodes,
                anchor_stats.redirects,
            )
            _touch_checked_sources(evidence_path, successful_checks, checked_at)
            _touch_runtime_check(db_path, checked_at)
            logging.info(
                "Mapping sources unchanged; runtime/evidence databases kept in place (%d checked)",
                len(successful_checks),
            )
            return None

        new_path.unlink(missing_ok=True)
        evidence_new_path.unlink(missing_ok=True)
        required_loaded: set[str] = set()
        with MappingDatabaseBuilder(
            new_path, evidence_path=evidence_new_path
        ) as builder:

            def ingest_regular_source(index: int, spec: MappingSourceSpec) -> int:
                record_count = 0
                staged_item = staged.get(spec.name)
                if staged_item is not None:
                    download_path, sha256 = staged_item
                    logging.info("Mapping source ingest: %s", spec.name)
                    importer = IMPORTERS[spec.importer]
                    record_count = builder.ingest_dataset(
                        spec,
                        importer(download_path),
                        sha256=sha256,
                        downloaded_at=snapshot_dates.get(spec.name, checked_at),
                    )
                    if record_count <= 0:
                        if snapshot_dir is not None and spec.name in state:
                            raise RuntimeError(
                                f"Previously published source is empty: {spec.name}"
                            )
                        if spec.required:
                            raise RuntimeError(
                                f"Required mapping source produced zero usable records: {spec.name}"
                            )
                        failed_optional[spec.name] = (
                            "source produced zero usable mapping records"
                        )
                    elif mappings_keep_downloads():
                        downloads_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(download_path, downloads_dir / download_path.name)
                elif snapshot_dir is not None:
                    return 0
                elif evidence_path.is_file() and spec.name in state:
                    record_count = builder.copy_dataset_from(evidence_path, spec.name)
                    if record_count:
                        logging.info(
                            "Mapping source carried forward without network check: %s — %d records",
                            spec.name,
                            record_count,
                        )
                elif spec.name in failed_optional:
                    bootstrap_path = _bootstrap_path(spec)
                    if bootstrap_path is not None:
                        bootstrap_sha = _sha256_file(bootstrap_path)
                        importer = IMPORTERS[spec.importer]
                        record_count = builder.ingest_dataset(
                            spec,
                            importer(bootstrap_path),
                            sha256=bootstrap_sha,
                            downloaded_at=checked_at,
                        )
                        if record_count > 0:
                            failed_optional[spec.name] += (
                                "; bundled CC0 bootstrap snapshot used"
                            )
                            changed_sources.add(spec.name)
                            logging.warning(
                                "Mapping source bootstrap fallback used: %s — %d records",
                                spec.name,
                                record_count,
                            )
                else:
                    download_path = _download_path(work_dir, index, spec)
                    download_path.unlink(missing_ok=True)
                    try:
                        sha256 = _download(spec, download_path)
                        importer = IMPORTERS[spec.importer]
                        record_count = builder.ingest_dataset(
                            spec,
                            importer(download_path),
                            sha256=sha256,
                            downloaded_at=checked_at,
                        )
                    finally:
                        download_path.unlink(missing_ok=True)

                if record_count > 0:
                    logging.info(
                        "Mapping source indexed: %s — %d records",
                        spec.name,
                        record_count,
                    )
                    if spec.required:
                        required_loaded.add(spec.name)
                return record_count

            # Phase 1: independent/direct sources establish the accepted graph.
            for index, spec in enumerate(SOURCE_SPECS):
                if spec.supplemental:
                    continue
                ingest_regular_source(index, spec)

            expected_required = {
                spec.name
                for spec in SOURCE_SPECS
                if spec.required and not spec.supplemental
            }
            missing_required = expected_required - required_loaded
            if missing_required:
                raise RuntimeError(
                    "Required mapping sources missing: "
                    + ", ".join(sorted(missing_required))
                )

            # Materialize a provisional runtime graph. Supplemental aggregate rows are
            # allowed to enrich only rows backed by two accepted, conflict-free anchors.
            builder.finalize(built_at=checked_at)

            # Phase 2: supplemental aggregates. They never create evidence between
            # pre-existing provider IDs; they only attach new namespaces to trusted anchors.
            for index, spec in enumerate(SOURCE_SPECS):
                if not spec.supplemental:
                    continue
                record_count = 0
                staged_item = staged.get(spec.name)
                if staged_item is not None:
                    download_path, sha256 = staged_item
                    # Validate these sources against prior supplemental inputs as
                    # well, so an already attached target cannot be reassigned.
                    if spec.importer in {
                        "media_index",
                        "aniliberty",
                        "sovetromantica",
                        "malsync_crunchyroll",
                        "malsync_netflix",
                        "anime365",
                        "docchi",
                        "animelib",
                        "adkami",
                        "aniyan",
                        "anidream",
                        "aninexus",
                        "yummyani",
                        "annict_api",
                    }:
                        builder.finalize(built_at=checked_at)
                    supplemental_importer = SUPPLEMENTAL_IMPORTERS.get(spec.importer)
                    if supplemental_importer is None:
                        raise RuntimeError(
                            f"Unsupported supplemental importer: {spec.importer}"
                        )
                    record_count = builder.ingest_dataset(
                        spec,
                        supplemental_importer(download_path, builder.conn),
                        sha256=sha256,
                        downloaded_at=snapshot_dates.get(spec.name, checked_at),
                    )
                    if record_count <= 0:
                        if snapshot_dir is not None and spec.name in state:
                            raise RuntimeError(
                                f"Previously published source is empty: {spec.name}"
                            )
                        failed_optional[spec.name] = (
                            "supplemental source produced zero anchor-validated records"
                        )
                    elif mappings_keep_downloads():
                        downloads_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(download_path, downloads_dir / download_path.name)
                elif (
                    snapshot_dir is None
                    and evidence_path.is_file()
                    and spec.name in state
                    and not base_changed
                    and spec.importer
                    not in {
                        "media_index",
                        "aniliberty",
                        "sovetromantica",
                        "malsync_crunchyroll",
                        "malsync_netflix",
                        "anime365",
                        "docchi",
                        "animelib",
                        "adkami",
                        "aniyan",
                        "anidream",
                        "aninexus",
                        "yummyani",
                        "annict_api",
                    }
                ):
                    # Safe only when the base graph is unchanged. If it changed and the
                    # supplemental source is unavailable, omit old enrichment rather than
                    # preserve mappings whose anchors can no longer be revalidated.
                    record_count = builder.copy_dataset_from(evidence_path, spec.name)
                elif spec.name in failed_optional:
                    record_count = 0

                if record_count > 0:
                    logging.info(
                        "Supplemental mapping source indexed: %s — %d records",
                        spec.name,
                        record_count,
                    )

            override_count = copy_mapping_overrides(db_path, builder.conn)
            if override_count:
                logging.info(
                    "Mapping overrides preserved in rebuild: %d", override_count
                )

            # Re-materialize with supplemental evidence included.
            stats = builder.finalize(built_at=checked_at)
            for conn in (builder.conn, builder.evidence_conn):
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES('optional_failures', ?)",
                    (json.dumps(failed_optional, ensure_ascii=False, sort_keys=True),),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES('overrides', ?)",
                    (str(override_count),),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES('last_source_check_at', ?)",
                    (checked_at,),
                )
                conn.commit()

        if stats.datasets < len(required_loaded):
            raise RuntimeError(
                "mappings.db validation failed: dataset count is too small"
            )
        if stats.edges <= 0 or stats.accepted_edges <= 0:
            raise RuntimeError(
                "mappings.db validation failed: no accepted mapping edges"
            )

        anchor_stats = materialize_anchor_index(
            new_path,
            previous_path=db_path if db_path.is_file() else None,
            force=True,
        )
        if anchor_stats.nodes <= 0 or anchor_stats.entities <= 0:
            raise RuntimeError(
                "mappings.db validation failed: empty anchor identity index"
            )
        logging.info(
            "Mapping anchor index rebuilt: entities=%d reused=%d created=%d redirects=%d",
            anchor_stats.entities,
            anchor_stats.reused,
            anchor_stats.created,
            anchor_stats.redirects,
        )

        if mappings_keep_previous():
            if db_path.exists():
                shutil.copy2(db_path, previous_path)
            if evidence_path.exists():
                shutil.copy2(evidence_path, evidence_previous_path)

        # Runtime first: if the second replace ever fails, the bot still has the
        # newly built self-contained lookup database. The next updater can recover
        # provenance from the older evidence DB without breaking lookups.
        os.replace(new_path, db_path)
        os.replace(evidence_new_path, evidence_path)
        logging.info(
            "Mapping databases updated: changed=%s datasets=%d records=%d evidence=%d edges=%d accepted=%d conflicts=%d overrides=%d runtime_bytes=%d evidence_bytes=%d",
            ",".join(sorted(changed_sources))
            or ("runtime-only" if runtime_rebuild_only else "forced"),
            stats.datasets,
            stats.records,
            stats.evidence,
            stats.edges,
            stats.accepted_edges,
            stats.conflicts,
            override_count,
            db_path.stat().st_size,
            evidence_path.stat().st_size,
        )
        return stats
    finally:
        new_path.unlink(missing_ok=True)
        evidence_new_path.unlink(missing_ok=True)
        for path, _sha in staged.values():
            path.unlink(missing_ok=True)
        try:
            if work_dir.exists() and not any(work_dir.iterdir()):
                work_dir.rmdir()
        except OSError:
            pass
        lock_path.unlink(missing_ok=True)


def update_if_stale() -> MappingBuildStats | None:
    return update_mapping_database(force=False)


def mapping_status() -> dict[str, object]:
    database = MappingDatabase()
    evidence_path = mappings_evidence_db_path()
    metadata = database.metadata()
    return {
        "path": str(database.path),
        "available": database.available,
        "evidence_path": str(evidence_path),
        "evidence_available": evidence_path.is_file(),
        "stale": _is_stale(evidence_path),
        "metadata": metadata,
    }
