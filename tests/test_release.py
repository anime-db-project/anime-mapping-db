from __future__ import annotations

import csv
import io
import json
import sqlite3
import tempfile
from contextlib import closing
import unittest
from pathlib import Path

import zstandard as zstd

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.release import (
    TEXT_EXPORT_FIELDS,
    TEXT_EXPORT_SCHEMA_VERSION,
    package_release,
    sha256_file,
)
from anime_mapping_db.resolver import set_mapping_override


def _read_zstd_text(path: Path) -> str:
    with path.open("rb") as src:
        with zstd.ZstdDecompressor().stream_reader(src) as reader:
            return io.TextIOWrapper(reader, encoding="utf-8").read()


class ReleasePackagingTests(unittest.TestCase):
    def test_release_assets_and_manifest_are_reproducibly_described(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = root / "mappings.db"
            evidence = root / "mappings-evidence.db"
            with MappingDatabaseBuilder(runtime, evidence_path=evidence) as builder:
                builder.ingest_dataset(
                    MappingSourceSpec(
                        "fixture",
                        "https://example.invalid/data.json",
                        "test",
                        True,
                        "fixture license",
                    ),
                    [
                        MappingRecord(
                            "1",
                            {"mal": ("1",), "anidb": ("2",)},
                            "fixture",
                            95,
                        )
                    ],
                    sha256="source-sha",
                    downloaded_at="2026-11-01T00:00:00+00:00",
                )
                builder.finalize(built_at="2026-11-01T00:00:00+00:00")

            output = root / "release"
            manifest = package_release(
                runtime,
                evidence,
                output,
                release_tag="v2026.11.01-test",
            )
            self.assertEqual(manifest["release_tag"], "v2026.11.01-test")
            self.assertEqual(manifest["schema_version"], 3)
            self.assertEqual(manifest["sources"][0]["sha256"], "source-sha")
            self.assertEqual(manifest["providers"], {"anidb": 1, "mal": 1})
            self.assertTrue(manifest["source_fingerprint"])
            self.assertEqual(
                manifest["text_export"],
                {
                    "schema_version": TEXT_EXPORT_SCHEMA_VERSION,
                    "semantics": "directed single-seed resolver routes",
                    "fields": list(TEXT_EXPORT_FIELDS),
                    "rows": 2,
                },
            )

            expected = {
                "mappings.db",
                "mappings.db.zst",
                "mappings-evidence.db.zst",
                "mappings.tsv.zst",
                "mappings.jsonl.zst",
                "manifest.json",
                "SHA256SUMS",
            }
            self.assertEqual({path.name for path in output.iterdir()}, expected)
            parsed = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                parsed["assets"]["runtime"]["sha256"],
                sha256_file(output / "mappings.db"),
            )
            for key, name in (
                ("runtime_tsv_zstd", "mappings.tsv.zst"),
                ("runtime_jsonl_zstd", "mappings.jsonl.zst"),
            ):
                self.assertEqual(parsed["assets"][key]["name"], name)
                self.assertEqual(parsed["assets"][key]["rows"], 2)
                self.assertEqual(
                    parsed["assets"][key]["schema_version"],
                    TEXT_EXPORT_SCHEMA_VERSION,
                )
                self.assertEqual(
                    parsed["assets"][key]["sha256"],
                    sha256_file(output / name),
                )

            tsv_rows = list(
                csv.DictReader(
                    io.StringIO(_read_zstd_text(output / "mappings.tsv.zst")),
                    delimiter="\t",
                )
            )
            self.assertEqual(
                tsv_rows,
                [
                    {
                        "source_provider": "anidb",
                        "source_id": "2",
                        "target_provider": "mal",
                        "target_id": "1",
                        "confidence": "95",
                        "evidence_count": "1",
                        "evidence_group_count": "1",
                        "max_weight": "95",
                        "origin": "evidence",
                    },
                    {
                        "source_provider": "mal",
                        "source_id": "1",
                        "target_provider": "anidb",
                        "target_id": "2",
                        "confidence": "95",
                        "evidence_count": "1",
                        "evidence_group_count": "1",
                        "max_weight": "95",
                        "origin": "evidence",
                    },
                ],
            )
            jsonl_rows = [
                json.loads(line)
                for line in _read_zstd_text(output / "mappings.jsonl.zst").splitlines()
            ]
            self.assertEqual(len(jsonl_rows), 2)
            self.assertEqual(jsonl_rows[0]["source_provider"], "anidb")
            self.assertEqual(jsonl_rows[0]["confidence"], 95)
            self.assertEqual(jsonl_rows[1]["target_id"], "2")

            sums = (output / "SHA256SUMS").read_text(encoding="utf-8")
            self.assertIn("mappings.tsv.zst", sums)
            self.assertIn("mappings.jsonl.zst", sums)

            restored = root / "restored.db"
            decompressor = zstd.ZstdDecompressor()
            with (
                (output / "mappings.db.zst").open("rb") as src,
                restored.open("wb") as dst,
            ):
                decompressor.copy_stream(src, dst)
            self.assertEqual(sha256_file(restored), sha256_file(output / "mappings.db"))
            self.assertNotEqual(sha256_file(restored), sha256_file(runtime))
            self.assertEqual(manifest["storage"]["profile"], "compact-v1")

            # The compact evidence asset keeps the old read contract while
            # storing pair evidence through normalized record memberships.
            restored_evidence = root / "restored-evidence.db"
            with (
                (output / "mappings-evidence.db.zst").open("rb") as src,
                restored_evidence.open("wb") as dst,
            ):
                zstd.ZstdDecompressor().copy_stream(src, dst)
            with closing(sqlite3.connect(restored_evidence)) as compact:
                self.assertEqual(
                    compact.execute(
                        "SELECT value FROM metadata WHERE key='storage_profile'"
                    ).fetchone()[0],
                    "compact-v1",
                )
                self.assertEqual(
                    compact.execute("SELECT COUNT(*) FROM edge_evidence").fetchone()[0],
                    1,
                )
                self.assertEqual(
                    compact.execute("SELECT COUNT(*) FROM record_nodes").fetchone()[0],
                    2,
                )

            # The next incremental build must be able to seed its strict staging
            # database from the compact evidence release without changing local
            # node allocation merely because edge_evidence is now a view.
            rebuilt_runtime = root / "rebuilt.db"
            rebuilt_evidence = root / "rebuilt-evidence.db"
            with MappingDatabaseBuilder(
                rebuilt_runtime, evidence_path=rebuilt_evidence
            ) as rebuilder:
                self.assertEqual(
                    rebuilder.copy_dataset_from(restored_evidence, "fixture"), 1
                )
                rebuilt_stats = rebuilder.finalize(built_at="2026-11-01T00:00:00+00:00")
            self.assertEqual(rebuilt_stats.records, 1)
            self.assertEqual(rebuilt_stats.evidence, 1)
            with (
                closing(sqlite3.connect(evidence)) as original,
                closing(sqlite3.connect(rebuilt_evidence)) as rebuilt,
            ):
                original_nodes = original.execute(
                    "SELECT id, provider, external_id FROM nodes ORDER BY id"
                ).fetchall()
                rebuilt_nodes = rebuilt.execute(
                    "SELECT id, provider, external_id FROM nodes ORDER BY id"
                ).fetchall()
                self.assertEqual(rebuilt_nodes, original_nodes)

    def test_text_exports_follow_directional_conflicts_and_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = root / "mappings.db"
            evidence = root / "mappings-evidence.db"
            with MappingDatabaseBuilder(runtime, evidence_path=evidence) as builder:
                builder.ingest_dataset(
                    MappingSourceSpec(
                        "fixture",
                        "https://example.invalid/data.json",
                        "test",
                        True,
                        "fixture license",
                    ),
                    [
                        MappingRecord(
                            "a",
                            {"mal": ("1",), "anidb": ("2",)},
                            "fixture-a",
                            95,
                        ),
                        MappingRecord(
                            "b",
                            {"mal": ("1",), "anidb": ("3",)},
                            "fixture-b",
                            95,
                        ),
                    ],
                    sha256="source-sha",
                    downloaded_at="2026-11-01T00:00:00+00:00",
                )
                builder.finalize(built_at="2026-11-01T00:00:00+00:00")

            # MAL -> AniDB is directionally ambiguous in evidence. A manual accept
            # chooses one target and should therefore appear as an override route.
            set_mapping_override(
                "mal",
                "1",
                "anidb",
                "2",
                action="accept",
                reason="fixture override",
                path=runtime,
            )
            set_mapping_override(
                "mal",
                "999",
                "anidb",
                "999",
                action="accept",
                reason="fixture override without evidence",
                path=runtime,
            )

            output = root / "release"
            manifest = package_release(
                runtime,
                evidence,
                output,
                release_tag="v2026.11.01-test",
            )
            rows = [
                json.loads(line)
                for line in _read_zstd_text(output / "mappings.jsonl.zst").splitlines()
            ]
            routes = {
                (
                    row["source_provider"],
                    row["source_id"],
                    row["target_provider"],
                    row["target_id"],
                ): row
                for row in rows
            }
            self.assertIn(("anidb", "2", "mal", "1"), routes)
            self.assertIn(("anidb", "3", "mal", "1"), routes)
            self.assertIn(("mal", "1", "anidb", "2"), routes)
            self.assertNotIn(("mal", "1", "anidb", "3"), routes)
            overridden = routes[("mal", "1", "anidb", "2")]
            self.assertEqual(overridden["origin"], "override")
            self.assertEqual(overridden["confidence"], 95)
            override_only = routes[("mal", "999", "anidb", "999")]
            self.assertEqual(override_only["origin"], "override")
            self.assertIsNone(override_only["confidence"])
            self.assertEqual(manifest["text_export"]["rows"], 4)


if __name__ == "__main__":
    unittest.main()
