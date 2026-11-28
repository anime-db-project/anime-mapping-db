from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from anime_mapping_db.annict_api import fetch_catalog


class AnnictTests(unittest.TestCase):
    def test_id_projection_and_pagination(self) -> None:
        def respond(request):
            page = int(request.url.params["page"])
            self.assertEqual(request.url.params["fields"], "id,mal_anime_id")
            self.assertEqual(request.url.params["per_page"], "50")
            return httpx.Response(
                200,
                json={
                    "works": [
                        {"id": i, "mal_anime_id": str(i + 100)}
                        for i in (range(1, 51) if page == 1 else [51])
                    ],
                    "total_count": 51,
                    "next_page": 2 if page == 1 else None,
                },
            )

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            rows = fetch_catalog(client, "https://example.invalid/works")
        self.assertEqual(len(rows), 51)
        self.assertEqual(rows[-1], {"id": "51", "mal": "151"})

    def test_incomplete_catalogue_rejected(self) -> None:
        with httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "works": [{"id": 1, "mal_anime_id": "101"}],
                        "total_count": 2,
                        "next_page": None,
                    },
                )
            )
        ) as client:
            with self.assertRaises(ValueError):
                fetch_catalog(client, "https://example.invalid/works")
