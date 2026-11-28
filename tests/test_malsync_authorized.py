from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.malsync_authorized import (
    AUTHORIZED_IMPORTERS,
    PROVIDERS,
    INDEPENDENT_ID_REQUIRED,
    SEASON_PROVIDERS,
    normalize_authorized,
)


class AuthorizedCatalogueTests(unittest.TestCase):
    def test_all_registered_and_normalized(self) -> None:
        self.assertEqual(set(PROVIDERS), set(AUTHORIZED_IMPORTERS))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            for provider in PROVIDERS:
                native = "123" if provider != "animewho" else "anime-123"
                if provider == "crunchyroll_season":
                    native = "G123ABCD"
                extra = {}
                scope = "title"
                if provider in SEASON_PROVIDERS:
                    scope = "season"
                    extra.update(full_season=True, offset=0)
                if provider in INDEPENDENT_ID_REQUIRED:
                    extra["native_id_verified"] = True
                path.write_text(
                    json.dumps(
                        [
                            {
                                "id": native,
                                "scope": scope,
                                **extra,
                                "mal_id": 101,
                                "anilist_id": 201,
                                "name": "discard",
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
                normalize_authorized(path, provider)
                before = path.read_bytes()
                normalize_authorized(path, provider)
                self.assertEqual(before, path.read_bytes())
                self.assertEqual(
                    json.loads(before),
                    [
                        {
                            "id": native,
                            "scope": scope,
                            **extra,
                            "mal": "101",
                            "anilist": "201",
                            "shikimori": None,
                            "kitsu": None,
                        }
                    ],
                )

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

    def test_kitsu_only_anchor_and_conflicting_claims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "source.json"
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
                            {"mal": (str(100 + i),), "kitsu": (str(200 + i),)},
                            "trusted",
                            95,
                        )
                        for i in (1, 2)
                    ],
                    sha256="base",
                    downloaded_at="2026-11-28",
                )
                builder.finalize(built_at="2026-11-28")
                path.write_text(
                    json.dumps([{"id": "7", "scope": "title", "kitsu": 201}]),
                    encoding="utf-8",
                )
                records = list(AUTHORIZED_IMPORTERS["animepahe"](path, builder.conn))
                self.assertEqual(records[0].ids["animepahe"], ("7",))
                self.assertEqual(records[0].ids["kitsu"], ("201",))
                path.write_text(
                    json.dumps(
                        [{"id": "7", "scope": "title", "kitsu": 201, "mal": 102}]
                    ),
                    encoding="utf-8",
                )
                self.assertEqual(
                    list(AUTHORIZED_IMPORTERS["animepahe"](path, builder.conn)), []
                )

    def test_special_scope_and_reused_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            for provider, row in (
                ("fireanime", {"id": "x", "scope": "title", "anilist": 101}),
                (
                    "miruro",
                    {
                        "id": "101",
                        "scope": "title",
                        "anilist": 101,
                        "native_id_verified": True,
                    },
                ),
                (
                    "anikoto_season",
                    {"id": "x", "scope": "episode", "mal": 101},
                ),
                (
                    "netflix_season",
                    {
                        "id": "123",
                        "scope": "season",
                        "mal": 101,
                        "full_season": True,
                        "offset": 12,
                    },
                ),
            ):
                path.write_text(json.dumps([row]), encoding="utf-8")
                with self.assertRaises(ValueError):
                    normalize_authorized(path, provider)
