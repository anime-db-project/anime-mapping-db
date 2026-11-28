from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from anime_mapping_db.malsync_authorized import (
    AUTHORIZED_IMPORTERS,
    PROVIDERS,
    normalize_authorized,
)


class AuthorizedCatalogueTests(unittest.TestCase):
    def test_all_registered_and_normalized(self) -> None:
        self.assertEqual(set(PROVIDERS), set(AUTHORIZED_IMPORTERS))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            for provider in PROVIDERS:
                native = "123" if provider != "animewho" else "anime-123"
                path.write_text(
                    json.dumps([{"id": native, "scope": "title", "mal_id": 101,
                                 "anilist_id": 201, "name": "discard"}]),
                    encoding="utf-8",
                )
                normalize_authorized(path, provider)
                before = path.read_bytes()
                normalize_authorized(path, provider)
                self.assertEqual(before, path.read_bytes())
                self.assertEqual(json.loads(before), [
                    {"id": native, "scope": "title", "mal": "101",
                     "anilist": "201", "shikimori": None}
                ])

    def test_bad_scope_conflicts_and_session_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            for row in (
                {"id": "1", "scope": "episode", "mal": 101},
                {"id": "1", "scope": "title", "mal": 101, "mal_id": 102},
                {"id": "session-uuid", "scope": "title", "mal": 101},
                {"id": "1", "scope": "title", "mal": True},
                {"id": "1", "scope": "title"},
            ):
                path.write_text(json.dumps([row]), encoding="utf-8")
                with self.assertRaises(ValueError):
                    normalize_authorized(path, "animepahe")
