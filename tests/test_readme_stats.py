from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.update_readme_stats import (
    BEGIN,
    END,
    LANGUAGES,
    WORDS,
    read_entities,
    refresh_readmes,
)


class ReadmeStatisticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        (self.root / "docs").mkdir()
        self.db = self.root / "mappings.db"
        with sqlite3.connect(self.db) as conn:
            conn.execute("CREATE TABLE entities (entity_id INTEGER PRIMARY KEY)")
            conn.executemany("INSERT INTO entities VALUES(?)", [(1,), (2,), (3,)])
        for lang in LANGUAGES:
            path = self.root / (
                "README.md" if lang == "en" else f"docs/README.{lang}.md"
            )
            path.write_text(
                f"# Test\n\n## {WORDS[lang]['title']}\n\nOld snapshot.\n\n## Features\n\nKeep this.\n",
                encoding="utf-8",
            )
        self.manifest = {
            "release_tag": "v2026.11.05.123",
            "built_at": "2026-11-05T15:21:01+00:00",
            "counts": {
                "datasets": 18,
                "accepted_edges": 42,
                "conflicts": 2,
                "records": 99,
                "evidence": 111,
            },
            "providers": {"mal": 30, "anilist": 20},
            "text_export": {"rows": 57},
            "assets": {
                "runtime": {"size": self.db.stat().st_size},
                "runtime_zstd": {"size": 1024},
            },
        }
        self.performance = {
            "database_bytes": self.db.stat().st_size,
            "sampled_ids": 10,
            "rounds": 2,
            "median_ms": 0.2,
            "mean_ms": 0.3,
            "p95_ms": 0.4,
            "p99_ms": 0.5,
            "lookups_per_second": 2000,
            "environment": "Linux / Python 3.12",
        }

    def test_all_translations_update_once_and_preserve_other_content(self) -> None:
        self.assertEqual(read_entities(self.db), 3)
        changed = refresh_readmes(self.root, self.manifest, self.db, self.performance)
        self.assertEqual(len(changed), 7)
        for lang in LANGUAGES:
            path = self.root / (
                "README.md" if lang == "en" else f"docs/README.{lang}.md"
            )
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(BEGIN), 1)
            self.assertEqual(text.count(END), 1)
            self.assertIn("**42**", text)
            self.assertIn("**0.200 ms**", text)
            self.assertNotIn("≈35", text)
            self.assertNotIn("unique anime titles", text)
            self.assertNotIn("database build time", text)
            self.assertIn("Keep this.", text)
        self.assertEqual(
            refresh_readmes(self.root, self.manifest, self.db, self.performance), []
        )
        self.assertEqual(
            refresh_readmes(
                self.root, self.manifest, self.db, self.performance, check=True
            ),
            [],
        )

    def test_new_release_updates_every_translation(self) -> None:
        refresh_readmes(self.root, self.manifest, self.db, self.performance)
        updated = dict(self.manifest)
        updated["release_tag"] = "v2026.11.06.1"
        updated["counts"] = {**self.manifest["counts"], "accepted_edges": 61}
        self.assertEqual(
            len(
                refresh_readmes(
                    self.root, updated, self.db, self.performance, check=True
                )
            ),
            7,
        )
        self.assertEqual(
            len(refresh_readmes(self.root, updated, self.db, self.performance)), 7
        )

    def test_stale_benchmark_rejected_without_overwriting_files(self) -> None:
        invalid = {**self.performance, "database_bytes": 5}
        with self.assertRaises(ValueError):
            refresh_readmes(self.root, self.manifest, self.db, invalid)
        self.assertNotIn(BEGIN, (self.root / "README.md").read_text())

    def test_invalid_tag_rejected(self) -> None:
        wrong = {**self.manifest, "release_tag": "../main"}
        with self.assertRaises(ValueError):
            refresh_readmes(self.root, wrong, self.db, self.performance)


if __name__ == "__main__":
    unittest.main()
