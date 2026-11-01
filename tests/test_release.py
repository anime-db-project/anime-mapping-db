from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import zstandard as zstd

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.release import package_release, sha256_file


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
            self.assertTrue(manifest["source_fingerprint"])

            expected = {
                "mappings.db",
                "mappings.db.zst",
                "mappings-evidence.db.zst",
                "manifest.json",
                "SHA256SUMS",
            }
            self.assertEqual({path.name for path in output.iterdir()}, expected)
            parsed = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                parsed["assets"]["runtime"]["sha256"],
                sha256_file(output / "mappings.db"),
            )

            restored = root / "restored.db"
            decompressor = zstd.ZstdDecompressor()
            with (
                (output / "mappings.db.zst").open("rb") as src,
                restored.open("wb") as dst,
            ):
                decompressor.copy_stream(src, dst)
            self.assertEqual(sha256_file(restored), sha256_file(runtime))


if __name__ == "__main__":
    unittest.main()
