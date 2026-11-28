from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.importers.aggregate_urls import (
    import_animap_id,
    import_athanasso,
    normalize_snapshot,
    parse_id,
)


class AggregateUrlTests(unittest.TestCase):
    def test_strict_urls(self) -> None:
        self.assertEqual(parse_id("https://anilist.co/anime/1"), ("anilist", "1"))
        self.assertEqual(
            parse_id("https://animenewsnetwork.com/encyclopedia/anime.php?id=13"),
            ("ann", "13"),
        )
        for url in (
            "https://evil.invalid/anilist.co/anime/1",
            "https://anilist.co.evil.invalid/anime/1",
            "https://anilist.co/anime/1/episode/2",
            "https://anilist.co/anime/01",
            "https://anilist.co/anime/1?other=2",
            "https://www.themoviedb.org/tv/1",
            "https://anilist.co@evil.invalid/anime/1",
        ):
            self.assertIsNone(parse_id(url))

    def test_normalize_and_safe_enrich(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "source.json"
            rows = [
                [
                    "https://anilist.co/anime/1",
                    "https://myanimelist.net/anime/101",
                    "https://kitsu.app/anime/301",
                ],
                [
                    "https://anilist.co/anime/2",
                    "https://myanimelist.net/anime/102",
                    "https://kitsu.app/anime/302",
                ],
                ["https://anilist.co/anime/3", "https://kitsu.app/anime/302"],
                [
                    "https://anilist.co/anime/4",
                    "https://myanimelist.net/anime/104",
                    "https://kitsu.app/anime/304",
                    "https://kitsu.app/anime/305",
                ],
                [
                    "https://anilist.co/anime/5",
                    "https://myanimelist.net/anime/106",
                    "https://kitsu.app/anime/306",
                ],
                [
                    "https://anilist.co/anime/7",
                    "https://myanimelist.net/anime/107",
                    "https://kitsu.app/anime/307",
                ],
                [
                    "https://anilist.co/anime/8",
                    "https://myanimelist.net/anime/108",
                    "https://kitsu.app/anime/308",
                ],
            ]
            path.write_text(
                json.dumps(
                    {"data": [{"sources": x, "title": "discard"} for x in rows]}
                ),
                encoding="utf-8",
            )
            normalize_snapshot(path)
            data = path.read_bytes()
            self.assertNotIn(b"discard", data)
            normalize_snapshot(path)
            self.assertEqual(data, path.read_bytes())
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
                            {
                                "anilist": (str(i),),
                                "mal": (str(i + 100),),
                                **({"kitsu": ("999",)} if i == 7 else {}),
                            },
                            "trusted",
                            95,
                        )
                        for i in range(1, 8)
                    ],
                    sha256="base",
                    downloaded_at="2026-11-28",
                )
                builder.finalize(built_at="2026-11-28")
                for importer in (import_animap_id, import_athanasso):
                    records = list(importer(path, builder.conn))
                    self.assertEqual(len(records), 2)
                    self.assertEqual({r.ids["kitsu"] for r in records}, {("301",)})
