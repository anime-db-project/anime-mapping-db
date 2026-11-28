from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from anime_mapping_db.malsync_registry import _anchor, inventory


class MALSyncRegistryTests(unittest.TestCase):
    def test_inventory_does_not_promote_fixture_to_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pages.md").write_text(
                "<h1>Anime</h1><table><tr><td>ADN</td><td>French</td>"
                "<td>:x:</td><td>:x:</td><td>:x:</td><td>:x:</td></tr>"
                "<tr><td>Example</td><td>English</td>"
                "<td>:x:</td><td>:x:</td><td>:heavy_check_mark:</td><td>:x:</td></tr>"
                "</table><h1>Manga</h1><table><tr><td>Ignored</td>"
                "<td>x</td><td>x</td><td>x</td><td>x</td><td>x</td></tr></table>",
                encoding="utf-8",
            )
            legacy = root / "src" / "pages"
            chibi = root / "src" / "pages-chibi"
            legacy.mkdir(parents=True)
            chibi.mkdir(parents=True)
            (legacy / "pages.ts").write_text(
                "import { Example } from './Example/main';", encoding="utf-8"
            )
            (chibi / "pages.ts").write_text(
                "import { ADN } from './implementations/ADN/main';", encoding="utf-8"
            )
            for folder, code in (
                (legacy / "Example", "name: 'Example', getIdentifier() {}, getMalUrl() {}"),
                (chibi / "implementations" / "ADN", "name: 'ADN', getIdentifier() {}"),
            ):
                folder.mkdir(parents=True)
                (folder / "main.ts").write_text(code, encoding="utf-8")
                (folder / "tests.json").write_text(
                    json.dumps(
                        {
                            "testCases": [
                                {
                                    "expected": {
                                        "identifier": "123",
                                        "malUrl": "https://myanimelist.net/anime/456",
                                    }
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
            report = inventory(root, "fixture")
            self.assertEqual(report["anime_integrations"], 2)
            self.assertFalse(report["fixture_candidates_are_release_evidence"])
            a, b = report["sources"]
            self.assertEqual(a["status"], "identifier_only_or_indirect")
            self.assertEqual(b["status"], "explicit_hook_requires_verification")
            self.assertEqual(
                b["implementations"][0]["fixture_candidates"],
                [{"id": "123", "anchor_provider": "mal", "anchor_id": "456"}],
            )

    def test_only_exact_catalogue_urls(self) -> None:
        self.assertEqual(_anchor("https://anilist.co/anime/123"), ("anilist", "123"))
        self.assertIsNone(_anchor("https://myanimelist.net/manga/123"))
        self.assertIsNone(_anchor("https://myanimelist.net.example/anime/123"))
        self.assertIsNone(_anchor("https://myanimelist.net/anime/abc"))
