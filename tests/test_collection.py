from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from anime_mapping_db.catalogue_report import catalogue_stats, shrink_reason
from anime_mapping_db.collection import assemble, collect_one, matrix, source_key
from anime_mapping_db.config import SOURCE_SPECS, MappingSourceSpec
from anime_mapping_db.database import MappingRecord
from anime_mapping_db.snapshots import _normalize_wikidata, load_snapshot


class CollectionTests(unittest.TestCase):
    def test_credential_preflight_does_not_contact_source(self) -> None:
        spec = MappingSourceSpec(
            "fixture",
            "https://example.invalid/catalog",
            "docchi",
            False,
            "test",
            supplemental=True,
            credential_env="TEST_SOURCE_KEY",
            permission_env="TEST_SOURCE_PERMISSION",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parts = root / "parts"
            part = parts / f"mapping-source-{source_key(spec)}"
            snapshots = root / "snapshots"
            with (
                patch.dict("os.environ", {"TEST_SOURCE_KEY": ""}),
                patch("anime_mapping_db.snapshots._download") as download,
            ):
                collect_one(part, spec)
                download.assert_not_called()
            assemble(snapshots, parts, (spec,))
            report = json.loads((snapshots / "collection-report.json").read_text())
            self.assertEqual(report["sources"][0]["status"], "missing_api_key")
            self.assertIsNone(report["sources"][0]["last_attempted_at"])
            with (
                patch.dict(
                    "os.environ",
                    {"TEST_SOURCE_KEY": "fixture", "TEST_SOURCE_PERMISSION": "0"},
                ),
                patch("anime_mapping_db.snapshots._download") as download,
            ):
                collect_one(part, spec)
                download.assert_not_called()
            assemble(snapshots, parts, (spec,))
            report = json.loads((snapshots / "collection-report.json").read_text())
            self.assertEqual(report["sources"][0]["status"], "permission_not_confirmed")
            self.assertTrue(matrix((spec,), snapshots)["include"][0]["due"])

    def test_interval_preserves_last_attempt_and_snapshot(self) -> None:
        spec = MappingSourceSpec(
            "fixture",
            "https://example.invalid/series",
            "docchi",
            False,
            "test",
            supplemental=True,
            collection_interval_hours=48,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshots = root / "snapshots"
            parts = root / "parts"
            part = parts / f"mapping-source-{source_key(spec)}"

            def download(_spec, target):
                target.write_text('[{"id":"one","mal":"101"}]', encoding="utf-8")

            with patch("anime_mapping_db.snapshots._download", side_effect=download):
                collect_one(part, spec)
            before = assemble(snapshots, parts, (spec,))
            report_path = snapshots / "collection-report.json"
            report = json.loads(report_path.read_text())
            report["sources"][0]["last_attempted_at"] = "2026-11-28T00:00:00+00:00"
            report_path.write_text(json.dumps(report))
            now = datetime(2026, 11, 29, tzinfo=timezone.utc)
            self.assertFalse(matrix((spec,), snapshots, now=now)["include"][0]["due"])
            self.assertTrue(
                matrix((spec,), snapshots, now=now, force=True)["include"][0]["due"]
            )
            import shutil

            shutil.rmtree(part)
            with patch("anime_mapping_db.snapshots._download") as download_mock:
                collect_one(part, spec, deferred=True)
                download_mock.assert_not_called()
            self.assertEqual(before, assemble(snapshots, parts, (spec,)))
            result = json.loads(report_path.read_text())["sources"][0]
            self.assertEqual(result["status"], "deferred")
            self.assertEqual(result["last_attempted_at"], "2026-11-28T00:00:00+00:00")
            now = datetime(2026, 11, 30, tzinfo=timezone.utc)
            self.assertTrue(matrix((spec,), snapshots, now=now)["include"][0]["due"])

    def test_catalogue_shrink_guard_retains_old_until_explicit_override(self) -> None:
        spec = MappingSourceSpec(
            "fixture native",
            "https://example.invalid/series",
            "docchi",
            False,
            "test",
            supplemental=True,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshots = root / "snapshots"
            parts = root / "parts"
            part = parts / f"mapping-source-{source_key(spec)}"

            def collect_rows(count, anchored):
                def download(_spec, target):
                    target.write_text(
                        json.dumps(
                            [
                                {"id": str(i), "mal": str(i) if i <= anchored else None}
                                for i in range(1, count + 1)
                            ]
                        ),
                        encoding="utf-8",
                    )
                    return "unused"

                if part.exists():
                    import shutil

                    shutil.rmtree(part)
                with patch(
                    "anime_mapping_db.snapshots._download", side_effect=download
                ):
                    collect_one(part, spec)

            collect_rows(100, 100)
            before = assemble(snapshots, parts, (spec,))
            collect_rows(100, 80)
            retained = assemble(snapshots, parts, (spec,))
            self.assertEqual(retained, before)
            report = json.loads((snapshots / "collection-report.json").read_text())
            outcome = report["sources"][0]
            self.assertEqual(outcome["status"], "retained")
            self.assertEqual(outcome["catalogue"]["with_external_id"], 100)
            self.assertEqual(outcome["attempted_catalogue"]["with_external_id"], 80)
            self.assertIn("with_external_id", outcome["retention_reason"])
            changed = assemble(
                snapshots, parts, (spec,), allow_shrink=frozenset({"docchi"})
            )
            self.assertNotEqual(
                changed["source_fingerprint"], before["source_fingerprint"]
            )
            collect_rows(70, 70)
            self.assertEqual(assemble(snapshots, parts, (spec,)), changed)
        self.assertIsNone(
            shrink_reason(
                {"native_ids": 100, "with_external_id": 100},
                {"native_ids": 95, "with_external_id": 95},
            )
        )
        self.assertIsNone(shrink_reason(None, {}))

    def test_native_catalogue_counts_distinct_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.json"
            path.write_text(
                json.dumps(
                    [
                        {"id": "1", "mal": "10"},
                        {"id": "1", "anilist": "20"},
                        {"id": "2", "mal": None},
                        {"id": "3", "shikimori": "30"},
                    ]
                ),
                encoding="utf-8",
            )
            result = catalogue_stats("animelib", path)
            self.assertEqual(
                result,
                {
                    "rows": 4,
                    "native_ids": 3,
                    "with_external_id": 2,
                    "without_external_id": 1,
                    "with_anchor_by_namespace": {
                        "mal": 1,
                        "anilist": 1,
                        "shikimori": 1,
                    },
                },
            )
            self.assertIsNone(catalogue_stats("base", path))
            self.assertIsNone(catalogue_stats("animelib", None))

    def test_collection_modes(self) -> None:
        modes = {spec.importer: spec.collection_mode for spec in SOURCE_SPECS}
        self.assertEqual(modes["docchi"], "single")
        self.assertEqual(modes["aniliberty"], "paginated")
        self.assertEqual(modes["anime365"], "paginated")
        self.assertEqual(modes["animelib"], "paginated")
        self.assertEqual(
            {key for key, mode in modes.items() if mode == "paginated"},
            {"aniliberty", "anime365", "animelib"}
            | ({"yummyani"} if "yummyani" in modes else set())
            | ({"annict_api"} if "annict_api" in modes else set())
            | ({"tioanime"} if modes.get("tioanime") == "paginated" else set())
            | {spec.importer for spec in SOURCE_SPECS if spec.export_api},
        )
        entries = matrix(SOURCE_SPECS)["include"]
        self.assertEqual(
            {item["key"]: item["mode"] for item in entries},
            {source_key(spec): spec.collection_mode for spec in SOURCE_SPECS},
        )

    def test_matrix_merge_retains_previous_data(self) -> None:
        specs = (
            MappingSourceSpec(
                "one", "https://example.invalid/one.json", "base", True, "test"
            ),
            MappingSourceSpec(
                "two", "https://example.invalid/two.json", "base", False, "test"
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parts = root / "parts"
            snapshots = root / "snapshots"

            def download(spec, target):
                target.write_text(json.dumps({"source": spec.name}), encoding="utf-8")
                return "unused"

            def importer(_path):
                yield MappingRecord("1", {"mal": ("1",), "anilist": ("2",)}, "test", 95)

            def collect_parts():
                for spec in specs:
                    collect_one(parts / f"mapping-source-{source_key(spec)}", spec)

            self.assertEqual(len(matrix(specs)["include"]), 2)
            with (
                patch("anime_mapping_db.importers.IMPORTERS", {"base": importer}),
                patch("anime_mapping_db.snapshots._download", side_effect=download),
            ):
                collect_parts()
                first = assemble(snapshots, parts, specs)
            # Fresh runner directories: one provider fails while the other succeeds.
            import shutil

            shutil.rmtree(parts)

            def partial(spec, target):
                if spec.name == "one":
                    raise RuntimeError("offline")
                return download(spec, target)

            with (
                patch("anime_mapping_db.importers.IMPORTERS", {"base": importer}),
                patch("anime_mapping_db.snapshots._download", side_effect=partial),
            ):
                collect_parts()
                second = assemble(snapshots, parts, specs)
            self.assertEqual(first, second)
            self.assertEqual(len(load_snapshot(snapshots, specs)), 2)
            report = json.loads((snapshots / "collection-report.json").read_text())
            self.assertEqual(
                [item["collection_mode"] for item in report["sources"]],
                ["single", "single"],
            )
            self.assertEqual(
                [item["status"] for item in report["sources"]],
                ["retained", "unchanged"],
            )
            with self.assertRaises(RuntimeError):
                assemble(root / "empty", parts, specs)

    def test_wikidata_projection_ignores_order_and_endpoint_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "data.json"
            a = {
                "item": {"value": "http://www.wikidata.org/entity/Q1"},
                "mal": {"value": "1"},
            }
            b = {
                "item": {"value": "http://www.wikidata.org/entity/Q2"},
                "mal": {"value": "2"},
            }
            path.write_text(
                json.dumps({"head": {"link": ["a"]}, "results": {"bindings": [a, b]}})
            )
            _normalize_wikidata(path, "wikidata_bahamut")
            first = path.read_bytes()
            path.write_text(
                json.dumps(
                    {"head": {"link": ["b"]}, "results": {"bindings": [b, a, a]}}
                )
            )
            _normalize_wikidata(path, "wikidata_bahamut")
            self.assertEqual(path.read_bytes(), first)
