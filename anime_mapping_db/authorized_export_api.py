"""Collect an explicitly configured authorized JSON export gateway.

The gateway contract is ours, not a claim about any undocumented native API.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from anime_mapping_db.config import MappingSourceSpec, source_preflight
from anime_mapping_db.crawler_policy import PacedClient, load_policy, user_agent


def _origin(url: str) -> tuple:
    p = urlsplit(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError("Invalid export URL")
    return p.scheme, p.hostname, p.port or 443


def fetch_export(client: httpx.Client, url: str) -> list[dict]:
    origin = _origin(url)
    paced = PacedClient(client, load_policy("authorized_export_api"))
    seen_urls: set[str] = set()
    seen_rows: set[str] = set()
    rows: list[dict] = []
    total = None
    while url:
        if _origin(url) != origin or url in seen_urls:
            raise ValueError("Cross-origin or cyclic export pagination")
        seen_urls.add(url)
        try:
            page = paced.get(url).json()
        except (httpx.HTTPError, ValueError) as exc:
            # Do not emit request query parameters or server response bodies.
            raise ValueError("Export API request or JSON validation failed") from exc
        if not isinstance(page, dict) or not {"rows", "total", "next"} <= page.keys():
            raise ValueError("Invalid export page envelope")
        count = page["total"]
        if type(count) is not int or not 1 <= count <= 200_000:
            raise ValueError("Invalid export total")
        if total is None:
            total = count
        if total != count or not isinstance(page["rows"], list) or not page["rows"]:
            raise ValueError("Incomplete or inconsistent export page")
        for row in page["rows"]:
            if not isinstance(row, dict):
                raise ValueError("Invalid export row")
            encoded = json.dumps(row, sort_keys=True, separators=(",", ":"))
            if encoded in seen_rows:
                raise ValueError("Duplicate row across export pages")
            seen_rows.add(encoded)
            rows.append(row)
        if len(rows) > total:
            raise ValueError("Export exceeds declared total")
        next_page = page["next"]
        if next_page is None:
            if len(rows) != total:
                raise ValueError("Export terminated before declared total")
            break
        if (
            not isinstance(next_page, str)
            or not next_page.strip()
            or len(rows) == total
        ):
            raise ValueError("Invalid export continuation")
        url = urljoin(url, next_page)
    return rows


def download_export_api(
    spec: MappingSourceSpec, target: Path, *, timeout: float
) -> None:
    if not spec.export_api:
        raise ValueError("Export API transport not selected")
    reason = source_preflight(spec)
    if reason:
        raise ValueError(f"Source preflight: {reason}")
    headers = {"Accept": "application/json", "User-Agent": user_agent()}
    if spec.credential_env:
        headers["Authorization"] = "Bearer " + os.environ[spec.credential_env].strip()
    with httpx.Client(
        timeout=timeout, follow_redirects=False, headers=headers
    ) as client:
        rows = fetch_export(client, spec.url)
    target.write_text(json.dumps(rows), encoding="utf-8")
