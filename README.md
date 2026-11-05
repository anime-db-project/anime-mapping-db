> **AI-assisted project:** Developed with the assistance of AI.

<p align="center">
  <strong>English</strong> · <a href="docs/README.ru.md">Русский</a> · <a href="docs/README.ja.md">日本語</a> · <a href="docs/README.de.md">Deutsch</a> · <a href="docs/README.es.md">Español</a> · <a href="docs/README.fr.md">Français</a> · <a href="docs/README.it.md">Italiano</a>
</p>

# anime-mapping-db

[![CI](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml)
[![Releases](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Code license](https://img.shields.io/badge/Code-Apache%202.0-D22128.svg)](LICENSE)
[![Data license](https://img.shields.io/badge/Data-Upstream%20terms-555555.svg)](DATA_LICENSE.md)

A reproducible, provenance-aware database of cross-service anime title identifiers. It provides a stable project identity and compact SQLite lookups for other applications.

## Features

- Stable `amdb:<anchor_id>` identifiers across database rebuilds.
- Cross-provider mappings with evidence-aware confidence and conservative conflict handling.
- Direct-only, ambiguity-safe resolver instead of unrestricted graph traversal.
- Separate compact runtime database and detailed evidence database.
- Versioned GitHub Releases with compressed databases, text exports, manifests, and checksums.

## Identity and matching rules

Anime Mapping DB provides `amdb:<anchor_id>` as a project-owned, stable title identity, independent of MAL, AniList or any other external catalog. A consumer may store this ID across rebuilds. By contrast, the SQLite `entity_id` is a dense internal key scoped to one database build and must never be persisted as a public identity.

Concrete provider IDs are stored as `(provider, external_id)` nodes. A verified set of nodes may belong to one project entity, but the builder will not allow two distinct IDs from the same provider to be collapsed into the same entity. Ambiguous evidence or directional conflicts leave routes unresolved rather than guessing.

During rebuilds, existing anchors are retained for matching or enriched entities. Legitimate merges preserve a surviving anchor and record redirects; splits assign new anchors to newly separated components without recycling retired IDs. This is essential when companion databases refer to anime independently of a particular mapping release.

```text
(provider, external_id) ──accepted edge── (provider, external_id)
          \                         /
           \── stable amdb:<anchor_id> ──/
                   │
              anchor redirects
```

## Data sources

The builder combines 18 configured inputs, including direct mapping datasets and strictly validated supplemental catalogs. Supplemental records cannot establish new anime identities without independent anchor confirmation; exact inputs and their licensing are tracked in the release manifest.

- [Fribb/anime-lists](https://github.com/Fribb/anime-lists)
- [Kometa-Team/Anime-IDs](https://github.com/Kometa-Team/Anime-IDs)
- [Anime-Lists/anime-lists](https://github.com/Anime-Lists/anime-lists)
- [cplieger/animap](https://github.com/cplieger/animap)
- [cedya77/anime-offline-database](https://github.com/cedya77/anime-offline-database)
- [anibridge/anibridge-mappings](https://github.com/anibridge/anibridge-mappings)
- [Wikidata / Bahamut](https://www.wikidata.org/)
- [rensetsu/db.notify.rensetsu-mirai](https://github.com/rensetsu/db.notify.rensetsu-mirai)
- [kawaiioverflow/arm](https://github.com/kawaiioverflow/arm)
- [rensetsu/db.trakt.extended-anitrakt (TV and movies)](https://github.com/rensetsu/db.trakt.extended-anitrakt)
- [rensetsu/db.rensetsu.public-dump (AnimeThemes)](https://github.com/rensetsu/db.rensetsu.public-dump)
- [anime-and-manga/lists](https://github.com/anime-and-manga/lists)
- [shinkro/community-mapping](https://github.com/shinkro/community-mapping)
- [notseteve/AnimeAggregations](https://github.com/notseteve/AnimeAggregations)
- [Wikidata multi-ID](https://www.wikidata.org/)
- [nattadasu/animeApi](https://github.com/nattadasu/animeApi)
- [rensetsu/db.rensetsu.public-dump (SilverYasha)](https://github.com/rensetsu/db.rensetsu.public-dump)

An `amdb:<anchor_id>` is a durable title identifier; provider IDs are aliases backed by evidence, while internal `entity_id` values are build-local. Conflicting source-to-target matches are not silently selected. [Identity contract](docs/IDENTITY.md).

## Input pipeline and provenance

The builder imports public bulk datasets and creates evidence records before materializing a runtime mapping graph. Input records carry source identity and evidence-group lineage. Correlated mirrors do not automatically count as independent sources.

Direct inputs can establish evidence-backed edges; supplemental catalogs such as AnimeAPI, AnimeAggregations, AnimeThemes reference data and multi-ID Wikidata enrich already anchored entities only after validation against at least two existing non-conflicting anchors. This avoids treating an adaptation, TV season or whole franchise as the same title.

Source fetching, hashes and versions are recorded in the release manifest. The canonical input configuration lives in `anime_mapping_db/config.py`. No third-party runtime REST API is needed to resolve IDs; the distributed SQLite database is read locally.

```text
1. Collect public datasets
2. Group evidence by independent lineage
3. Score and validate direct ID relationships
4. Resolve conflicts and stable AMDB identities
5. Audit, compact and package release assets
```

## Database design

The compact runtime `mappings.db` stores the resolver's nodes, accepted/candidate edges, directional conflicts, stable entities, redirects and optional manual overrides. It is optimized for indexed direct lookups, not for exploring every possible transitive path.

The separate `mappings-evidence.db` records datasets, source observations, evidence groups and original relationships used to justify edges. Applications that only resolve identifiers can omit the evidence database. Both are built and checked before distribution.

```text
mappings.db
  metadata · nodes · edges · conflicts
  entities · entity_nodes · anchor_redirects
  mapping_overrides · mapping_override_history

mappings-evidence.db
  metadata · datasets · nodes · evidence_groups
  records · record_nodes · edge_evidence (view)
```

## Quick start

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Using the resolver

A lookup starts with a source namespace and an external ID. It returns only independently accepted, unambiguous direct targets. For example, the same number used by MAL and AniList has no relationship unless an evidence-backed mapping explicitly connects them.

Use the Python resolver in an application, or query `mappings.db` using SQLite. Canonical `amdb` identities are available through the entity/anchor tables; the resolver's direct provider lookup should not be replaced with unrestricted recursive joins.

```python
from anime_mapping_db.resolver import MappingResolver

resolver = MappingResolver("data/mappings/mappings.db")
ids = resolver.resolve({"mal": "1"})
print(ids)
```

```bash
python -m anime_mapping_db status
python -m anime_mapping_db build --force
python -m anime_mapping_db anchors
python -m anime_mapping_db package-release --tag v1.0.0 --output release
```

## Confidence and conflicts

Evidence-aware confidence combines the strongest source weight, distinct evidence groups and corroborating records. A strong enough single source or two independent evidence groups can establish an accepted edge. Lower-confidence relationships remain candidates and are not exposed as safe direct routes.

Conflicts are directional: `A → provider B` may be ambiguous while an independently safe reverse lookup remains valid. Manual overrides can accept or reject a specific mapping and are stored with audit history. An override should be reviewed carefully because downstream applications may reuse the same cross-ID edge.

```text
confidence = min(100,
    max_weight
    + 8 × (distinct_evidence_groups - 1)
    + 2 × min(5, evidence_count - distinct_evidence_groups)
)

accepted: max_weight >= 80 OR distinct_evidence_groups >= 2
candidate: unconfirmed relationships
```

## Database and releases

Download `mappings.db.zst` and `manifest.json` from the latest Release for applications. `mappings-evidence.db.zst` holds detailed provenance; `mappings.tsv.zst` and `mappings.jsonl.zst` are portable exports. Scheduled releases are published when inputs change, with other builds available on code changes and manual dispatch.

- [Latest release](https://github.com/anime-db-project/anime-mapping-db/releases/latest)
- [Runtime database (zstd)](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db.zst)
- [Release manifest](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json)

```text
data/mappings/mappings.db
data/mappings/mappings-evidence.db
```

## Release assets and consumption

Each published release includes runtime and evidence databases, zstd-compressed assets, portable resolver-safe text routes, a machine-readable manifest and SHA-256 checksums. Text exports contain directed, ambiguity-filtered results rather than raw graph edges.

The release manifest is authoritative for schema versions, generated size, dataset versions, hashes, counts and fingerprint. These values change with each build, so static totals in README should not be interpreted as live coverage. Validate checksums before loading remote assets.

The release workflow supports repository changes, scheduled source checks, version tags and manual runs. Scheduled publishing can skip a release when input fingerprints are unchanged. GitHub already provides source-code archives, so the project does not ship redundant copies.

| File | Purpose |
| --- | --- |
| `mappings.db` | Compact, directly queryable runtime SQLite |
| `mappings.db.zst` | Compressed runtime database for applications |
| `mappings-evidence.db.zst` | Compressed evidence and provenance SQLite |
| `mappings.tsv.zst` | Portable filtered directed TSV routes |
| `mappings.jsonl.zst` | Portable filtered directed JSON Lines routes |
| `manifest.json` | Schema, sources, coverage, checksums and fingerprints |
| `SHA256SUMS` | SHA-256 integrity hashes |

```text
source_provider
source_id
target_provider
target_id
confidence
evidence_count
evidence_group_count
max_weight
origin
```

`source_provider` — Source provider; `source_id` — Source ID; `target_provider` — Target provider; `target_id` — Target ID; `confidence` — Confidence; `evidence_count` — Evidence record count; `evidence_group_count` — Independent evidence groups; `max_weight` — Strongest source weight; `origin` — Route provenance

## Validation and development

CI checks tests, formatting, database integrity, anchors and redirects, source confidence, conflict behavior, portable lookups and release packages. A successful build must produce non-empty accepted mappings without violating data and identity rules. Contributors should adjust importers and tests together.

```bash
python -m pip install -e .
python -m pip install pytest ruff
python -m pytest -q
python -m ruff check .
```

[Identity contract](docs/IDENTITY.md)

## Documentation

- [Identity and matching](docs/IDENTITY.md)
- [Data licensing](DATA_LICENSE.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## License and attribution

Code: Apache-2.0. Compiled databases contain third-party data with separate terms, including ODbL/DbCL and attribution obligations. Consult both license documents before redistribution. [Apache-2.0](LICENSE) · [DATA_LICENSE.md](DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
