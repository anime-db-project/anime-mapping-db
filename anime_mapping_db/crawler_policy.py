"""Conservative per-source pacing, adapted from anime-timestamp-db."""

from __future__ import annotations

import json
import os
import random
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx


@dataclass(frozen=True)
class SourcePolicy:
    enabled: bool
    max_requests: int
    per_second: int
    per_minute: int
    per_hour: int
    delay_seconds: tuple[float, float]
    retry_429_wait_seconds: float
    max_429_wait_seconds: float


def load_policy(source: str) -> SourcePolicy:
    path = Path(__file__).with_name("crawler_sources.json")
    row = json.loads(path.read_text(encoding="utf-8"))[source]
    policy = SourcePolicy(**row)
    lo, hi = policy.delay_seconds
    if (
        type(policy.enabled) is not bool
        or not 1 <= policy.max_requests <= 5000
        or min(policy.per_second, policy.per_minute, policy.per_hour) < 1
        or not 0 <= lo <= hi <= 10
        or not 0 <= policy.retry_429_wait_seconds <= policy.max_429_wait_seconds <= 600
    ):
        raise ValueError(f"Invalid crawler policy for {source}")
    return policy


def user_agent() -> str:
    return os.environ.get("MAPPING_CRAWLER_USER_AGENT", "").strip() or (
        "anime-mapping-db/0.4 (+https://github.com/anime-db-project/anime-mapping-db)"
    )


def retry_after(response: httpx.Response, default: float) -> float:
    value = response.headers.get("Retry-After", "").strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            return max(0.0, (date - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return default


class PacedClient:
    def __init__(self, client: httpx.Client, policy: SourcePolicy) -> None:
        if not policy.enabled:
            raise RuntimeError("Crawler disabled by source policy")
        self.client = client
        self.policy = policy
        self.requests = 0
        self.previous = None
        self.windows = (
            (1.0, policy.per_second, deque()),
            (60.0, policy.per_minute, deque()),
            (3600.0, policy.per_hour, deque()),
        )

    def _pace(self) -> None:
        if self.requests >= self.policy.max_requests:
            raise RuntimeError("Crawler request budget exhausted")
        now = time.monotonic()
        wait = 0.0
        if self.previous is not None:
            wait = max(
                wait, self.previous + random.uniform(*self.policy.delay_seconds) - now
            )
        for window, limit, seen in self.windows:
            while seen and now - seen[0] >= window:
                seen.popleft()
            if len(seen) >= limit:
                wait = max(wait, seen[0] + window - now)
        if wait > 0:
            time.sleep(wait + 0.01)
        now = time.monotonic()
        for window, _, seen in self.windows:
            while seen and now - seen[0] >= window:
                seen.popleft()
            seen.append(now)
        self.previous = now
        self.requests += 1

    def get(self, url: str, **kwargs) -> httpx.Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        for attempt in range(2):
            self._pace()
            response = self.client.request(method, url, **kwargs)
            if response.status_code != 429:
                response.raise_for_status()
                return response
            delay = retry_after(response, self.policy.retry_429_wait_seconds)
            if (
                attempt
                or delay > self.policy.max_429_wait_seconds
                or self.requests >= self.policy.max_requests
            ):
                response.raise_for_status()
            time.sleep(max(0.1, delay))
        raise AssertionError("Unreachable")
