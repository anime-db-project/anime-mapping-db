from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from anime_mapping_db.authorized_export_api import fetch_export


class ExportApiTests(unittest.TestCase):
    def test_pagination_and_total(self) -> None:
        def respond(request):
            second = request.url.params.get("page") == "2"
            return httpx.Response(
                200,
                json={
                    "rows": [{"id": "2" if second else "1"}],
                    "total": 2,
                    "next": None if second else "?page=2",
                },
            )

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            self.assertEqual(
                fetch_export(client, "https://example.invalid/export"),
                [{"id": "1"}, {"id": "2"}],
            )

    def test_rejects_cross_origin_or_short_export(self) -> None:
        for next_page in ("https://other.invalid/export", None):
            calls = []

            def respond(request):
                calls.append(request.url)
                return httpx.Response(
                    200, json={"rows": [{"id": "1"}], "total": 2, "next": next_page}
                )

            with (
                httpx.Client(transport=httpx.MockTransport(respond)) as client,
                patch("anime_mapping_db.crawler_policy.time.sleep"),
            ):
                with self.assertRaises(ValueError):
                    fetch_export(client, "https://example.invalid/export")
            self.assertEqual(len(calls), 1)
