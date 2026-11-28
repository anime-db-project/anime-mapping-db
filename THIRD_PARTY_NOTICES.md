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
| Wikidata | Optional direct + supplemental | Wikidata structured data is CC0 1.0. QLever is the primary bulk SPARQL backend with WDQS fallback; both query the same Wikidata lineage. Bahamut retains a bundled CC0 bootstrap snapshot for first-build endpoint outages. |
| rensetsu/db.notify.rensetsu-mirai | Optional direct | Repository is MIT. Builder consumes the public GitHub JSON dump, not Notify or another external API. |
| kawaiioverflow/arm | Optional direct | Package metadata declares MIT. Builder consumes `arm.json` from GitHub. |
| rensetsu/db.trakt.extended-anitrakt | Optional direct | Repository is MIT (archived but public). TV and movie JSON dumps are separate dataset inputs; season IDs are intentionally excluded. |
| rensetsu/db.rensetsu.public-dump / SilverYasha | Optional direct | Repository is CC0-1.0. Builder consumes the public SilverYasha JSON dump and does not scrape the site. |
| rensetsu/db.rensetsu.public-dump / AnimeThemes | Supplemental | Repository is CC0-1.0. Builder consumes the converted AnimeThemes GitHub dump and does not call AnimeThemes APIs. |
| anime-and-manga/lists | Optional corroborating | Public GitHub mapping dump with no explicit dataset license in the repository; review upstream terms before redistribution. Its weight is below the single-source acceptance threshold. |
| shinkro/community-mapping | Optional corroborating | Repository is MIT. Only title-level MAL↔TVDB-series and MAL↔TMDB-movie mappings are imported; season/episode routing and generated AniDB fields are excluded. |
| notseteve/AnimeAggregations | Supplemental | Repository uses the Unlicense, but the aggregate contains external/upstream identifiers. It is used only after two trusted anchors agree, and generic/adaptation resources are excluded. |
| Wikidata multi-ID | Supplemental | Same CC0 Wikidata lineage as above. Adds only anchor-validated missing IDs/QIDs; QLever and WDQS are query backends, not separate evidence sources. |
| nattadasu/animeApi | Supplemental | Compiled database is ODbL 1.0 + DbCL 1.0; software code is MIT. Builder consumes only the GitHub-hosted `v3/database/animeapi.tsv`, never AnimeAPI's REST service. |
| anilifecommunity/media-index | Supplemental | MIT-0 covers code and original contributions, not the aggregated data. [Source policy](https://github.com/anilifecommunity/media-index/blob/main/docs/SOURCE-POLICY.md) explicitly distinguishes owner attestation from provider permission. Only missing factual identifiers are imported after strict validation; no descriptions, artwork or episode metadata. Upstream redistribution rights have not been independently confirmed. Set `MAPPINGS_ENABLE_MEDIA_INDEX=0` and force a rebuild to exclude this source. |
| AniLiberty catalog | Supplemental | [Public API v1](https://api.anilibria.app/api/docs/v1/). Only explicit release ID, MAL and Shikimori references are read; no video, descriptions or artwork. Upstream data terms apply; redistribution permission has not been independently confirmed. |
| notwindstone/MALToAnything / SovetRomantica | Supplemental | GPL-3.0 repository; [historical JSON snapshot](https://github.com/notwindstone/MALToAnything/blob/main/sovetromantica/sovetromantica-mapped.json) derived from explicit `anime_shikimori` API references according to the upstream README. Only numeric title IDs are imported; no name matching, no AniLibria portion, no API calls to SovetRomantica. Upstream redistribution terms remain applicable. Disable via `MAPPINGS_ENABLE_SOVETROMANTICA=0` and rebuild. |

| MALSync / Crunchyroll and Netflix | Supplemental | [GPL-3.0-only repository](https://github.com/MALSync/MALSync). Only explicitly authored `malId` season overrides without episode offsets or season overrides are considered. Native season identifiers remain separate from series IDs. No blocked backup, live service API, streaming URLs, source code or catalogue metadata are imported. Upstream data terms remain applicable; disable with `MAPPINGS_ENABLE_MALSYNC_CRUNCHYROLL=0` or `MAPPINGS_ENABLE_MALSYNC_NETFLIX=0` and rebuild. |

| Anime365 | Supplemental | [MALSync adapter](https://github.com/MALSync/MALSync/blob/master/src/pages/Anime365/main.ts); [catalogue API schema](https://github.com/ragedrugg/anime365/blob/main/openapi.yaml). Native `id` and `myAnimeListId` only. Public metadata endpoint, no playback or user data. Upstream data redistribution terms not independently verified. Disable via `MAPPINGS_ENABLE_ANIME365=0` and rebuild. |

## Supplemental lineage policy

AnimeAPI, media-index and AnimeAggregations contain data that can overlap with direct sources already used by Anime Mapping DB. Wikidata multi-ID is intentionally conservative because one Wikidata item can still represent a franchise/season concept differently from another catalogue. These sources therefore run only after the direct-source graph has been finalized once.

For third-party aggregates, a supplemental item must contain at least two exact base IDs that are already connected by an accepted direct edge with no directional conflict. Only then may missing targets be attached. Ambiguous multiple IDs for the same target provider are skipped. AnimeAPI also excludes season-only fields and rows marked potentially invalid for Trakt; AnimeAggregations excludes VNDB and generic website/social/adaptation relationships.

AnimeAPI's generator can also use live scrapers and an external Geckyzz API. Anime Mapping DB does **not** call those services. Hikka, Kaize, Nautiljon and Otak-Otaku identifiers may enter through AnimeAPI's already-published GitHub TSV, but this project does not scrape those sites itself.

AniLiberty is a provider-native catalog rather than a third-party aggregate. Its own numeric release ID may attach to an existing exact MAL or Shikimori ID explicitly asserted by the catalog. Both references, when known, must agree on a single existing component; duplicate release claims for a component and conflicting references are excluded. No new AMDB identities or inferred title matches are introduced. MAL and Shikimori are not counted as independent evidence lineages.

The SovetRomantica snapshot is a historical copy of explicit provider cross-references, not a second independent catalogue lineage. It may attach one missing SovetRomantica ID to an existing, non-singleton group via an exact known Shikimori ID. Conflicting or ambiguous claims are excluded, and equal numerical MAL IDs are not inferred. Live catalogue validity and upstream redistribution rights have not been independently confirmed.

MALSync's open-source season overrides are a deliberately narrow exception to the two-anchor aggregate rule. A declared MAL ID may attach a missing, separately scoped season identifier to a non-singleton existing component only when the source claims are one-to-one and no directional conflict exists. These are explicit tracking overrides, not independent verification of full episode equivalence. Offset and season-renumbering overrides are not imported. Upstream data redistribution rights have not been independently verified.

Anime365 uses the provider's own explicit `myAnimeListId` assertion, not title matching or MALSync API responses. A missing numeric series ID may attach only to a non-singleton existing group with an exact known MAL anchor. Duplicate, contradictory, or conflicting claims are excluded. No new AMDB identities are created.

The exact URLs and notes embedded into every evidence database are defined in `anime_mapping_db/config.py`.

When publishing or redistributing a compiled `mappings.db`, the TSV/JSONL release exports, or another derivative database, preserve applicable attribution, share-alike/database-license requirements and notices from upstream sources. If an upstream project's licensing changes, update this file and the source specification before publishing the next database release.
