from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.malsync_native import (
    fetch_animelib,
    fetch_docchi,
    import_adkami,
    import_animelib,
    import_docchi,
    normalize_adkami,
    normalize_syncdata,
    slug_id,
)


class NativeCatalogueTests(unittest.TestCase):
    def test_docchi_slug_preserves_native_punctuation_and_unicode(self) -> None:
        for slug in ("-kouhai", "historié", "bang-dream!-yume∞mita"):
            self.assertEqual(slug_id(slug), slug)
        for slug in ("../title", "a/b", "a?b", "a b", "%2F"):
            self.assertIsNone(slug_id(slug))

    def test_syncdata_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            for provider, native in (
                ("aniyan", 11943),
                ("anidream", "no-game-no-life"),
                ("aninexus", 33),
            ):
                path.write_text(
                    json.dumps(
                        [{"anime_id": native, "myanimelist_id": 101, "anilist_id": 201}]
                    ),
                    encoding="utf-8",
                )
                normalize_syncdata(path, provider)
                self.assertEqual(
                    json.loads(path.read_text("utf-8")),
                    [{"id": str(native), "mal": "101", "anilist": "201"}],
                )
                original = path.read_bytes()
                normalize_syncdata(path, provider)
                self.assertEqual(path.read_bytes(), original)

    def test_docchi_projects_explicit_ids(self) -> None:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200, json=[{"slug": "title-1", "mal_id": 101, "title": "discard"}]
                )
            )
        ) as client:
            rows = fetch_docchi(client, "https://example.invalid/catalogue")
        self.assertEqual(rows, [{"id": "title-1", "mal": "101"}])

    def test_animelib_pages_and_duplicate_rejection(self) -> None:
        def run(duplicate: bool):
            def respond(request):
                self.assertEqual(request.url.params["sort_by"], "name")
                page = int(request.url.params["page"])
                native = 1 if duplicate else page
                return httpx.Response(
                    200,
                    json={
                        "data": [
                            {
                                "id": native,
                                "model": "anime",
                                "anilist_id": 200 + page,
                                "anilist_href": f"https://anilist.co/anime/{200 + page}",
                                "shikimori_href": f"https://shikimori.io/animes/{300 + page}",
                            }
                        ],
                        "meta": {"current_page": page, "per_page": 1},
                        "links": {"next": "not-followed" if page == 1 else None},
                    },
                )

            with (
                httpx.Client(transport=httpx.MockTransport(respond)) as client,
                patch("anime_mapping_db.crawler_policy.time.sleep"),
            ):
                return fetch_animelib(client, "https://example.invalid/catalogue")

        self.assertEqual(
            run(False),
            [
                {"id": "1", "anilist": "201", "shikimori": "301"},
                {"id": "2", "anilist": "202", "shikimori": "302"},
            ],
        )
        with self.assertRaises(ValueError):
            run(True)

    def test_three_importers_preserve_identity(self) -> None:
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
                            {
                                "mal": (str(100 + i),),
                                "anilist": (str(200 + i),),
                                "shikimori": (str(300 + i),),
                            },
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
                    json.dumps([{"id": "test-title", "mal": "101"}]),
                    encoding="utf-8",
                )
                records = list(import_docchi(path, builder.conn))
                self.assertEqual(records[0].ids["docchi"], ("test-title",))
                path.write_text(
                    json.dumps(
                        [
                            {"id": "5", "anilist": "201", "shikimori": "301"},
                            {"id": "6", "anilist": "202", "shikimori": "301"},
                        ]
                    ),
                    encoding="utf-8",
                )
                self.assertEqual(list(import_animelib(path, builder.conn)), [])
                path.write_text(
                    json.dumps([{"id": "123-2-1", "mal_id": 101, "anilist_id": 201}]),
                    encoding="utf-8",
                )
                normalize_adkami(path)
                records = list(import_adkami(path, builder.conn))
                self.assertEqual(len(records), 2)
                self.assertEqual(records[0].ids["adkami_season"], ("123-2-1",))
