# Project identity layer

Anime Mapping DB exposes two different identifiers for two different jobs.

## `entity_id`

`entity_id` is the compact SQLite primary key used only inside one concrete `mappings.db` build. It is intentionally dense and may be renumbered when the database is rebuilt. Consumers must not persist or exchange it outside that database file.

## `anchor_id`

`anchor_id` is the stable public project identifier for a normalized catalog entry. Its textual form is:

```text
amdb:<integer>
```

For example:

```text
amdb:18472
```

The numeric value is stored in `entities.anchor_id`; the `amdb:` prefix makes the namespace explicit when IDs are exchanged between applications or other anime-db-project databases.

An anchor is independent of MAL, AniList, AniDB, Kitsu or any other upstream provider. No external catalog is treated as the canonical provider.

## Runtime tables

```text
entities
  entity_id   build-local SQLite key
  anchor_id   stable external project ID

entity_nodes
  entity_id -> nodes.id

anchor_redirects
  old_anchor_id -> current anchor_id
```

`nodes` continues to own concrete `(provider, external_id)` identities. `entity_nodes` groups those nodes into conservative project entities without duplicating the provider IDs.

## Entity construction

Entities are built from accepted mapping evidence, but they are deliberately stricter than a raw transitive connected component:

- rejected manual overrides are excluded;
- accepted manual overrides are honored subject to entity-safety rules;
- directional mapping conflicts block the conflicting edge;
- stronger accepted edges are considered before weaker ones;
- one entity may contain at most one node from a given provider.

The last rule prevents a transitive chain from accidentally collapsing two MAL, AniList, AniDB, TVDB, or other catalog entries into one project title.

## Stability across rebuilds

Before replacing the current runtime database, the updater compares new entities with the existing `mappings.db` anchor registry.

- unchanged or enriched entities retain their previous `anchor_id`;
- a newly discovered entity receives a new monotonically allocated ID;
- when previously separate non-conflicting entities genuinely merge, the oldest/smallest surviving anchor remains canonical and the other old anchors become redirects;
- when a previous entity splits, the old anchor stays with the new component having the strongest node overlap, while the other components receive new anchors;
- retired anchor numbers are never reused for unrelated entities.

This means another database can safely persist `amdb:<id>` instead of copying dozens of provider IDs.

## Resolver API

```python
from anime_mapping_db import AnchorResolver

resolver = AnchorResolver("mappings.db")
identity = resolver.anchor_for({"mal": "5114"})
if identity:
    print(identity.reference)  # amdb:<id>

ids = resolver.ids_for("amdb:18472")
```

`AnchorIdentity.entity_id` is useful for joins inside the same SQLite file. `AnchorIdentity.anchor_id` / `.reference` is the value intended for durable cross-project references.
