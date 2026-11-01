# Anime Mapping DB

Anime Mapping DB is the standalone cross-database identifier mapping dataset used by `anime-db-project/anime-db-bot`.

It builds a compact SQLite runtime database from multiple upstream anime mapping datasets, keeps provenance/evidence in a separate SQLite database, validates conflicts, and publishes versioned release assets that can be consumed without running the builder.

The project intentionally exposes data files rather than an HTTP API. Consumers download `mappings.db` (or `mappings.db.zst`) and resolve IDs locally.

## What this repository owns

This repository is the single source of truth for:

- mapping source definitions and importers;
- evidence grouping and source weights;
- confidence calculation;
- accepted/candidate edge classification;
- directional conflict detection;
- schema migrations for the mapping database;
- reproducible builds of `mappings.db` and `mappings-evidence.db`;
- validation, checksums, manifests and GitHub Releases.

`anime-db-bot` only consumes the released runtime database. It no longer builds mappings from upstream sources.

## Release assets

Every published release contains stable asset names:

- `mappings.db` — uncompressed runtime SQLite database;
- `mappings.db.zst` — Zstandard-compressed runtime database;
- `mappings-evidence.db.zst` — compressed provenance/evidence database;
- `manifest.json` — schema version, counts, source hashes, release tag and asset hashes;
- `SHA256SUMS` — SHA-256 checksums for the published files.

The latest release can be consumed from:

```text
https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json
https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db
https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db.zst
https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings-evidence.db.zst
https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/SHA256SUMS
```

Consumers should read `manifest.json`, compare `source_fingerprint`, verify SHA-256, decompress to a temporary file, validate SQLite, and only then atomically replace their active database.

## Runtime schema

Schema version: `3`.

The runtime database is deliberately small and contains only what a resolver needs:

```text
metadata
nodes
edges
conflicts
mapping_overrides
mapping_override_history
```

`nodes` normalizes repeated `(provider, external_id)` strings to integer IDs.

```sql
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    UNIQUE(provider, external_id)
);
```

`edges` stores compact relationships between node IDs:

```sql
CREATE TABLE edges (
    a_node INTEGER NOT NULL,
    b_node INTEGER NOT NULL,
    confidence INTEGER NOT NULL,
    status TEXT NOT NULL,
    evidence_count INTEGER NOT NULL,
    evidence_group_count INTEGER NOT NULL,
    max_weight INTEGER NOT NULL,
    PRIMARY KEY (a_node, b_node)
) WITHOUT ROWID;
```

Indexes are optimized for direct lookup from either side of an edge.

## Basic SQL usage

Resolve all accepted direct mappings from a MAL ID:

```sql
SELECT target.provider, target.external_id
FROM nodes AS source
JOIN edges AS e
  ON e.a_node = source.id OR e.b_node = source.id
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
ORDER BY target.provider, target.external_id;
```

The project also includes a small Python resolver:

```python
from anime_mapping_db.resolver import MappingResolver

resolver = MappingResolver("data/mappings/mappings.db")
print(resolver.resolve({"mal": "1"}))
```

Resolution is intentionally direct/one-hop only. Cross-catalog mappings are not safely transitive: season splits and grouped TVDB/TMDB entries can otherwise turn a correct identity into a related but different title.

## Evidence database

`mappings-evidence.db` is not required for normal lookups. It exists to explain and rebuild the runtime result.

It contains:

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
  -> source record
    -> evidence group
      -> one or more mapping edges
