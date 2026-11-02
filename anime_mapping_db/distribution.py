from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

STORAGE_PROFILE = "compact-v1"


def _verify(path: Path) -> None:
    with closing(sqlite3.connect(path, timeout=30.0)) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise RuntimeError(f"SQLite integrity check failed for {path}: {integrity}")
        foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_keys:
            raise RuntimeError(
                f"SQLite foreign key check failed for {path}: {foreign_keys[:5]}"
            )


def compact_runtime_database(source: Path, destination: Path) -> None:
    """Materialize the read-optimized runtime distribution database.

    The build database keeps symmetric edge indexes because builder/audit code uses
    both directions freely.  A released database is read-only, so the left side of
    ``edges`` can use the WITHOUT ROWID primary key directly and only the reverse
    accepted-edge lookup needs a secondary index.
    """

    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == destination.resolve():
        raise ValueError("runtime distribution destination must differ from source")
    shutil.copy2(source, destination)

    with closing(sqlite3.connect(destination, timeout=30.0)) as conn:
        conn.execute("DROP INDEX IF EXISTS edges_a_lookup_idx")
        conn.execute("DROP INDEX IF EXISTS edges_b_lookup_idx")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS edges_b_accepted_idx
            ON edges(b_node, a_node)
            WHERE status='accepted'
            """
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('storage_profile', ?)",
            (STORAGE_PROFILE,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('edge_lookup_layout', 'pk-plus-reverse-accepted')"
        )
        conn.execute("ANALYZE")
        conn.commit()
        conn.execute("VACUUM")

    _verify(destination)


def compact_evidence_database(source: Path, destination: Path) -> None:
    """Materialize a lossless compact provenance distribution database.

    Build-time ``records`` uniqueness is already audited before packaging, so the
    distribution copy does not need the ~34 MiB composite UNIQUE B-tree.  Likewise,
    pairwise edge evidence is exactly reconstructible from the set of nodes present
    in each source record.  ``record_nodes`` stores that normalized membership and
    a compatibility ``edge_evidence`` view exposes the original rows unchanged.
    """

    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == destination.resolve():
        raise ValueError("evidence distribution destination must differ from source")
    destination.unlink(missing_ok=True)

    with closing(sqlite3.connect(destination, timeout=60.0)) as conn:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.execute("PRAGMA temp_store=FILE")
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.executescript(
            """
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE datasets (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                source_url TEXT NOT NULL,
                importer TEXT NOT NULL,
                license_note TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                downloaded_at TEXT NOT NULL,
                record_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE nodes (
                id INTEGER PRIMARY KEY,
                provider TEXT NOT NULL,
                external_id TEXT NOT NULL,
                UNIQUE(provider, external_id)
            );

            CREATE TABLE evidence_groups (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE records (
                id INTEGER PRIMARY KEY,
                dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
                record_key TEXT NOT NULL,
                evidence_group_id INTEGER NOT NULL REFERENCES evidence_groups(id),
                weight INTEGER NOT NULL
            );

            CREATE INDEX records_dataset_idx ON records(dataset_id);

            CREATE TABLE record_nodes (
                record_id INTEGER NOT NULL REFERENCES records(id) ON DELETE CASCADE,
                node_id INTEGER NOT NULL REFERENCES nodes(id),
                PRIMARY KEY(record_id, node_id)
            ) WITHOUT ROWID;

            CREATE VIEW edge_evidence AS
            SELECT
                left_node.record_id AS record_id,
                left_node.node_id AS a_node,
                right_node.node_id AS b_node
            FROM record_nodes AS left_node
            JOIN record_nodes AS right_node
              ON right_node.record_id=left_node.record_id
             AND right_node.node_id>left_node.node_id
            JOIN nodes AS left_identity ON left_identity.id=left_node.node_id
            JOIN nodes AS right_identity ON right_identity.id=right_node.node_id
            WHERE left_identity.provider<>right_identity.provider;
            """
        )
        conn.execute("ATTACH DATABASE ? AS source_db", (source.resolve().as_posix(),))
        try:
            for table in (
                "metadata",
                "datasets",
                "nodes",
                "evidence_groups",
                "records",
            ):
                columns = [
                    str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")
                ]
                packed = ", ".join(columns)
                conn.execute(
                    f"INSERT INTO {table}({packed}) SELECT {packed} FROM source_db.{table}"
                )
            conn.execute(
                """
                INSERT INTO record_nodes(record_id, node_id)
                SELECT record_id, a_node FROM source_db.edge_evidence
                UNION
                SELECT record_id, b_node FROM source_db.edge_evidence
                """
            )
            source_records = int(
                conn.execute("SELECT COUNT(*) FROM source_db.records").fetchone()[0]
            )
            source_evidence = int(
                conn.execute("SELECT COUNT(*) FROM source_db.edge_evidence").fetchone()[
                    0
                ]
            )
            compact_records = int(
                conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            )
            compact_evidence = int(
                conn.execute("SELECT COUNT(*) FROM edge_evidence").fetchone()[0]
            )
            if source_records != compact_records:
                raise RuntimeError(
                    f"evidence record count changed during compaction: {source_records} != {compact_records}"
                )
            if source_evidence != compact_evidence:
                raise RuntimeError(
                    f"edge evidence count changed during compaction: {source_evidence} != {compact_evidence}"
                )
            conn.commit()
        finally:
            conn.execute("DETACH DATABASE source_db")

        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('storage_profile', ?)",
            (STORAGE_PROFILE,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES('edge_evidence_storage', 'record_nodes-view')"
        )
        conn.execute("ANALYZE")
        conn.commit()
        conn.execute("VACUUM")

    _verify(destination)
