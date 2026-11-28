from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from anime_mapping_db.yummyani import download_yummyani, fetch_catalog


class YummyAnimeTests(unittest.TestCase):
    def test_projection_and_offset_pagination(self) -> None:
        offsets = []

        def respond(request):
            offset = int(request.url.params["offset"])
            offsets.append(offset)
            self.assertEqual(request.url.params["limit"], "100")
            self.assertEqual(request.url.params["sort"], "id")
            if offset == 2:
                return httpx.Response(200, json={"response": []})
            return httpx.Response(
                200,
                json={
                    "response": [
                        {
                            "anime_id": offset + 1,
                            "anime_url": f"title-{offset + 1}",
                            "remote_ids": {"myanimelist_id": 101 + offset},
                            "description": "discard",
                        }
                    ]
                },
            )

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            rows = fetch_catalog(client, "https://example.invalid/anime")
        self.assertEqual(offsets, [0, 1, 2])
        self.assertEqual(
            rows[0],
            {"id": "1", "slug": "title-1", "mal": "101", "shikimori": None},
        )

    def test_no_token_means_no_http_request(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict("os.environ", {"MAPPINGS_YUMMYANI_APPLICATION_TOKEN": ""}),
            patch("anime_mapping_db.yummyani.httpx.Client") as client,
        ):
            with self.assertRaises(ValueError):
                download_yummyani(
                    "https://api.yani.tv/anime",
                    Path(directory) / "snapshot",
                    timeout=5,
                )
            client.assert_not_called()
