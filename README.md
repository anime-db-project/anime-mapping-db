> **AI-assisted project:** This project was developed with the help of AI.

<p align="center">
  <strong>English</strong> · <a href="docs/README.ru.md">Русский</a> · <a href="docs/README.ja.md">日本語</a> · <a href="docs/README.de.md">Deutsch</a> · <a href="docs/README.es.md">Español</a> · <a href="docs/README.fr.md">Français</a> · <a href="docs/README.it.md">Italiano</a>
</p>

# Anime Mapping DB

[![CI](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/anime-db-project/anime-mapping-db)](https://github.com/anime-db-project/anime-mapping-db/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/Code-Apache%202.0-D22128.svg)](LICENSE)

**Anime Mapping DB** builds and publishes a compact SQLite database for resolving anime identifiers between many public databases and tracking services.

There is no mapping HTTP API in this project. Consumers download `mappings.db` (or `mappings.db.zst`) from GitHub Releases and resolve IDs locally with SQLite. `anime-db-project/anime-db-bot` is one consumer, but the database is intentionally standalone and reusable.

## Highlights

- **31 provider namespaces** in the current build, from MAL/AniList/AniDB to Annict, Shikimori, Hikka, Notify, Trakt and others.
- **13 dataset inputs** from public mapping projects and GitHub-hosted dumps.
- **Direct-only runtime resolution**: no unsafe transitive graph walking across season/grouping boundaries.
- **Evidence-aware confidence**: correlated datasets do not automatically become independent votes.
- **Directional conflicts**: ambiguous source → target-provider routes are suppressed without discarding safe reverse routes.
- **Separate provenance database**: runtime lookups use only `mappings.db`; build/audit evidence lives in `mappings-evidence.db`.
- **AnimeAPI enrichment without its REST API**: only the GitHub-hosted TSV is consumed, after strict anchor validation.
- **Reproducible releases**: manifest, source hashes, provider counts, compressed assets and SHA-256 checksums.
- **Sub-millisecond local lookup** in the current benchmark.

## Latest build snapshot

The figures below come from the feature build used to validate the AnimeAPI expansion on 2026-11-01. Every release also publishes the same machine-readable counts in `manifest.json`.

| Metric | Value |
| --- | ---: |
| Dataset inputs | 13 |
| Provider namespaces | 31 |
| Unique provider/ID nodes | 371,128 |
| Source records | 654,827 |
| Evidence edges | 2,169,089 |
| Runtime edges | 1,111,505 |
| Accepted runtime edges | 1,104,610 |
| Directional conflicts | 19,724 |
| `mappings.db` | 109,547,520 B (~104.5 MiB) |
| `mappings.db.zst` | 18,808,357 B (~17.9 MiB) |
| `mappings-evidence.db` | 126,738,432 B (~120.9 MiB) |
| `mappings-evidence.db.zst` | 31,557,064 B (~30.1 MiB) |

## Databases inside `mappings.db`

A provider namespace is the key used by the resolver. Some services intentionally have more than one namespace when their IDs have different semantics (for example TMDB TV vs movie, or Letterboxd UID vs slug).

| Namespace | Database / identifier | IDs in validated build |
| --- | --- | ---: |
| `anidb` | AniDB | 16,341 |
| `anilist` | AniList | 22,415 |
| `animecountdown` | AnimeCountdown | 14,711 |
| `animeplanet` | Anime-Planet | 25,126 |
| `anisearch` | aniSearch | 20,042 |
| `ann` | Anime News Network | 12,402 |
| `annict` | Annict | 13,353 |
| `bahamut` | Bahamut Animation Crazy | 783 |
| `hikka` | Hikka | 27,157 |
| `imdb` | IMDb | 7,162 |
| `kaize` | Kaize slug | 23,233 |
| `kaize_id` | Kaize numeric ID | 9,956 |
| `kitsu` | Kitsu | 21,692 |
| `letterboxd_lid` | Letterboxd LID | 1,269 |
| `letterboxd_slug` | Letterboxd slug | 1,269 |
| `letterboxd_uid` | Letterboxd UID | 1,269 |
| `livechart` | LiveChart.me | 12,367 |
| `mal` | MyAnimeList | 28,119 |
| `nautiljon` | Nautiljon slug | 8,979 |
| `nautiljon_id` | Nautiljon numeric ID | 9,002 |
| `notify` | Notify.moe | 16,861 |
| `otakotaku` | Otak Otaku | 3,131 |
| `shikimori` | Shikimori | 27,711 |
| `shoboi` | Shoboi / Syoboi Calendar | 6,525 |
| `silveryasha` | SilverYasha | 5,703 |
| `simkl` | SIMKL | 14,711 |
| `tmdb_movie` | TMDB movie | 3,304 |
| `tmdb_tv` | TMDB TV | 4,465 |
| `trakt` | Trakt title | 6,100 |
| `tvdb` | TVDB series | 4,854 |
| `tvdb_movie` | TVDB movie | 1,116 |

`manifest.json` contains a `providers` object with these counts for each published build, so consumers do not need to query SQLite just to inspect coverage.

## Upstream datasets

The current builder has 13 dataset inputs. All newly added AnimeAPI-related inputs are consumed as GitHub-hosted files; the pre-existing Wikidata/Bahamut integration remains the only SPARQL query source.

| Dataset input | Role | Access path | Evidence group / note |
| --- | --- | --- | --- |
| `Fribb/anime-lists` | Required direct source | GitHub raw JSON | `fribb` |
| `Kometa-Team/Anime-IDs` | Required direct source | GitHub raw JSON | correlated groups are preserved by importer |
| `Anime-Lists/anime-lists` | Required direct source | GitHub raw XML | `anime-lists` |
| `cplieger/animap` | Required direct source | GitHub Release JSON | `animap` |
| `cedya77/anime-offline-database` | Optional direct source | GitHub Release JSONL | `manami`; maintained fork replacing the old Manami URL |
| `anibridge/anibridge-mappings` | Optional direct source | GitHub Release JSON | `anibridge` |
| Wikidata / Bahamut | Optional direct source | WDQS + bundled CC0 bootstrap fallback | `wikidata-bahamut` |
| `rensetsu/db.notify.rensetsu-mirai` | Optional direct source | GitHub raw JSON | `notify-rensetsu` |
| `kawaiioverflow/arm` | Optional direct source | GitHub raw JSON | `arm` |
| `rensetsu/db.trakt.extended-anitrakt` TV | Optional direct source | GitHub raw JSON | `anitrakt` |
| `rensetsu/db.trakt.extended-anitrakt` Movies | Optional direct source | GitHub raw JSON | `anitrakt` |
| `rensetsu/db.rensetsu.public-dump` SilverYasha | Optional direct source | GitHub raw JSON | `silveryasha` |
| `nattadasu/animeApi` | Supplemental enrichment | GitHub raw `database/animeapi.tsv` | `animeapi-anchor` |

Exact URLs, importer names and license notes are defined in `anime_mapping_db/config.py` and copied into `mappings-evidence.db` plus every release manifest.

## How AnimeAPI is used

AnimeAPI is intentionally **not** treated as a normal independent vote. Its compiled database aggregates several projects that Anime Mapping DB also consumes directly, so counting AnimeAPI as another ordinary evidence group would artificially increase confidence.

The integration therefore runs in two phases:

```text
Direct GitHub/public datasets
        ↓
provisional accepted graph + conflicts
        ↓
AnimeAPI GitHub TSV
        ↓
anchor validation
        ↓
new/missing provider namespaces only
        ↓
final runtime graph
```

For an AnimeAPI row to add a new ID:

1. at least two already-known anime-native anchors must exist in the provisional graph;
2. those two anchors must already have an **accepted direct edge**;
3. neither direction may be blocked by a conflict;
4. AnimeAPI does not add evidence between those existing anchors;
5. if the exact target ID already exists in the base graph, AnimeAPI does not add a correlated duplicate vote for it;
6. `trakt_may_invalid=true` rows are ignored for Trakt;
7. `themoviedb_season_id`, `thetvdb_season_id`, `trakt_season`, `trakt_season_id` and other season-only fields are never imported into the title graph.

The builder downloads only:

```text
https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv
```

It does **not** call AnimeAPI's REST service. It also does not directly call AnimeAPI's external Geckyzz endpoint or run AnimeAPI's Hikka/Kaize/Nautiljon/Otak-Otaku/SilverYasha site scrapers. IDs originating from those sources may appear through the already-published AnimeAPI TSV, but our builder itself performs no such scraping.

To improve provenance, several databases AnimeAPI itself uses are consumed directly from their GitHub repositories: `cedya77/anime-offline-database`, `kawaiioverflow/arm`, Notify/Rensetsu, AniTrakt/Rensetsu and the CC0 SilverYasha public dump. `Fribb/anime-lists` was already a direct source before AnimeAPI support.

## Lookup example

The project intentionally performs a single direct hop. Example:

```python
from anime_mapping_db.resolver import MappingResolver

resolver = MappingResolver("data/mappings/mappings.db")
print(resolver.resolve({"mal": "1"}))
```

A validated build currently resolves MAL `1` to IDs including AniDB, AniList, Anime-Planet, aniSearch, ANN, Annict, Hikka, IMDb, Kaize, Kitsu, LiveChart, Notify, Otak Otaku, Shikimori, Shoboi, SilverYasha, SIMKL, TMDB TV, Trakt and TVDB.

Equivalent direct SQL:

```sql
SELECT target.provider, target.external_id
FROM nodes AS source
JOIN edges AS e ON e.a_node = source.id OR e.b_node = source.id
JOIN nodes AS target
  ON target.id = CASE
      WHEN e.a_node = source.id THEN e.b_node
      ELSE e.a_node
  END
LEFT JOIN conflicts AS c
  ON c.source_node = source.id
 AND c.target_provider = target.provider
WHERE source.provider = 'mal'
  AND source.external_id = '1'
  AND e.status = 'accepted'
  AND c.source_node IS NULL
ORDER BY target.provider;
```

## Lookup benchmark

A reproducible benchmark is included:

```bash
python scripts/benchmark_lookup.py \
  --db data/mappings/mappings.db \
  --samples 1200 \
  --rounds 3
```

Validation run on the same Linux host, 1,200 common IDs × 3 rounds (3,600 lookups):

| Database | Median | p95 |
| --- | ---: | ---: |
| Previous 7-source schema-v3 build | 0.418 ms | 0.749 ms |
| Expanded 13-dataset build | **0.403 ms** | **0.552 ms** |

A separate sample across the expanded database measured median **0.446 ms**, mean **0.437 ms**, p95 **0.551 ms**, p99 **0.604 ms**.

These are microbenchmarks, not a latency guarantee. They measure local SQLite resolution including opening a read-only resolver connection. Hardware, filesystem cache and OS will change the exact numbers. The important result is that the much larger provider set did not introduce an observable lookup regression in the validation run.

## Runtime and evidence databases

### `mappings.db`

The runtime file contains only what consumers need:

```text
metadata
nodes
edges
conflicts
mapping_overrides
mapping_override_history
```

Repeated `(provider, external_id)` strings are normalized into integer node IDs. Runtime edges are indexed for lookup from either side.

### `mappings-evidence.db`

The evidence database is for builds, audit and provenance:

```text
metadata
datasets
nodes
evidence_groups
records
edge_evidence
```

Conceptually:

```text
upstream dataset
  → source record
    → evidence group
      → mapping edge
```

Normal consumers do not need to open the evidence database.

## Confidence model

For each pair of nodes:

```text
confidence = min(
  100,
  max_weight
  + 8 × (distinct_evidence_groups - 1)
  + 2 × min(5, evidence_count - distinct_evidence_groups)
)
```

An edge is accepted when either:

```text
max_weight >= 80
```

or:

```text
distinct_evidence_groups >= 2
```

Lower-confidence edges remain `candidate` and are not returned by the normal resolver.

Several public datasets share upstream lineage. Importers deliberately assign correlated records to the same evidence group where appropriate, so copied data does not masquerade as independent confirmation.

## Directional conflicts

Mappings are not always 1:1. If one AniDB item points to two MAL entries, the route `AniDB → MAL` is ambiguous even when each reverse `MAL → AniDB` route is individually safe.

The `conflicts` table therefore stores unsafe `(source_node, target_provider)` routes. This preserves usable directions instead of deleting the entire relationship.

## Releases

Every release contains:

- `mappings.db`
- `mappings.db.zst`
- `mappings-evidence.db.zst`
- `manifest.json`
- `SHA256SUMS`

Latest stable asset URLs use GitHub Releases:

```text
https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json
https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db.zst
```

`manifest.json` includes schema version, build time, dataset counts, provider counts, source URLs/hashes, `source_fingerprint`, release asset sizes and SHA-256 hashes.

Release automation runs:

- after mapping-engine changes land on `main`;
- daily at 03:17 UTC to check upstream datasets;
- for explicit `v*` tags;
- manually through `workflow_dispatch`.

Scheduled runs skip publishing when the source fingerprint is unchanged. Mapping-engine pushes publish even when upstream files are unchanged because a builder change can alter the resulting graph.

## Build locally

Python 3.11+:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
```

Outputs:

```text
data/mappings/mappings.db
data/mappings/mappings-evidence.db
```

Status:

```bash
python -m anime_mapping_db status
```

Package release assets:

```bash
python -m anime_mapping_db package-release \
  --tag v2026.11.01-test \
  --output release
```

## Validation

CI and release builds verify:

- Python 3.11–3.14 unit tests;
- Windows and macOS portability smoke tests;
- Ruff correctness checks and formatting;
- coverage gate;
- SQLite `PRAGMA integrity_check`;
- runtime/evidence schema roles and versions;
- non-empty accepted graph;
- direct-only resolution and directional conflicts;
- correlated evidence behavior;
- AnimeAPI two-anchor enrichment and invalid/season-field exclusions;
- release compression and SHA-256 integrity.

## Relationship to anime-db-bot

```text
upstream datasets
       ↓
anime-mapping-db
       ↓ GitHub Release
mappings.db.zst + manifest.json
       ↓
anime-db-bot
       ↓
local direct SQLite lookups
```

The bot does not build mapping datasets and does not call a mapping web API.

## Licensing

Project **code** is licensed under Apache-2.0. The generated database combines third-party datasets with their own licenses and attribution/share-alike requirements. In particular, AnimeAPI and anime-offline-database compiled data are ODbL 1.0 + DbCL 1.0.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) before redistributing `mappings.db` or a derivative database.
