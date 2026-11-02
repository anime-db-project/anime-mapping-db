from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from anime_mapping_db.anchors import AnchorResolver, materialize_anchor_index


class AnchorIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _database(self, name: str, *, merge: bool = False, extra: bool = False) -> Path:
        path = self.root / name
        with sqlite3.connect(path) as conn:
            conn.executescript(
                """
                CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE nodes(
                    id INTEGER PRIMARY KEY,
                    provider TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    UNIQUE(provider, external_id)
                );
                CREATE TABLE edges(
                    a_node INTEGER NOT NULL,
                    b_node INTEGER NOT NULL,
                    confidence INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    evidence_count INTEGER NOT NULL,
                    evidence_group_count INTEGER NOT NULL,
                    max_weight INTEGER NOT NULL,
                    PRIMARY KEY(a_node, b_node)
                );
                CREATE TABLE conflicts(
                    source_node INTEGER NOT NULL,
                    target_provider TEXT NOT NULL,
                    candidate_ids_json TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    PRIMARY KEY(source_node, target_provider)
                );
                CREATE TABLE mapping_overrides(
                    source_provider TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_provider TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    author TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(source_provider, source_id, target_provider, target_id)
                );
                INSERT INTO nodes VALUES
                    (1, 'mal', '1'),
                    (2, 'anilist', '10'),
                    (3, 'mal', '2'),
                    (4, 'anilist', '20');
                INSERT INTO edges VALUES
                    (1, 2, 100, 'accepted', 1, 1, 100),
                    (3, 4, 100, 'accepted', 1, 1, 100);
                """
            )
            if extra:
                conn.execute("INSERT INTO nodes VALUES(5, 'kitsu', 'series-one')")
                conn.execute(
                    "INSERT INTO edges VALUES(1, 5, 100, 'accepted', 1, 1, 100)"
                )
            if merge:
                conn.execute(
                    "INSERT INTO edges VALUES(2, 3, 100, 'accepted', 1, 1, 100)"
                )
        return path

    def test_anchor_survives_graph_enrichment(self) -> None:
        previous = self._database("previous.db")
        first = materialize_anchor_index(previous)
        self.assertEqual(first.entities, 2)
        old = AnchorResolver(previous)
        anchor_one = old.anchor_for({"mal": "1"})
        anchor_two = old.anchor_for({"mal": "2"})
        self.assertIsNotNone(anchor_one)
        self.assertIsNotNone(anchor_two)

        current = self._database("current.db", extra=True)
        second = materialize_anchor_index(current, previous_path=previous)
        self.assertEqual(second.reused, 2)
        resolver = AnchorResolver(current)
        self.assertEqual(
            resolver.anchor_for({"kitsu": "series-one"}).anchor_id,
            anchor_one.anchor_id,
        )
        self.assertEqual(
            resolver.anchor_for({"mal": "2"}).anchor_id,
            anchor_two.anchor_id,
        )

    def test_merge_keeps_survivor_and_redirects_old_anchor(self) -> None:
        previous = self._database("previous.db")
        materialize_anchor_index(previous)
        old = AnchorResolver(previous)
        first = old.anchor_for({"mal": "1"}).anchor_id
        second = old.anchor_for({"mal": "2"}).anchor_id

        current = self._database("current.db", merge=True)
        stats = materialize_anchor_index(current, previous_path=previous)
        self.assertEqual(stats.entities, 1)
        self.assertEqual(stats.merged, 1)
        self.assertEqual(stats.redirects, 1)

        resolver = AnchorResolver(current)
        survivor = min(first, second)
        self.assertEqual(resolver.anchor_for({"mal": "1"}).anchor_id, survivor)
        self.assertEqual(resolver.anchor_for({"mal": "2"}).anchor_id, survivor)
        redirected = resolver.ids_for(f"amdb:{max(first, second)}")
        self.assertEqual(redirected["mal"], ("1", "2"))

    def test_conflicted_edge_does_not_merge_entities(self) -> None:
        path = self._database("conflict.db")
        with sqlite3.connect(path) as conn:
            conn.execute(
                "INSERT INTO conflicts VALUES(1, 'anilist', '[\"10\",\"20\"]', 'ambiguous')"
            )
        materialize_anchor_index(path)
        resolver = AnchorResolver(path)
        self.assertNotEqual(
            resolver.anchor_for({"mal": "1"}).anchor_id,
            resolver.anchor_for({"anilist": "10"}).anchor_id,
        )


if __name__ == "__main__":
    unittest.main()
