from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.importers import import_anime_lists, import_fribb, import_manami
from anime_mapping_db.resolver import (
    MappingResolver,
    copy_mapping_overrides,
    delete_mapping_override,
    list_mapping_override_history,
    list_mapping_overrides,
    set_mapping_override,
)


class MappingDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runtime = self.root / "mappings.db"
        self.evidence = self.root / "mappings-evidence.db"

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def spec(name: str = "fixture") -> MappingSourceSpec:
        return MappingSourceSpec(
            name, "https://example.invalid/data", "test", True, "test"
        )

    def build(self, datasets: list[tuple[str, list[MappingRecord]]]) -> MappingResolver:
        with MappingDatabaseBuilder(
            self.runtime, evidence_path=self.evidence
        ) as builder:
            for index, (name, records) in enumerate(datasets):
                builder.ingest_dataset(
                    self.spec(name),
                    records,
                    sha256=f"sha-{index}",
                    downloaded_at="2026-11-01T00:00:00+00:00",
                )
            builder.finalize(built_at="2026-11-01T00:00:00+00:00")
        return MappingResolver(self.runtime)

    def test_high_trust_direct_edge_resolves(self) -> None:
        resolver = self.build(
            [("a", [MappingRecord("1", {"mal": ("100",), "anidb": ("200",)}, "a", 90)])]
        )
        self.assertEqual(resolver.resolve({"mal": "100"}), {"anidb": "200"})

    def test_correlated_sources_do_not_double_vote(self) -> None:
        record = lambda key: MappingRecord(
            key, {"mal": ("100",), "anidb": ("200",)}, "shared", 60
        )
        resolver = self.build([("a", [record("1")]), ("b", [record("2")])])
        self.assertEqual(resolver.resolve({"mal": "100"}), {})
        with closing(sqlite3.connect(self.runtime)) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT status, evidence_count, evidence_group_count FROM edges"
                ).fetchone(),
                ("candidate", 2, 1),
            )

    def test_independent_groups_accept_lower_weight_edge(self) -> None:
        resolver = self.build(
            [
                (
                    "a",
                    [
                        MappingRecord(
                            "1", {"mal": ("100",), "anidb": ("200",)}, "g1", 60
                        )
                    ],
                ),
                (
                    "b",
                    [
                        MappingRecord(
                            "2", {"mal": ("100",), "anidb": ("200",)}, "g2", 60
                        )
                    ],
                ),
            ]
        )
        self.assertEqual(resolver.resolve({"mal": "100"}), {"anidb": "200"})

    def test_directional_conflict_and_no_transitive_walk(self) -> None:
        resolver = self.build(
            [
                (
                    "a",
                    [
                        MappingRecord(
                            "1", {"anidb": ("200",), "mal": ("100",)}, "a", 95
                        ),
                        MappingRecord(
                            "2", {"anidb": ("200",), "mal": ("101",)}, "a", 95
                        ),
                        MappingRecord(
                            "3", {"mal": ("100",), "kitsu": ("300",)}, "a", 95
                        ),
                    ],
                )
            ]
        )
        self.assertEqual(resolver.resolve({"anidb": "200"}), {})
        self.assertEqual(resolver.resolve({"mal": "101"}), {"anidb": "200"})
        self.assertNotIn("kitsu", resolver.resolve({"anidb": "200"}))

    def test_runtime_and_evidence_are_separate(self) -> None:
        self.build(
            [
                (
                    "a",
                    [
                        MappingRecord(
                            "1",
                            {"mal": ("1",), "anidb": ("2",), "imdb": ("tt3",)},
                            "a",
                            95,
                        )
                    ],
                )
            ]
        )
        with closing(sqlite3.connect(self.runtime)) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn("edges", tables)
            self.assertNotIn("datasets", tables)
            self.assertEqual(
                conn.execute(
                    "SELECT value FROM metadata WHERE key='database_role'"
                ).fetchone()[0],
                "runtime",
            )
        with closing(sqlite3.connect(self.evidence)) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn("datasets", tables)
            self.assertNotIn("edges", tables)
            self.assertEqual(
                conn.execute(
                    "SELECT value FROM metadata WHERE key='database_role'"
                ).fetchone()[0],
                "evidence",
            )

    def test_override_history_and_copy_survive_rebuild(self) -> None:
        resolver = self.build(
            [("a", [MappingRecord("1", {"mal": ("100",), "anidb": ("200",)}, "a", 95)])]
        )
        set_mapping_override(
            "mal",
            "100",
            "anidb",
            "201",
            action="accept",
            reason="verified",
            author="test",
            path=self.runtime,
        )
        self.assertEqual(resolver.resolve({"mal": "100"}), {"anidb": "201"})
        self.assertEqual(list_mapping_overrides(self.runtime)[0].author, "test")
        rebuilt = self.root / "rebuilt.db"
        with MappingDatabaseBuilder(rebuilt) as builder:
            builder.ingest_dataset(
                self.spec(),
                [MappingRecord("1", {"mal": ("100",), "anidb": ("200",)}, "a", 95)],
                sha256="new",
                downloaded_at="2026-11-02T00:00:00+00:00",
            )
            self.assertEqual(copy_mapping_overrides(self.runtime, builder.conn), 1)
            builder.finalize(built_at="2026-11-02T00:00:00+00:00")
        self.assertEqual(
            MappingResolver(rebuilt).resolve({"mal": "100"}), {"anidb": "201"}
        )
        self.assertTrue(
            delete_mapping_override("mal", "100", "anidb", "201", path=rebuilt)
        )
        self.assertEqual(
            [item.event for item in list_mapping_override_history(rebuilt)],
            ["set", "delete"],
        )

    def test_selected_importers_stream_fixtures(self) -> None:
        fribb = self.root / "fribb.json"
        fribb.write_text(
            json.dumps([{"anidb_id": 10, "mal_id": 20, "anilist_id": 30}]),
            encoding="utf-8",
        )
        self.assertEqual(next(import_fribb(fribb)).ids["mal"], ("20",))
        xml = self.root / "anime-list.xml"
        xml.write_text(
            '<anime-list><anime anidbid="10" tvdbid="40" /></anime-list>',
            encoding="utf-8",
        )
        self.assertEqual(next(import_anime_lists(xml)).ids["tvdb"], ("40",))
        manami = self.root / "manami.jsonl"
        manami.write_text(
            json.dumps(
                {
                    "sources": [
                        "https://anidb.net/anime/10",
                        "https://myanimelist.net/anime/20",
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.assertEqual(next(import_manami(manami)).ids["mal"], ("20",))


if __name__ == "__main__":
    unittest.main()
