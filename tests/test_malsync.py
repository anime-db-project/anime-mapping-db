from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.importers.malsync import (
    import_malsync_crunchyroll,
    import_malsync_netflix,
    normalize_snapshot,
)


class MALSyncTests(unittest.TestCase):
    def test_only_explicit_unambiguous_season_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "catalog.json"
            path.write_text(
                json.dumps(
                    {
                        "series": {
                            "SERIES001": {
                                "seasons": {
                                    "SEASON001": {"override": {"malId": 101}},
                                    "SEASON002": {"override": {"malId": 102}},
                                    "SEASON003": {"override": {"malId": 102}},
                                    "SEASON004": {
                                        "override": {"malId": 103, "offset": 12}
                                    },
                                    "SEASON005": {
                                        "override": {"malId": 104, "season": 1}
                                    },
                                    "SEASON006": {"title": "not a mapping"},
                                    "SEASON007": {"override": {"malId": 999}},
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            normalize_snapshot(path, "malsync_crunchyroll")
            self.assertEqual(len(json.loads(path.read_text("utf-8"))), 4)
            spec = MappingSourceSpec(
                "base", "https://example.invalid/base", "test", True, "test"
            )
            with MappingDatabaseBuilder(
                root / "runtime.db", evidence_path=root / "evidence.db"
            ) as builder:
                builder.ingest_dataset(
                    spec,
                    [
                        MappingRecord(
                            str(i),
                            {"mal": (str(100 + i),), "anilist": (str(200 + i),)},
                            "trusted",
                            95,
                        )
                        for i in range(1, 5)
                    ],
                    sha256="base",
                    downloaded_at="2026-11-28",
                )
                builder.finalize(built_at="2026-11-28")
                imported = list(import_malsync_crunchyroll(path, builder.conn))
                self.assertEqual(len(imported), 1)
                self.assertEqual(
                    imported[0].ids,
                    {"crunchyroll_season": ("SEASON001",), "mal": ("101",)},
                )
                path.write_text(
                    json.dumps(
                        {
                            "seasons": {
                                "12345678": {"override": {"malId": 101}},
                                "12345679": {"override": {"malId": 102, "offset": 45}},
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                imported = list(import_malsync_netflix(path, builder.conn))
                self.assertEqual(len(imported), 1)
                self.assertEqual(
                    imported[0].ids,
                    {"netflix_season": ("12345678",), "mal": ("101",)},
                )
