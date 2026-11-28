"""Bounded, permission-gated TioAnime metadata catalogue collection."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from anime_mapping_db.crawler_policy import PacedClient, load_policy, user_agent
from anime_mapping_db.malsync_authorized import normalize_authorized
from anime_mapping_db.malsync_native import slug_id

ORIGIN = "https://tioanime.com"
DIRECTORY = ORIGIN + "/directorio"
_JIKAN = re.compile(
    r"https?://api\.jikan\.moe/v[0-9]+/anime/([1-9][0-9]*)\b", re.I
)


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slugs: set[str] = set()
        self.pages: set[int] = {1}

    def handle_starttag(self, tag, attrs) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        parts = urlsplit(urljoin(DIRECTORY, href))
        if parts.scheme != "https" or parts.netloc != "tioanime.com":
            return
        match = re.fullmatch(r"/anime/([^/]+)/?", parts.path)
        if match and (slug := slug_id(match[1])):
            self.slugs.add(slug)
        if parts.path.rstrip("/") == "/directorio":
            page = parse_qs(parts.query).get("p", ["1"])[0]
            if page.isascii() and page.isdecimal() and int(page) > 0:
                self.pages.add(int(page))


def fetch_tioanime(client: httpx.Client, url: str) -> list[dict]:
    if url != DIRECTORY:
        raise ValueError("Unverified TioAnime catalogue URL")
    paced = PacedClient(client, load_policy("tioanime"))
    robots_response = paced.get(ORIGIN + "/robots.txt")
    if robots_response.status_code != 200 or "<html" in robots_response.text.lower():
        raise ValueError("TioAnime robots.txt could not be verified")
    # The stdlib parser does not implement wildcard disallow rules consistently.
    # Fail closed rather than risk fetching a disallowed path.
    for line in robots_response.text.splitlines():
        rule = line.split("#", 1)[0].strip().lower()
        if rule.startswith("disallow:") and ("*" in rule or "$" in rule):
            raise ValueError("Complex robots.txt rule requires operator review")
    robots = RobotFileParser()
    robots.parse(robots_response.text.splitlines())

    def get_html(target: str) -> str:
        if not robots.can_fetch(user_agent(), target):
            raise ValueError("TioAnime robots.txt disallows metadata request")
        response = paced.get(target)
        if response.status_code != 200:
            raise ValueError("Unexpected TioAnime response")
        return response.text

    page = 1
    last = None
    catalogue: set[str] = set()
    while last is None or page <= last:
        target = DIRECTORY if page == 1 else f"{DIRECTORY}?p={page}"
        links = _Links()
        links.feed(get_html(target))
        if not links.slugs:
            raise ValueError("Empty TioAnime catalogue page")
        if last is None:
            last = max(links.pages)
            if last > 500:
                raise ValueError("Unverified catalogue pagination")
        if catalogue.intersection(links.slugs):
            raise ValueError("Duplicate IDs across TioAnime catalogue pages")
        if page < last and len(links.slugs) != 20:
            raise ValueError("Incomplete intermediate TioAnime catalogue page")
        catalogue.update(links.slugs)
        page += 1

    rows = []
    for slug in sorted(catalogue):
        html = get_html(f"{ORIGIN}/anime/{slug}")
        if not re.search(r"<h1(?:\s|>)", html, re.I):
            raise ValueError("Invalid TioAnime metadata page")
        ids = set(_JIKAN.findall(html))
        # Multiple explicit references are ambiguous and never guessed.
        rows.append(
            {
                "id": slug,
                "scope": "title",
                "mal": next(iter(ids)) if len(ids) == 1 else None,
            }
        )
    return rows


def download_tioanime(url: str, target: Path, *, timeout: float) -> None:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        headers={"Accept": "text/html,text/plain", "User-Agent": user_agent()},
    ) as client:
        rows = fetch_tioanime(client, url)
    target.write_text(json.dumps(rows), encoding="utf-8")
    normalize_authorized(target, "tioanime")
