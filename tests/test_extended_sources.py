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
    import_animeaggregations_enrichment,
    import_anime_and_manga_lists,
    import_animethemes,
    import_animethemes_enrichment,
    import_anitrakt_movie,
    import_anitrakt_tv,
    import_arm,
    import_notify_rensetsu,
    import_silveryasha,
    import_shinkro,
    import_wikidata_enrichment,
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

    def test_new_direct_bulk_source_importers(self) -> None:
        themes = self.root / "themes.json"
        themes.write_text(
            json.dumps(
                [
                    {
                        "uuid": "theme-1",
                        "mappings": {
                            "anidb": 23,
                            "anilist": 1,
                            "animenewsnetwork": 13,
                            "animeplanet": "cowboy-bebop",
                            "animethemes": {"id": 3489, "slug": "cowboy_bebop"},
                            "kitsu": {"id": 1},
                            "myanimelist": 1,
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )
        theme_record = next(import_animethemes(themes))
        self.assertEqual(theme_record.ids["animethemes"], ("3489",))
        self.assertEqual(theme_record.ids["ann"], ("13",))
        self.assertEqual(theme_record.evidence_group, "animethemes")

        lists = self.root / "lists.json"
        lists.write_text(
            json.dumps([{"idAL": 1, "idAniDB": 23, "idMal": 1}]),
            encoding="utf-8",
        )
        list_record = next(import_anime_and_manga_lists(lists))
        self.assertEqual(
            list_record.ids,
            {"anilist": ("1",), "anidb": ("23",), "mal": ("1",)},
        )
        self.assertLess(list_record.weight, 80)

        shinkro = self.root / "shinkro.json"
        shinkro.write_text(
            json.dumps(
                [
                    {
                        "malid": 1,
                        "anidbid": 23,
                        "tvdbid": 76885,
                        "tmdbid": 0,
                        "tvdbseason": 1,
                        "animeMapping": [{"tvdbseason": 2, "start": 13}],
                    },
                    {"malid": 5, "anidbid": 219, "tvdbid": 0, "tmdbid": 11299},
                ]
            ),
            encoding="utf-8",
        )
        shinkro_records = list(import_shinkro(shinkro))
        self.assertEqual(len(shinkro_records), 2)
        self.assertTrue(all(record.weight < 80 for record in shinkro_records))
        self.assertEqual(shinkro_records[0].ids, {"mal": ("1",), "tvdb": ("76885",)})
        self.assertEqual(
            shinkro_records[1].ids,
            {"mal": ("5",), "tmdb_movie": ("11299",)},
        )
        self.assertFalse(
            any(
                provider == "anidb" or "season" in provider
                for record in shinkro_records
                for provider in record.ids
            )
        )

    def _trusted_runtime_builder(self) -> MappingDatabaseBuilder:
        runtime = self.root / "runtime.db"
        evidence = self.root / "evidence.db"
        spec = MappingSourceSpec(
            "base", "https://example.invalid/base", "test", True, "test"
        )
        builder = MappingDatabaseBuilder(runtime, evidence_path=evidence)
        builder.ingest_dataset(
            spec,
            [
                MappingRecord(
                    "trusted",
                    {
                        "mal": ("1",),
                        "anilist": ("2",),
                        "anidb": ("23",),
                        "ann": ("13",),
                    },
                    "trusted",
                    95,
                ),
                MappingRecord(
                    "known-cr",
                    {"mal": ("99",), "crunchyroll": ("KNOWN",)},
                    "trusted",
                    95,
                ),
            ],
            sha256="base",
            downloaded_at="2026-11-01T00:00:00+00:00",
        )
        builder.finalize(built_at="2026-11-01T00:00:00+00:00")
        return builder

    def test_animethemes_production_mode_adds_only_the_new_namespace(self) -> None:
        source = self.root / "themes-enrichment.json"
        source.write_text(
            json.dumps(
                [
                    {
                        "uuid": "theme-1",
                        "mappings": {
                            "anidb": 23,
                            "anilist": 2,
                            "animeplanet": "alternate-slug-must-not-be-added",
                            "animethemes": {"id": 521},
                            "myanimelist": 1,
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )
        with self._trusted_runtime_builder() as builder:
            records = list(import_animethemes_enrichment(source, builder.conn))
        self.assertEqual(len(records), 2)
        self.assertTrue(
            all(record.evidence_group == "animethemes-anchor" for record in records)
        )
        self.assertTrue(all("animethemes" in record.ids for record in records))
        self.assertFalse(any("animeplanet" in record.ids for record in records))

    def test_animeaggregations_is_anchor_only_and_excludes_non_identity_resources(
        self,
    ) -> None:
        source = self.root / "animeaggregations.json"
        source.write_text(
            json.dumps(
                {
                    "animes": {
                        "23": {
                            "resources": {
                                "MAL": ["1"],
                                "ANN": ["13"],
                                "CRUNCHY_ROLL": ["GTEST"],
                                "BANGUMI": ["123"],
                                "TMDB": ["tv/30991"],
                                "VNDB": ["v1"],
                                "WEBSITE": ["https://example.test"],
                            }
                        },
                        "999": {
                            "resources": {
                                "MAL": ["777"],
                                "CRUNCHY_ROLL": ["MUST-NOT-APPEAR"],
                            }
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        with self._trusted_runtime_builder() as builder:
            records = list(import_animeaggregations_enrichment(source, builder.conn))
        providers = {provider for record in records for provider in record.ids}
        values = {
            value
            for record in records
            for vals in record.ids.values()
            for value in vals
        }
        self.assertIn("crunchyroll", providers)
        self.assertIn("bangumi", providers)
        self.assertNotIn("tmdb_tv", providers)
        self.assertNotIn("vndb", providers)
        self.assertNotIn("website", providers)
        self.assertNotIn("MUST-NOT-APPEAR", values)
        self.assertTrue(
            all(
                record.evidence_group == "animeaggregations-anchor"
                for record in records
            )
        )

    def test_wikidata_multi_requires_two_anchors_and_skips_ambiguous_targets(
        self,
    ) -> None:
        source = self.root / "wikidata.json"
        bindings = []

        def row(item: str, prop: str, value: str) -> dict[str, object]:
            return {
                "item": {
                    "type": "uri",
                    "value": f"http://www.wikidata.org/entity/{item}",
                },
                "prop": {
                    "type": "uri",
                    "value": f"http://www.wikidata.org/prop/direct/{prop}",
                },
                "id": {"type": "literal", "value": value},
            }

        bindings.extend(
            [
                row("Q1", "P4086", "1"),
                row("Q1", "P8729", "2"),
                row("Q1", "P5732", "100"),
                row("Q1", "P11330", "GNEW"),
                # Two values for one provider are ambiguous and must not be emitted.
                row("Q1", "P11176", "ch1"),
                row("Q1", "P11176", "ch2"),
                # This Q-item has only one known base anchor and must be ignored.
                row("Q2", "P4086", "1"),
                row("Q2", "P5732", "200"),
            ]
        )
        source.write_text(
            json.dumps({"results": {"bindings": bindings}}), encoding="utf-8"
        )
        with self._trusted_runtime_builder() as builder:
            records = list(import_wikidata_enrichment(source, builder.conn))
        providers = {provider for record in records for provider in record.ids}
        values = {
            value
            for record in records
            for vals in record.ids.values()
            for value in vals
        }
        self.assertIn("wikidata", providers)
        self.assertIn("bangumi", providers)
        self.assertIn("crunchyroll", providers)
        self.assertNotIn("niconico", providers)
        self.assertNotIn("200", values)
        self.assertTrue(
            all(record.evidence_group == "wikidata-anchor" for record in records)
        )

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
