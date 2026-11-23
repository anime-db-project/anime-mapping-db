# ID source research - 2026-11-24

## Baseline
The project already includes Wikidata/Bahamut and Wikidata multi-ID
among its 18 configured sources. An inspected runtime database contained
55 provider ID namespaces, including 2,427 Crunchyroll IDs and 7,279
Wikidata QIDs. They are ID node counts, not anime-work counts.

The active Wikidata import already recognizes P11330 as the modern
Crunchyroll series ID. P4110 is deprecated and is NOT imported into
the Crunchyroll namespace. Different seasons, movies, or series sharing
a storefront listing must never be unconditionally merged.

## Added Wikidata properties
These are expansions of one existing dataset, not independent sources.
Every candidate must pass the existing two-accepted-anchor safeguard,
and ambiguous target IDs are excluded.

| Wikidata | AMDB namespace | Scope |
|---|---|---|
| P1874 | netflix | Numeric Netflix title ID (existing namespace) |
| P6466 | hulu_movie | Hulu movie ID |
| P6467 | hulu_series | Hulu series ID |
| P7595 | disneyplus_movie | Disney+ movie ID |
| P7596 | disneyplus_series | Disney+ series ID |
| P8055 | amazon_prime_video_asin | Amazon video ASIN, e.g. B07J68L6MX |
| P14440 | primevideo_title | PrimeVideo.com 26-character title ID |

A one-time QLever check counted statements with a MAL anime ID on
the same Wikidata item: Netflix 849, Hulu movies 17, Hulu series 167,
Disney+ movies 6, Disney+ series 12, Amazon ASIN 30, Prime Video
title IDs 7. These are NOT new confirmed mappings. Many may already
exist or lack the two independent accepted anchors necessary for import.

Properties: https://www.wikidata.org/wiki/Property:P11330
https://www.wikidata.org/wiki/Property:P1874
https://www.wikidata.org/wiki/Property:P6466
https://www.wikidata.org/wiki/Property:P6467
https://www.wikidata.org/wiki/Property:P7595
https://www.wikidata.org/wiki/Property:P7596
https://www.wikidata.org/wiki/Property:P8055
https://www.wikidata.org/wiki/Property:P14440

## Candidate datasets - not yet enabled
- anilifecommunity/media-index:
  https://github.com/anilifecommunity/media-index
  Daily AniList-to-TMDB/MAL/Kitsu/AniDB/Simkl id-map.json; README
  reports 20,925 anime. Derived from AniList and TMDB: evaluate
  accepted new routes and rights before any supplemental importer.
  Do not regard it as independent evidence for its source datasets.
- athanasso/anime-offline-database:
  https://github.com/athanasso/anime-offline-database
  Weekly ODbL-licensed compilation of 13 providers. Its README
  explicitly derives cross-references from Fribb/anime-lists, which
  is already an input. Do not count derived Fribb links twice.
  Compare incremental unambiguous coverage against existing cedya77
  and Fribb sources before enabling a nineteenth source.
- MALSync/MALSync:
  https://github.com/MALSync/MALSync
  A possible research lead for streaming ID coverage, but player and
  tracker URL rules may refer to a franchise or season differently.
  Do not create direct AMDB mapping edges from heuristic URL matches.

## Future source validation
Before adding a new dataset: count novel provider IDs, new independently
verified anchor pairs, conflict delta, identifier granularity, derivative
evidence lineage, and actual build/distribution size. Do not infer added
coverage from a raw CSV/JSON row count.
