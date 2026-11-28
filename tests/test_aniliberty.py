from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from anime_mapping_db.aniliberty import _fetch_catalog, import_aniliberty_enrichment
from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord


class AniLibertyTests(unittest.TestCase):
    def test_catalog_projection(self) -> None:
        def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.params["include"], "id,mal.id,shikimori.id")
            page = int(request.url.params["page"])
            start = (page - 1) * 50
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": index + 1,
                            "mal": {"id": index + 100},
                            "shikimori": None,
                            "description": "not retained",
                        }
                        for index in range(start, min(51, start + 50))
                    ],
                    "meta": {
                        "pagination": {
                            "total": 51,
                            "total_pages": 2,
                            "current_page": page,
                        }
                    },
                },
            )

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            rows = _fetch_catalog(client, "https://example.invalid/catalog")
        self.assertEqual(len(rows), 51)
        self.assertEqual(rows[0], {"id": "1", "mal": "100", "shikimori": None})

    def test_catalog_rejects_partial_results(self) -> None:
        def respond(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": [{"id": 1, "mal": {"id": 100}}],
                    "meta": {
                        "pagination": {
                            "total": 51,
                            "total_pages": 2,
                            "current_page": 1,
                        }
                    },
                },
            )

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            with self.assertRaises(ValueError):
                _fetch_catalog(client, "https://example.invalid/catalog")

    def test_native_ids_only_for_unambiguous_existing_titles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = MappingSourceSpec(
                "base", "https://example.invalid/base", "test", True, "test"
            )
            source = root / "catalog.json"
            source.write_text(
                json.dumps(
                    [
                        {"id": "1", "mal": "101", "shikimori": "201"},
                        {"id": "2", "mal": "102"},
                        {"id": "3", "mal": "102"},
                        {"id": "4", "mal": "103", "shikimori": "204"},
                        {"id": "5", "mal": "999"},
                        {"id": "6", "shikimori": "205"},
                        {"id": "7", "mal": "106"},
                        {"id": "8", "mal": "107", "shikimori": "999"},
                    ]
                ),
                encoding="utf-8",
            )
            with MappingDatabaseBuilder(
                root / "runtime.db", evidence_path=root / "evidence.db"
            ) as builder:
                records = [
                    MappingRecord(
                        str(index),
                        {
                            "mal": (str(100 + index),),
                            "shikimori": (str(200 + index),),
                            **({"aniliberty": ("800",)} if index == 6 else {}),
                        },
                        "trusted",
                        95,
                    )
                    for index in range(1, 8)
                ]
                builder.ingest_dataset(
                    spec, records, sha256="base", downloaded_at="2026-11-28"
                )
                builder.finalize(built_at="2026-11-28")
                imported = list(import_aniliberty_enrichment(source, builder.conn))
                self.assertEqual(
                    {record.ids["aniliberty"][0] for record in imported}, {"1", "6"}
                )
                self.assertEqual(len(imported), 3)
                self.assertTrue(
                    all(
                        record.evidence_group == "aniliberty-native"
                        for record in imported
                    )
                )
