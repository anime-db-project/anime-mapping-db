from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from anime_mapping_db.tioanime import DIRECTORY, fetch_tioanime


class TioAnimeTests(unittest.TestCase):
    def test_catalogue_projects_only_unambiguous_mal(self) -> None:
        calls = []

        def respond(request):
            calls.append(request.url.path)
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /\n")
            if request.url.path == "/directorio":
                return httpx.Response(
                    200, text='<a href="/anime/a">a</a><a href="/anime/b">b</a>'
                )
            if request.url.path == "/anime/a":
                return httpx.Response(
                    200, text="<h1>a</h1>https://api.jikan.moe/v4/anime/101"
                )
            return httpx.Response(
                200,
                text="<h1>b</h1>https://api.jikan.moe/v4/anime/102 "
                "https://api.jikan.moe/v4/anime/103",
            )

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            rows = fetch_tioanime(client, DIRECTORY)
        self.assertEqual(
            rows,
            [
                {"id": "a", "scope": "title", "mal": "101"},
                {"id": "b", "scope": "title", "mal": None},
            ],
        )
        self.assertEqual(calls, ["/robots.txt", "/directorio", "/anime/a", "/anime/b"])

    def test_robots_denial_prevents_catalogue_request(self) -> None:
        calls = []

        def respond(request):
            calls.append(request.url.path)
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            with self.assertRaises(ValueError):
                fetch_tioanime(client, DIRECTORY)
        self.assertEqual(calls, ["/robots.txt"])