```

Evidence answers questions such as:

- which upstream dataset produced an edge;
- which source record produced it;
- whether multiple records are actually independent evidence;
- why an edge reached its confidence score;
- why one route was classified as conflicting.

The runtime database and evidence database intentionally use the same normalized node IDs during a build, but runtime lookups never need to open the evidence database.

## Confidence and acceptance

For every pair of nodes, confidence is calculated from all evidence records:

```text
confidence = min(
  100,
  max_weight
  + 8 * (distinct_evidence_groups - 1)
  + 2 * min(5, evidence_count - distinct_evidence_groups)
)
```

An edge is accepted when either:

```text
max_weight >= 80
```

or at least two independent evidence groups corroborate it:

```text
distinct_evidence_groups >= 2
```

Otherwise it remains a `candidate` and is not returned by the normal resolver.

Evidence groups matter because several public datasets may derive the same relationship from a common upstream source. Two copies of the same upstream evidence must not be counted as two independent votes.

## Directional conflicts

A relationship can be valid in one direction and ambiguous in the other.

Example:

```text
AniDB 200 -> MAL 100
AniDB 200 -> MAL 101
```

`AniDB 200 -> MAL` is ambiguous and becomes a directional conflict. `MAL 100 -> AniDB 200` can still be unambiguous and usable.

The `conflicts` table records these unsafe source-node/target-provider routes. Consumers should suppress automatic results for a route present in this table.

## Current upstream sources

The builder currently ingests:

1. `Fribb/anime-lists`
2. `Kometa-Team/Anime-IDs`
3. `Anime-Lists/anime-lists`
4. `cplieger/animap`
5. `manami-project/anime-offline-database`
6. `anibridge/anibridge-mappings`
7. `Wikidata/Bahamut Animation Crazy`

Some sources are mandatory for a successful build; some are optional. Exact URLs, importers, required flags and attribution notes live in `anime_mapping_db/config.py` and are copied into the evidence database.

See `THIRD_PARTY_NOTICES.md` for licensing/attribution notes.

## Build locally

Python 3.11+ is supported.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
```

Default outputs:

```text
data/mappings/mappings.db
data/mappings/mappings-evidence.db
```

Inspect status:

```bash
python -m anime_mapping_db status
```

Create the same release layout used by GitHub Actions:

```bash
python -m anime_mapping_db package-release \
  --tag v2026.11.01-test \
  --output release
```

Environment overrides are available for local builds:

```text
MAPPINGS_DB_PATH
MAPPINGS_EVIDENCE_DB_PATH
MAPPINGS_UPDATE_MAX_AGE_HOURS
MAPPINGS_WIKIDATA_CHECK_INTERVAL_HOURS
MAPPINGS_REQUEST_TIMEOUT_SECONDS
MAPPINGS_KEEP_DOWNLOADS
MAPPINGS_KEEP_PREVIOUS
```

## Update behavior

The builder stores each source SHA-256 in the evidence database. A normal update checks only sources whose check interval has expired. If downloaded content has not changed, the runtime database is left untouched.

A rebuild is atomic:

```text
new runtime DB
new evidence DB
  -> validate
  -> preserve local builder overrides if present
  -> replace active files
```

GitHub release builds use a `source_fingerprint` derived from the sorted `(dataset name, SHA-256)` pairs. Scheduled CI can therefore skip publishing a new release when source content is unchanged even though build timestamps differ.

## Overrides

The schema contains directional manual override tables because some cross-catalog relationships require human correction.

`accept` replaces automatic candidates for one exact source -> target-provider route. `reject` removes one exact target ID. Override history is audit logged.

Published release databases are intended to represent the canonical dataset. A consumer may maintain local operational overrides and copy them into a newly downloaded runtime database before atomic replacement. `anime-db-bot` does this for its admin-managed overrides.

## Validation

Before publication the project verifies:

- SQLite `PRAGMA integrity_check` for runtime and evidence databases;
- matching schema versions;
- runtime/evidence database roles;
- non-empty accepted edge set;
- unit tests for confidence, conflicts, direct-only resolution, overrides and importers;
- release compression/decompression and hashes.

## CI and releases

`ci.yml` runs the fast unit suite on supported Python versions and a small portability smoke test. It intentionally avoids the much larger bot test matrix to keep organization Actions usage low.

`release.yml` performs the network-heavy source build. It can run manually, on release tags, and on a daily schedule. Scheduled runs publish only when the source fingerprint changes.

## Project relationship

```text
upstream mapping datasets
        |
        v
anime-db-project/anime-mapping-db
        |
        | GitHub Release: mappings.db.zst + manifest
        v
anime-db-project/anime-db-bot
        |
        v
local SQLite direct lookups
```

The bot does not call a mapping API and does not rebuild upstream datasets.

## License

Project code is licensed under the repository `LICENSE` file. The generated database combines information from multiple upstream datasets with their own licenses and attribution requirements. Redistribution of the compiled database does not erase those upstream obligations; review `THIRD_PARTY_NOTICES.md` before redistributing or creating derivative datasets.
