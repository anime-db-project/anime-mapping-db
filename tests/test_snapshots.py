from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingRecord
from anime_mapping_db.snapshots import collect, compare, load_snapshot
from anime_mapping_db.updater import update_mapping_database


class SnapshotTests(unittest.TestCase):
    def test_offline_build_and_unchanged_collection(self) -> None:
        spec = MappingSourceSpec(
            "base", "https://example.invalid/base.json", "base", True, "test"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshots = root / "snapshots"

            def download(_spec, target):
                target.write_text("fixture", encoding="utf-8")
                return "unused"

            def importer(_path):
                yield MappingRecord(
                    "1", {"mal": ("1",), "anilist": ("2",)}, "test", 95
                )

            with patch("anime_mapping_db.snapshots._download", side_effect=download):
                first = collect(snapshots, (spec,))
                second = collect(snapshots, (spec,))
            self.assertEqual(first, second)
            with (
                patch("anime_mapping_db.snapshots.SOURCE_SPECS", (spec,)),
                patch("anime_mapping_db.updater.SOURCE_SPECS", (spec,)),
                patch("anime_mapping_db.updater.IMPORTERS", {"base": importer}),
                patch(
                    "anime_mapping_db.updater.mappings_db_path",
                    return_value=root / "runtime.db",
                ),
                patch(
                    "anime_mapping_db.updater.mappings_evidence_db_path",
                    return_value=root / "evidence.db",
                ),
                patch(
                    "anime_mapping_db.updater._download",
                    side_effect=AssertionError("network"),
                ),
            ):
                self.assertFalse(compare(snapshots, first))
                self.assertTrue(compare(snapshots, first, force=True))
                self.assertIsNotNone(update_mapping_database(snapshot_dir=snapshots))
            with patch(
                "anime_mapping_db.snapshots._download", side_effect=RuntimeError("offline")
            ):
                self.assertEqual(collect(snapshots, (spec,)), first)
            entry = load_snapshot(snapshots, (spec,))[spec.name]
            (snapshots / entry["file"]).write_text("corrupt", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_snapshot(snapshots, (spec,))
