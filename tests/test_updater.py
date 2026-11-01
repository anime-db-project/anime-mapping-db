from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.updater import _source_due, update_mapping_database


class MappingUpdaterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = self.root / "mappings.db"
        self.evidence = self.root / "mappings-evidence.db"

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def spec(*, interval: str = "default") -> MappingSourceSpec:
        return MappingSourceSpec(
            name="fixture",
            url="https://example.invalid/data.json",
            importer="test",
            required=True,
            license_note="test",
            check_interval=interval,
        )

    def test_force_build_creates_runtime_and_evidence(self) -> None:
        spec = self.spec()

        def fake_download(_spec: MappingSourceSpec, target: Path) -> str:
            target.write_text("fixture", encoding="utf-8")
            return "fixture-sha"

        def fake_importer(_path: Path):
            yield MappingRecord(
                "1", {"mal": ("1",), "anidb": ("2",), "imdb": ("tt3",)}, "test", 95
            )

        with (
            patch("anime_mapping_db.updater.SOURCE_SPECS", (spec,)),
            patch(
                "anime_mapping_db.updater.mappings_db_path", return_value=self.runtime
            ),
            patch(
                "anime_mapping_db.updater.mappings_evidence_db_path",
                return_value=self.evidence,
            ),
            patch(
                "anime_mapping_db.updater.mappings_keep_previous", return_value=False
            ),
            patch(
                "anime_mapping_db.updater.mappings_keep_downloads", return_value=False
            ),
            patch("anime_mapping_db.updater._download", side_effect=fake_download),
            patch.dict("anime_mapping_db.updater.IMPORTERS", {"test": fake_importer}),
        ):
            stats = update_mapping_database(force=True)

        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats.edges, 3)
        self.assertEqual(stats.accepted_edges, 3)
        with closing(sqlite3.connect(self.runtime)) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT value FROM metadata WHERE key='database_role'"
                ).fetchone()[0],
                "runtime",
            )
        with closing(sqlite3.connect(self.evidence)) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT value FROM metadata WHERE key='database_role'"
                ).fetchone()[0],
                "evidence",
            )

    def test_unchanged_source_does_not_replace_runtime(self) -> None:
        spec = self.spec()
        old = "2020-01-01T00:00:00+00:00"
        with MappingDatabaseBuilder(
            self.runtime, evidence_path=self.evidence
        ) as builder:
            builder.ingest_dataset(
                spec,
                [MappingRecord("1", {"mal": ("1",), "anidb": ("2",)}, "test", 95)],
                sha256="same-sha",
                downloaded_at=old,
            )
            builder.finalize(built_at=old)
        inode_before = self.runtime.stat().st_ino

        def fake_download(_spec: MappingSourceSpec, target: Path) -> str:
            target.write_text("same", encoding="utf-8")
            return "same-sha"

        with (
            patch("anime_mapping_db.updater.SOURCE_SPECS", (spec,)),
            patch(
                "anime_mapping_db.updater.mappings_db_path", return_value=self.runtime
            ),
            patch(
                "anime_mapping_db.updater.mappings_evidence_db_path",
                return_value=self.evidence,
            ),
            patch(
                "anime_mapping_db.updater.mappings_update_max_age_hours",
                return_value=1.0,
            ),
            patch("anime_mapping_db.updater._download", side_effect=fake_download),
        ):
            self.assertIsNone(update_mapping_database(force=False))
        self.assertEqual(self.runtime.stat().st_ino, inode_before)

    def test_initial_wikidata_failure_uses_bundled_bootstrap_snapshot(self) -> None:
        spec = MappingSourceSpec(
            name="Wikidata/Bahamut Animation Crazy",
            url="https://query.wikidata.org/sparql?query=test",
            importer="wikidata_bahamut",
            required=False,
            license_note="Wikidata structured data is CC0 1.0.",
            check_interval="wikidata",
        )

        with (
            patch("anime_mapping_db.updater.SOURCE_SPECS", (spec,)),
            patch(
                "anime_mapping_db.updater.mappings_db_path", return_value=self.runtime
            ),
            patch(
                "anime_mapping_db.updater.mappings_evidence_db_path",
                return_value=self.evidence,
            ),
            patch(
                "anime_mapping_db.updater.mappings_keep_previous", return_value=False
            ),
            patch(
                "anime_mapping_db.updater.mappings_keep_downloads", return_value=False
            ),
            patch(
                "anime_mapping_db.updater._download",
                side_effect=RuntimeError("WDQS unavailable"),
            ),
        ):
            stats = update_mapping_database(force=True)

        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats.datasets, 1)
        self.assertEqual(stats.records, 777)
        with closing(sqlite3.connect(self.runtime)) as conn:
            failures = conn.execute(
                "SELECT value FROM metadata WHERE key='optional_failures'"
            ).fetchone()[0]
        self.assertIn("bundled CC0 bootstrap snapshot used", failures)

    def test_wikidata_has_independent_check_interval(self) -> None:
        checked = datetime.fromtimestamp(
            time.time() - 2 * 3600, timezone.utc
        ).isoformat()
        state = {"fixture": ("sha", checked)}
        with (
            patch(
                "anime_mapping_db.updater.mappings_update_max_age_hours",
                return_value=1.0,
            ),
            patch(
                "anime_mapping_db.updater.mappings_wikidata_check_interval_hours",
                return_value=168.0,
            ),
        ):
            self.assertTrue(_source_due(self.spec(), state))
            self.assertFalse(_source_due(self.spec(interval="wikidata"), state))


if __name__ == "__main__":
    unittest.main()
