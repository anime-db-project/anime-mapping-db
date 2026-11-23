"""Ensure new Wikidata property filters and importer remain in sync."""

import unittest

from anime_mapping_db.config import _WIKIDATA_MULTI_QUERY
from anime_mapping_db.importers.wikidata import (
    _WIKIDATA_ENRICHMENT_PROVIDERS,
    _WIKIDATA_PROPERTY_FIELDS,
)


class WikidataStreamingPropertyTests(unittest.TestCase):
    def test_new_properties_only_enrich_trusted_records(self):
        properties = {
            "P1874": ("netflix", True),
            "P6466": ("hulu_movie", False),
            "P6467": ("hulu_series", False),
            "P7595": ("disneyplus_movie", False),
            "P7596": ("disneyplus_series", False),
            "P8055": ("amazon_prime_video_asin", False),
            "P14440": ("primevideo_title", False),
        }
        for code, entry in properties.items():
            with self.subTest(code=code):
                self.assertEqual(_WIKIDATA_PROPERTY_FIELDS[code], entry)
                self.assertIn("wdt:" + code, _WIKIDATA_MULTI_QUERY)
                self.assertIn(entry[0], _WIKIDATA_ENRICHMENT_PROVIDERS)
        self.assertNotIn("wdt:P4110", _WIKIDATA_MULTI_QUERY)

    def test_similar_storefront_ids_use_distinct_namespaces(self):
        namespaces = [
            _WIKIDATA_PROPERTY_FIELDS[code][0]
            for code in ("P8055", "P14440", "P7595", "P7596", "P6466", "P6467")
        ]
        self.assertEqual(len(namespaces), len(set(namespaces)))
        self.assertEqual(_WIKIDATA_PROPERTY_FIELDS["P11330"][0], "crunchyroll")
