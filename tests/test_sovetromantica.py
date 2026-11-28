from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.importers.sovetromantica import (
    import_sovetromantica_enrichment,
    normalize_snapshot,
)


class SovetRomanticaTests(unittest.TestCase):
    def test_explicit_shikimori_only_and_ambiguity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "catalog.json"
            source.write_text(
                json.dumps(
                    [
                        {"idSR": 1, "idShikimori": 201},
                        {"idSR": 1, "idShikimori": 201},
                        {"idSR": 2, "idShikimori": 202},
                        {"idSR": 3, "idShikimori": 202},
                        {"idSR": 4, "idShikimori": 203},
                        {"idSR": 4, "idShikimori": 204},
                        {"idSR": 5, "idShikimori": 105},
                        {"idSR": 6, "idShikimori": 206},
                    ]
                ),
                encoding="utf-8",
            )
            normalize_snapshot(source)
            self.assertEqual(len(json.loads(source.read_text("utf-8"))), 7)
            spec = MappingSourceSpec(
                "base", "https://example.invalid/base", "test", True, "test"
            )
            with MappingDatabaseBuilder(
                root / "runtime.db", evidence_path=root / "evidence.db"
            ) as builder:
                records = [
                    MappingRecord(
                        str(index),
                        {
                            "mal": (str(100 + index),),
                            "shikimori": (str(200 + index),),
                            **({"sovetromantica": ("900",)} if index == 6 else {}),
                        },
                        "trusted",
                        95,
                    )
                    for index in range(1, 7)
                ]
                builder.ingest_dataset(
                    spec, records, sha256="base", downloaded_at="2026-11-28"
                )
                builder.finalize(built_at="2026-11-28")
                imported = list(import_sovetromantica_enrichment(source, builder.conn))
                self.assertEqual(len(imported), 1)
                self.assertEqual(
                    imported[0].ids, {"sovetromantica": ("1",), "shikimori": ("201",)}
                )
                self.assertEqual(
                    imported[0].evidence_group, "sovetromantica-api-historical"
                )

    def test_invalid_snapshot_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "catalog.json"
            source.write_text('[{"idSR": true, "idShikimori": 10}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                normalize_snapshot(source)
