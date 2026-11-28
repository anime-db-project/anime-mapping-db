from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

import httpx

from anime_mapping_db.kodik_audit import audit, next_cursor


class KodikAuditTests(unittest.TestCase):
    def test_cursor_does_not_forward_foreign_token_or_url(self) -> None:
        self.assertEqual(
            next_cursor("https://kodik-api.com/list?token=old&next=YQ%3D%3D"),
            "YQ==",
        )
        for url in (
            "https://example.invalid/list?next=YQ",
            "https://kodik-api.com/search?next=YQ",
            "https://kodik-api.com/list?next=YQ&next=Yg",
        ):
            with self.assertRaises(ValueError):
                next_cursor(url)

    def test_many_materials_one_title_without_exporting_ids(self) -> None:
        requests = []

        def respond(request):
            self.assertEqual(request.method, "POST")
            self.assertEqual(str(request.url), "https://kodik-api.com/list")
            params = parse_qs(request.content.decode())
            requests.append(params)
            self.assertEqual(params["token"], ["own-token"])
            self.assertEqual(params["types"], ["anime,anime-serial"])
            second = "next" in params
            if second:
                self.assertEqual(params["next"], ["YQ=="])
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "serial-2" if second else "serial-1",
                            "type": "anime-serial",
                            "shikimori_id": "20",
                            "translation": {"id": 2 if second else 1},
                            "kinopoisk_id": "99",
                            "imdb_id": "tt123",
                            "title": "discard",
                            "link": "discard",
                        }
                    ],
                    "next_page": (
                        None
                        if second
                        else "https://kodik-api.com/list?token=foreign&next=YQ%3D%3D"
                    ),
                },
            )

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            report = audit(client, "own-token")
        self.assertEqual(len(requests), 2)
        self.assertEqual(report["distinct_materials"], 2)
        self.assertEqual(report["distinct_shikimori_ids"], 1)
        self.assertEqual(report["shikimori_ids_with_multiple_materials"], 1)
        self.assertNotIn("serial-1", str(report))
        self.assertNotIn("own-token", str(report))

    def test_no_key_means_no_request(self) -> None:
        with httpx.Client(
            transport=httpx.MockTransport(lambda _: self.fail("Unexpected request"))
        ) as client:
            with self.assertRaises(ValueError):
                audit(client, "")
