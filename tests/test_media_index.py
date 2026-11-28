from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.importers import SUPPLEMENTAL_IMPORTERS


class MediaIndexTests(unittest.TestCase):
    def test_enrichment_rejects_ambiguity_and_weak_matches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = MappingSourceSpec(
                "base", "https://example.invalid/base", "test", True, "test"
            )
            source = root / "media-index.json"
            source.write_text(
                json.dumps(
                    {
                        "1": {
                            "mal": 101,
                            "bangumi": 301,
                            "bangumi_confidence": "STRONG",
                            "tmdb": 999,
                            "tvdb": 999,
                            "kitsu": 501,
                        },
                        "2": {
                            "mal": 102,
                            "bangumi": 302,
                            "bangumi_confidence": "STRONG",
                        },
                        "3": {
                            "mal": 103,
                            "bangumi": 302,
                            "bangumi_confidence": "STRONG",
                        },
                        "4": {
                            "mal": 104,
                            "bangumi": 304,
                            "bangumi_confidence": "WEAK",
                        },
                        "5": {
                            "mal": 105,
                            "anidb": 206,
                            "bangumi": 305,
                            "bangumi_confidence": "STRONG",
                        },
                        "6": {
                            "mal": 106,
                            "bangumi": 306,
                            "bangumi_confidence": "STRONG",
                        },
                        "7": {
                            "bangumi": 307,
                            "bangumi_confidence": "STRONG",
                        },
                        "999": {
                            "mal": 999,
                            "bangumi": 399,
                            "bangumi_confidence": "STRONG",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with MappingDatabaseBuilder(
                root / "runtime.db", evidence_path=root / "evidence.db"
            ) as builder:
                records = [
                    MappingRecord(
                        str(index),
                        {
                            "anilist": (str(index),),
                            "mal": (str(100 + index),),
                            "anidb": (str(200 + index),),
                            **({"bangumi": ("800",)} if index == 6 else {}),
                        },
                        "trusted",
                        95,
                    )
                    for index in range(1, 8)
                ]
                builder.ingest_dataset(
                    spec, records, sha256="base", downloaded_at="2026-11-28"
                )
                builder.finalize(built_at="2026-11-28")
                imported = list(
                    SUPPLEMENTAL_IMPORTERS["media_index"](source, builder.conn)
                )
                targets = {
                    (provider, ids[0])
                    for record in imported
                    for provider, ids in record.ids.items()
                    if provider in {"bangumi", "kitsu", "simkl", "tmdb_tv", "tvdb"}
                }
                self.assertEqual(targets, {("bangumi", "301"), ("kitsu", "501")})
                self.assertEqual(len(imported), 4)
                self.assertTrue(
                    all(
                        record.evidence_group == "media-index-anchor"
                        for record in imported
                    )
                )
