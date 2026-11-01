from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from anime_mapping_db.config import MappingSourceSpec
from anime_mapping_db.database import MappingDatabaseBuilder, MappingRecord
from anime_mapping_db.importers import (
    import_animeapi_enrichment,
    import_anitrakt_movie,
    import_anitrakt_tv,
    import_arm,
    import_notify_rensetsu,
    import_silveryasha,
)


class ExtendedSourceImporterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_direct_github_source_importers(self) -> None:
        notify = self.root / "notify.json"
        notify.write_text(
            json.dumps(
                [
                    {
                        "uuid": "row-1",
                        "mappings": {
                            "anidb": 10,
                            "anilist": 20,
                            "kitsu": {"id": 30},
                            "myanimelist": 40,
                            "notify": "notify-x",
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )
        notify_record = next(import_notify_rensetsu(notify))
        self.assertEqual(notify_record.ids["notify"], ("notify-x",))
        self.assertEqual(notify_record.evidence_group, "notify-rensetsu")

        arm = self.root / "arm.json"
        arm.write_text(
            json.dumps(
                [
                    {
                        "mal_id": 40,
                        "anilist_id": 20,
                        "annict_id": 50,
                        "syobocal_tid": 60,
                    }
                ]
            ),
            encoding="utf-8",
        )
        arm_record = next(import_arm(arm))
        self.assertEqual(arm_record.ids["annict"], ("50",))
        self.assertEqual(arm_record.ids["shoboi"], ("60",))

        tv = self.root / "anitrakt-tv.json"
        tv.write_text(
            json.dumps(
                [
                    {
                        "myanimelist": {"id": 40},
                        "trakt": {
                            "id": 70,
                            "season": {"id": 999, "number": 1},
                        },
                        "externals": {
                            "tvdb": 80,
                            "tmdb": 90,
                            "imdb": "tt0000040",
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )
        tv_record = next(import_anitrakt_tv(tv))
        self.assertEqual(tv_record.ids["trakt"], ("70",))
        self.assertEqual(tv_record.ids["tvdb"], ("80",))
        self.assertEqual(tv_record.ids["tmdb_tv"], ("90",))
        self.assertFalse(any("season" in provider for provider in tv_record.ids))

        movie = self.root / "anitrakt-movie.json"
        movie.write_text(
            json.dumps(
                [
                    {
                        "myanimelist": {"id": 41},
                        "trakt": {"id": 71},
                        "externals": {
                            "tmdb": 91,
                            "imdb": "tt0000041",
                            "letterboxd": {
                                "uid": 101,
                                "slug": "movie-slug",
                                "lid": "AbCd",
                            },
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )
        movie_record = next(import_anitrakt_movie(movie))
        self.assertEqual(movie_record.ids["tmdb_movie"], ("91",))
        self.assertEqual(movie_record.ids["letterboxd_uid"], ("101",))
        self.assertEqual(movie_record.ids["letterboxd_slug"], ("movie-slug",))

        silver = self.root / "silveryasha.json"
        silver.write_text(
            json.dumps({"data": [{"id": 120, "mal_id": "40"}]}),
            encoding="utf-8",
        )
        silver_record = next(import_silveryasha(silver))
        self.assertEqual(silver_record.ids["silveryasha"], ("120",))

    def test_animeapi_requires_two_trusted_anchors_and_skips_unsafe_fields(
        self,
    ) -> None:
        runtime = self.root / "runtime.db"
        evidence = self.root / "evidence.db"
        spec = MappingSourceSpec(
            "base", "https://example.invalid/base", "test", True, "test"
        )
        with MappingDatabaseBuilder(runtime, evidence_path=evidence) as builder:
            builder.ingest_dataset(
                spec,
                [
                    MappingRecord(
                        "trusted",
                        {"mal": ("1",), "anilist": ("2",)},
                        "trusted",
                        95,
                    ),
                    MappingRecord(
                        "known-annict",
                        {"mal": ("99",), "annict": ("77",)},
                        "trusted",
                        95,
                    ),
                ],
                sha256="base",
                downloaded_at="2026-11-01T00:00:00+00:00",
            )
            builder.finalize(built_at="2026-11-01T00:00:00+00:00")

            tsv = self.root / "animeapi.tsv"
            fieldnames = [
                "title",
                "myanimelist",
                "anilist",
                "annict",
                "hikka",
                "shikimori",
                "trakt",
                "trakt_may_invalid",
                "themoviedb_season_id",
                "thetvdb_season_id",
                "trakt_season_id",
            ]
            with tsv.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerow(
                    {
                        "title": "trusted",
                        "myanimelist": "1",
                        "anilist": "2",
                        "annict": "77",
                        "hikka": "hikka-title",
                        "shikimori": "1",
                        "trakt": "1234",
                        "trakt_may_invalid": "true",
                        "themoviedb_season_id": "555",
                        "thetvdb_season_id": "666",
                        "trakt_season_id": "777",
                    }
                )
                writer.writerow(
                    {
                        "title": "one-anchor",
                        "myanimelist": "1",
                        "hikka": "must-not-appear",
                    }
                )

            records = list(import_animeapi_enrichment(tsv, builder.conn))

        emitted = {
            (
                next(
                    provider
                    for provider in record.ids
                    if provider not in {"mal", "anilist"}
                ),
                next(
                    value[0]
                    for provider, value in record.ids.items()
                    if provider not in {"mal", "anilist"}
                ),
            )
            for record in records
        }
        self.assertIn(("hikka", "hikka-title"), emitted)
        self.assertIn(("shikimori", "1"), emitted)
        self.assertNotIn(("annict", "77"), emitted)
        self.assertFalse(
            any("season" in provider for record in records for provider in record.ids)
        )
        self.assertFalse(any("trakt" in record.ids for record in records))
        self.assertFalse(
            any(
                "must-not-appear" in values
                for record in records
                for values in record.ids.values()
            )
        )


if __name__ == "__main__":
    unittest.main()
