# Third-party data notices

Anime Mapping DB is compiled from independent upstream datasets. This file records the source and licensing notes used by the builder; it is not a substitute for reading each upstream project's current license and terms.

| Source | Role | Licensing / attribution note |
| --- | --- | --- |
| Fribb/anime-lists | Required | No explicit repository dataset license is declared by the builder; source is downloaded at build time. Review the upstream repository before redistribution. |
| Kometa-Team/Anime-IDs | Required | Repository is MIT; generated data contains mappings derived from upstream projects and may carry additional obligations. |
| Anime-Lists/anime-lists | Required | No explicit repository dataset license is declared by the builder; review upstream terms before redistribution. |
| cplieger/animap | Required | Dataset is distributed under ODbL 1.0 with DbCL 1.0; project code is Apache-2.0. |
| manami-project/anime-offline-database | Optional | Dataset is distributed under ODbL 1.0 with DbCL 1.0. |
| anibridge/anibridge-mappings | Optional | Repository is MIT; generated mappings may inherit obligations from upstream datasets. |
| Wikidata | Optional | Wikidata structured data is CC0 1.0. The builder currently uses it for Bahamut Animation Crazy identifiers linked to MAL/AniList/AniDB. A small bundled CC0 bootstrap snapshot of the same query is retained for first-build availability during WDQS outages. |

The exact URLs and notes embedded into every evidence database are defined in `anime_mapping_db/config.py`.

When publishing or redistributing a compiled `mappings.db`, preserve applicable attribution, share-alike/database-license requirements and notices from upstream sources. If an upstream project's licensing changes, update this file and the source specification before publishing the next database release.
