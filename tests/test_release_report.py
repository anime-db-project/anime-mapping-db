from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from anime_mapping_db.crawler_policy import PacedClient, SourcePolicy
from anime_mapping_db.release_report import build_report, render


class CrawlerPolicyTests(unittest.TestCase):
    def test_retry_after_and_request_budget(self) -> None:
        policy = SourcePolicy(True, 2, 10, 10, 10, (0, 0), 10, 45)
        statuses = iter((429, 200))

        def respond(_request):
            return httpx.Response(next(statuses), headers={"Retry-After": "2"})

        with (
            httpx.Client(transport=httpx.MockTransport(respond)) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep") as sleep,
        ):
            paced = PacedClient(client, policy)
            self.assertEqual(paced.get("https://example.invalid").status_code, 200)
            sleep.assert_called_once_with(2.0)
            with self.assertRaises(RuntimeError):
                paced.get("https://example.invalid")

    def test_long_retry_after_is_not_truncated(self) -> None:
        policy = SourcePolicy(True, 2, 10, 10, 10, (0, 0), 10, 45)
        transport = httpx.MockTransport(
            lambda _: httpx.Response(429, headers={"Retry-After": "120"})
        )
        with (
            httpx.Client(transport=transport) as client,
            patch("anime_mapping_db.crawler_policy.time.sleep") as sleep,
        ):
            with self.assertRaises(httpx.HTTPStatusError):
                PacedClient(client, policy).get("https://example.invalid")
            sleep.assert_not_called()


class ReleaseReportTests(unittest.TestCase):
    def test_distinct_ids_per_source_and_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime.db"
            evidence = Path(directory) / "evidence.db"
            with sqlite3.connect(runtime) as db:
                db.executescript(
                    """
                    CREATE TABLE entities (id INTEGER);
                    INSERT INTO entities VALUES (1);
                    CREATE TABLE entity_nodes (entity_id INTEGER, node_id INTEGER);
                    INSERT INTO entity_nodes VALUES (1,1),(1,2);
                    """
                )
            with sqlite3.connect(evidence) as db:
                db.executescript(
                    """
                    CREATE TABLE datasets (id INTEGER, name TEXT);
                    INSERT INTO datasets VALUES (1,'fixture');
                    CREATE TABLE records (id INTEGER, dataset_id INTEGER);
                    INSERT INTO records VALUES (1,1),(2,1);
                    CREATE TABLE nodes (id INTEGER, provider TEXT);
                    INSERT INTO nodes VALUES (1,'mal'),(2,'anilist');
                    CREATE TABLE edge_evidence (record_id INTEGER,a_node INTEGER,b_node INTEGER);
                    INSERT INTO edge_evidence VALUES (1,1,2),(2,1,2);
                    """
                )
            manifest = {
                "release_tag": "v2",
                "providers": {"mal": 1, "anilist": 1},
                "counts": {
                    "datasets": 1,
                    "accepted_edges": 1,
                    "conflicts": 0,
                    "records": 2,
                    "evidence": 2,
                },
                "text_export": {"rows": 2},
                "assets": {},
                "sources": [
                    {
                        "name": "fixture",
                        "record_count": 2,
                        "sha256": "test",
                        "downloaded_at": "2026-11-28",
                    }
                ],
            }
            performance = {
                "environment": "test",
                "sampled_ids": 2,
                "rounds": 1,
                "median_ms": 1,
                "mean_ms": 1,
                "p95_ms": 1,
                "p99_ms": 1,
                "lookups_per_second": 1000,
            }
            report = build_report(
                manifest, runtime, evidence, {"providers": {"mal": 1}}, performance
            )
            self.assertEqual(report["sources"][0]["distinct_ids"], 2)
            self.assertEqual(
                report["sources"][0]["ids_by_namespace"], {"mal": 1, "anilist": 1}
            )
            self.assertEqual(report["group_size_distribution"], {2: 1})
            self.assertEqual(report["external_ids_delta"], 1)
            self.assertIn("| fixture | 2 | 2 |", render(report))
