"""Direct public title metadata collectors based on MALSync adapter markup.

Sitemaps are discovery indexes, never mapping evidence. No video, login,
internal playback API, mirror fallback, or title matching is used.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import httpx

from anime_mapping_db.crawler_policy import PacedClient, load_policy, user_agent
from anime_mapping_db.malsync_authorized import normalize_authorized
from anime_mapping_db.malsync_native import normalize_syncdata, slug_id
from anime_mapping_db.native_ids import positive_id

# The URL shapes are from MALSync's public adapters, not guessed API routes.
WEB_SOURCES = {
    "aniyan": ("https://aniyan.net", r"/a/([1-9][0-9]*)/[^/]+/?"),
    "anidream": ("https://anidream.cc", r"/series/([^/]+)/?"),
    "aninexus": ("https://aninexus.to", r"/tv-show/([^/]+)/?"),
    "animepahe": ("https://animepahe.com", r"/anime/([^/]+)/?"),
    "animeunity": ("https://animeunity.cx", r"/anime/([1-9][0-9]*-[^/]+)/?"),
    "animeonsen": ("https://www.animeonsen.xyz", r"/details/([^/]+)/?"),
    "animewho": ("https://animewho.com", r"/ceviriler/anime/([^/]+)/?"),
    "hinatasoul": ("https://hinatasoul.com", r"/anime(?:-dublado)?/([^/]+)/?"),
    "witanime": ("https://witanime.pics", r"/anime/([^/]+)/?"),
    "miruro": ("https://miruro.to", r"/info/([A-Za-z0-9_-]{20,64})/[^/]+/?"),
}
_SYNC = {"aniyan", "anidream", "aninexus"}
_MAX_XML_BYTES = 10_000_000


def _same_origin(url: str, origin: str) -> bool:
    parts = urlsplit(url)
    base = urlsplit(origin)
    return (
        parts.scheme == "https"
        and parts.netloc == base.netloc
        and not parts.fragment
        and not parts.username
        and not parts.password
    )


def _external_link(value: str) -> tuple[str, str] | None:
    parts = urlsplit(value)
    if parts.scheme != "https" or parts.username or parts.password:
        return None
    providers = {
        "myanimelist.net": "mal",
        "www.myanimelist.net": "mal",
        "anilist.co": "anilist",
        "www.anilist.co": "anilist",
    }
    match = re.fullmatch(r"/anime/([1-9][0-9]*)(?:/[^/]*)?/?", parts.path)
    if match and parts.hostname in providers:
        return providers[parts.hostname], match[1]
    return None


class _Metadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, set[str]] = defaultdict(set)
        self.links: list[dict[str, str]] = []
        self.who: list[dict[str, str]] = []
        self.sync: list[str] = []
        self._capture: str | None = None
        self._parts: list[str] = []
        self.h1 = False

    def handle_starttag(self, tag, attrs) -> None:
        a = {key: value or "" for key, value in attrs}
        if tag == "h1":
            self.h1 = True
        if tag == "meta" and a.get("name") and a.get("content"):
            self.meta[a["name"]].add(a["content"])
        if tag == "a" and a.get("href"):
            self.links.append(a)
        if a.get("id") == "malsync-data":
            self.who.append(a)
        if a.get("id") == "syncData":
            if self._capture is not None:
                raise ValueError("Nested syncData markup")
            self._capture = tag
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._capture:
            self.sync.append("".join(self._parts))
            self._capture = None


def _one(values: set[str]) -> str | None:
    if len(values) > 1:
        raise ValueError("Contradictory explicit metadata")
    return next(iter(values), None)


def _link_ids(links: list[dict[str, str]]) -> dict:
    ids: dict[str, set[str]] = defaultdict(set)
    for link in links:
        anchor = _external_link(link["href"])
        if anchor:
            ids[anchor[0]].add(anchor[1])
    return {provider: _one(values) for provider, values in ids.items()}


def extract_title(provider: str, url: str, html: str) -> dict:
    origin, pattern = WEB_SOURCES[provider]
    match = re.fullmatch(pattern, urlsplit(url).path)
    if not _same_origin(url, origin) or not match or urlsplit(url).query:
        raise ValueError("Unexpected title URL")
    native = match[1]
    page = _Metadata()
    page.feed(html)
    if provider in _SYNC:
        if len(page.sync) != 1:
            raise ValueError("Expected a single native syncData block")
        data = json.loads(page.sync[0])
        if not isinstance(data, dict) or data.get("page") != "anime":
            raise ValueError("Not a title-level syncData record")
        if provider != "aninexus" and str(data.get("anime_id")) != native:
            raise ValueError("Native ID does not match catalogue URL")
        series = data.get("series_url")
        if series and urlsplit(urljoin(url, series)).path.rstrip("/") != urlsplit(
            url
        ).path.rstrip("/"):
            raise ValueError("syncData refers to another title")
        return {
            "id": data.get("anime_id"),
            "mal": data.get("mal_id", data.get("myanimelist_id")),
            "anilist": data.get("anilist_id"),
        }
    row = {"id": native, "scope": "title"}
    if provider == "animepahe":
        native = positive_id(_one(page.meta["id"]))
        if native is None:
            raise ValueError("Missing numeric animepahe title ID")
        row["id"] = native
        for anchor, names in (
            ("mal", ("mal", "myanimelist")),
            ("anilist", ("anilist",)),
            ("kitsu", ("kitsu",)),
        ):
            values = set().union(*(page.meta[name] for name in names))
            value = _one(values)
            if value is not None and positive_id(value) is None:
                raise ValueError("Invalid external meta ID")
            row[anchor] = value
    elif provider == "animeonsen":
        value = _one(page.meta["ao-content-mal-url"])
        if value:
            row.update(_link_ids([{"href": value}]))
    elif provider == "animewho":
        if len(page.who) != 1:
            raise ValueError("Missing AnimeWho title metadata")
        meta = page.who[0]
        if meta.get("type") != "anime" or meta.get("series_id") != native:
            raise ValueError("AnimeWho identity mismatch")
        row["id"] = "anime-" + native
        if meta.get("mal_url"):
            row.update(_link_ids([{"href": meta["mal_url"]}]))
    elif provider in {"hinatasoul", "witanime"}:
        cls = "mbottom" if provider == "hinatasoul" else "anime-mal"
        row.update(
            _link_ids(
                [
                    link
                    for link in page.links
                    if cls in link.get("class", "").split()
                ]
            )
        )
        if provider == "hinatasoul":
            row["id"] = native.removesuffix("-dublado")
    else:
        # These two upstream adapters explicitly select provider links in title pages.
        row.update(_link_ids(page.links))
        if provider == "miruro":
            row["native_id_verified"] = True
    if provider != "animepahe" and not page.h1 and not page.who:
        if provider != "animeonsen" or not page.meta["ao-content-mal-url"]:
            raise ValueError("Title markup missing")
    if not slug_id(row["id"]):
        raise ValueError("Invalid native title ID")
    return row


def fetch_web_catalogue(client: httpx.Client, provider: str, origin: str) -> list[dict]:
    expected, pattern = WEB_SOURCES[provider]
    if origin != expected:
        raise ValueError("Unexpected catalogue origin")
    paced = PacedClient(client, load_policy(provider))
    response = paced.get(origin + "/robots.txt")
    if response.status_code != 200 or "<html" in response.text.lower():
        raise ValueError("Cannot verify robots.txt")
    rules = response.text.splitlines()
    for line in rules:
        directive = line.split("#", 1)[0].strip().lower()
        if directive.startswith("disallow:") and ("*" in directive or "$" in directive):
            raise ValueError("Complex robots rules require verification")
    robots = RobotFileParser()
    robots.parse(rules)

    def get(url: str) -> httpx.Response:
        if not _same_origin(url, origin) or not robots.can_fetch(user_agent(), url):
            raise ValueError("Off-origin or disallowed catalogue URL")
        response = paced.get(url)
        if response.status_code != 200:
            raise ValueError("Unexpected catalogue response")
        return response

    pending = [
        line.split(":", 1)[1].strip()
        for line in rules
        if line.strip().lower().startswith("sitemap:")
    ] or [origin + "/sitemap.xml"]
    seen: set[str] = set()
    titles: set[str] = set()
    while pending:
        sitemap = pending.pop()
        if sitemap in seen:
            continue
        if len(seen) >= 64:
            raise ValueError("Too many sitemap indexes")
        seen.add(sitemap)
        body = get(sitemap).content
        if len(body) > _MAX_XML_BYTES or b"<!DOCTYPE" in body.upper():
            raise ValueError("Invalid or oversized sitemap")
        root = ElementTree.fromstring(body)
        kind = root.tag.rsplit("}", 1)[-1]
        if kind not in {"sitemapindex", "urlset"}:
            raise ValueError("Unrecognized sitemap format")
        for node in root:
            loc = next(
                (
                    child.text
                    for child in node
                    if child.tag.rsplit("}", 1)[-1] == "loc"
                ),
                None,
            )
            if not loc:
                continue
            if kind == "sitemapindex":
                if not _same_origin(loc, origin):
                    raise ValueError("Off-origin sitemap")
                pending.append(loc)
            elif _same_origin(loc, origin):
                parts = urlsplit(loc)
                if not parts.query and re.fullmatch(pattern, parts.path):
                    titles.add(loc.rstrip("/"))
    if not titles:
        raise ValueError("No title pages discovered in public sitemap")
    if len(titles) > paced.policy.max_requests - paced.requests:
        raise ValueError("Full catalogue exceeds source request budget")
    return [
        extract_title(provider, url, get(url).text)
        for url in sorted(titles)
    ]


def download_web_catalogue(
    provider: str, origin: str, target: Path, *, timeout: float
) -> None:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={"Accept": "text/html,application/xml,text/plain", "User-Agent": user_agent()},
    ) as client:
        rows = fetch_web_catalogue(client, provider, origin)
    target.write_text(json.dumps(rows), encoding="utf-8")
    if provider in _SYNC:
        normalize_syncdata(target, provider)
    else:
        normalize_authorized(target, provider)
