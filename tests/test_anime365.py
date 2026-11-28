from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from anime_mapping_db.anime365 import fetch_catalog, import_anime365_enrichment
from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.importers.native_ids import enrich_native_ids


class Anime365Tests(unittest.TestCase):
    def test_cursor_projection(self) -> None:
        pages = {
            0: [{"id": 2, "myAnimeListId": 101, "title": "discarded"}],
            2: [{"id": 5, "myAnimeListId": 0}],
            5: [],
        }

        def respond(request):
            params = request.url.params
            self.assertEqual(params["fields"], "id,myAnimeListId")
            self.assertEqual(params["order"], "id")
            return httpx.Response(200, json={"data": pages[int(params["afterId"])]})

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            rows = fetch_catalog(client, "https://example.invalid/series")
        self.assertEqual(rows, [{"id": "2", "mal": "101"}, {"id": "5", "mal": None}])

    def test_repeated_cursor_rejected(self) -> None:
        with (
            httpx.Client(
                transport=httpx.MockTransport(
                    lambda _: httpx.Response(
                        200, json={"data": [{"id": 2, "myAnimeListId": 101}]}
                    )
                )
            ) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            with self.assertRaises(ValueError):
                fetch_catalog(client, "https://example.invalid/series")

    def test_api_error_in_http_200(self) -> None:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={"error": {"code": 403}})
            )
        ) as client:
            with self.assertRaises(ValueError):
                fetch_catalog(client, "https://example.invalid/series")

    def test_native_claims_are_conflict_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "source.json"
            rows = [
                {"id": "1", "mal": "101"},
                {"id": "2", "mal": "102"},
                {"id": "3", "mal": "102"},
                {"id": "4", "mal": "103", "anilist": "204"},
                {"id": "5", "mal": "999"},
                {"id": "6", "mal": None},
                {"id": "7", "mal": "105", "anilist": "205"},
                {"id": "8", "mal": "106", "anilist": "999"},
                {"id": "9", "mal": "107"},
                {"id": "9", "mal": "108"},
            ]
            path.write_text(json.dumps(rows), encoding="utf-8")
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
                        for i in range(1, 9)
                    ],
                    sha256="base",
                    downloaded_at="2026-11-28",
                )
                builder.finalize(built_at="2026-11-28")
                imported = list(import_anime365_enrichment(path, builder.conn))
                self.assertEqual(
                    {item.ids["anime365"][0] for item in imported}, {"1", "7"}
                )
                self.assertEqual(len(imported), 3)
                unknown = list(
                    enrich_native_ids(
                        [{"id": "1", "mal": "999"}],
                        builder.conn,
                        namespace="example",
                        lineage="example-native",
                    )
                )
                self.assertEqual(unknown, [])
