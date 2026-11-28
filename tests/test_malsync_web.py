from __future__ import annotations

import unittest
from unittest.mock import patch

import httpx

from anime_mapping_db.malsync_web import extract_title, fetch_web_catalogue


class WebCatalogueTests(unittest.TestCase):
    def test_syncdata_identity(self) -> None:
        self.assertEqual(
            extract_title(
                "aniyan",
                "https://aniyan.net/a/123/test",
                '<script id="syncData">{"page":"anime","anime_id":123,'
                '"myanimelist_id":456}</script>',
            ),
            {"id": 123, "mal": 456, "anilist": None},
        )
        with self.assertRaises(ValueError):
            extract_title(
                "aniyan",
                "https://aniyan.net/a/123/test",
                '<script id="syncData">{"page":"episode","anime_id":123}</script>',
            )

    def test_provider_specific_links_and_ids(self) -> None:
        row = extract_title(
            "witanime",
            "https://witanime.pics/anime/test",
            '<h1>Test</h1><a class="anime-mal" '
            'href="https://myanimelist.net/anime/123">MAL</a>'
            '<a href="https://myanimelist.net/anime/999">Related</a>',
        )
        self.assertEqual(row["mal"], "123")
        row = extract_title(
            "animepahe",
            "https://animepahe.com/anime/session",
            '<meta name="id" content="789"><meta name="mal" content="123">',
        )
        self.assertEqual(row["id"], "789")

    def test_sitemap_does_not_fetch_episode_or_other_host(self) -> None:
        calls = []
        origin = "https://witanime.pics"

        def respond(request):
            calls.append(str(request.url))
            if request.url.path == "/robots.txt":
                return httpx.Response(
                    200,
                    text="User-agent: *\nAllow: /\nSitemap: " + origin + "/sitemap.xml",
                )
            if request.url.path == "/sitemap.xml":
                return httpx.Response(
                    200,
                    text="<urlset><url><loc>"
                    + origin
                    + "/anime/test</loc></url><url><loc>"
                    + origin
                    + "/episode/test</loc></url><url><loc>"
                    "https://other.invalid/anime/test</loc></url></urlset>",
                )
            return httpx.Response(
                200,
                text='<h1>Test</h1><a class="anime-mal" '
                'href="https://myanimelist.net/anime/123">MAL</a>',
            )

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            rows = fetch_web_catalogue(client, "witanime", origin)
        self.assertEqual(rows[0]["mal"], "123")
        self.assertEqual(
            calls,
            [origin + "/robots.txt", origin + "/sitemap.xml", origin + "/anime/test"],
        )

    def test_disallowed_sitemap_is_not_fetched(self) -> None:
        calls = []

        def respond(request):
            calls.append(request.url.path)
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            with self.assertRaises(ValueError):
                fetch_web_catalogue(client, "witanime", "https://witanime.pics")
        self.assertEqual(calls, ["/robots.txt"])

    def test_animeunity_uses_native_archive_and_title_metadata(self) -> None:
        calls = []
        origin = "https://animeunity.cx"

        def respond(request):
            calls.append(str(request.url))
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /\n")
            if request.url.path == "/api/archive":
                page = int(request.url.params["page"])
                return httpx.Response(
                    200,
                    json={
                        "current_page": page,
                        "last_page": 2,
                        "data": [{"id": page, "slug": f"title-{page}"}],
                    },
                )
            native = int(request.url.path.split("/")[-1].split("-")[0])
            return httpx.Response(
                200,
                text=f'<h1>Title</h1><a href="https://myanimelist.net/anime/{100 + native}">MAL</a>',
            )

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep"),
        ):
            rows = fetch_web_catalogue(client, "animeunity", origin)
        self.assertEqual([row["id"] for row in rows], ["1-title-1", "2-title-2"])
        self.assertEqual([row["mal"] for row in rows], ["101", "102"])
        self.assertEqual(len(calls), 5)
