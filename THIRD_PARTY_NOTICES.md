# Third-party data notices

Anime Mapping DB is compiled from independent public datasets. This file records the sources and licensing notes used by the builder; it is not a substitute for reading each upstream project's current license and terms.

For the project-wide distinction between Apache-2.0 source code and generated database artifacts, also see [`DATA_LICENSE.md`](DATA_LICENSE.md).

| Source | Role | Licensing / attribution note |
| --- | --- | --- |
| Fribb/anime-lists | Required direct | No explicit dataset license is declared by the builder; review the upstream repository before redistribution. |
| Kometa-Team/Anime-IDs | Required direct | Repository is MIT; generated data contains mappings derived from upstream projects and may carry additional obligations. |
| Anime-Lists/anime-lists | Required direct | No explicit dataset license is declared by the builder; review upstream terms before redistribution. |
| cplieger/animap | Required direct | Dataset is ODbL 1.0 + DbCL 1.0; project code is Apache-2.0. |
| cedya77/anime-offline-database | Optional direct | Compiled database is ODbL 1.0 + DbCL 1.0. This maintained fork replaces the old manami-project download in the builder while retaining the `manami` evidence lineage. |
| anibridge/anibridge-mappings | Optional direct | Repository is MIT; generated mappings may inherit obligations from upstream datasets. |
| Wikidata | Optional direct | Wikidata structured data is CC0 1.0. Used for Bahamut Animation Crazy identifiers. A small bundled CC0 bootstrap snapshot is kept for first-build WDQS outages. |
| rensetsu/db.notify.rensetsu-mirai | Optional direct | Repository is MIT. Builder consumes the public GitHub JSON dump, not Notify or another external API. |
| kawaiioverflow/arm | Optional direct | Package metadata declares MIT. Builder consumes `arm.json` from GitHub. |
| rensetsu/db.trakt.extended-anitrakt | Optional direct | Repository is MIT (archived but public). TV and movie JSON dumps are separate dataset inputs; season IDs are intentionally excluded. |
| rensetsu/db.rensetsu.public-dump / SilverYasha | Optional direct | Repository is CC0-1.0. Builder consumes the public SilverYasha JSON dump and does not scrape the site. |
| nattadasu/animeApi | Supplemental | Compiled database is ODbL 1.0 + DbCL 1.0; software code is MIT. Builder consumes only the GitHub-hosted `v3/database/animeapi.tsv`, never AnimeAPI's REST service. |

## AnimeAPI lineage policy

AnimeAPI aggregates several projects that Anime Mapping DB also consumes directly. It is therefore **not** counted as a normal independent evidence source for relationships already present in the base graph.

AnimeAPI rows are accepted only as supplemental namespace enrichment after two existing, conflict-free accepted anchors agree. Existing exact target IDs are not given a duplicate AnimeAPI vote. Season-only fields and AnimeAPI rows marked as potentially invalid for Trakt are excluded.

AnimeAPI's generator can also use live scrapers and an external Geckyzz API. Anime Mapping DB does **not** call those services. Hikka, Kaize, Nautiljon and Otak-Otaku identifiers may enter through AnimeAPI's already-published GitHub TSV, but this project does not scrape those sites itself.

The exact URLs and notes embedded into every evidence database are defined in `anime_mapping_db/config.py`.

When publishing or redistributing a compiled `mappings.db`, the TSV/JSONL release exports, or another derivative database, preserve applicable attribution, share-alike/database-license requirements and notices from upstream sources. If an upstream project's licensing changes, update this file and the source specification before publishing the next database release.
