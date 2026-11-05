> **KI-unterstütztes Projekt:** Dieses Projekt wurde mit Hilfe von KI entwickelt.

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <strong>Deutsch</strong> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# anime-mapping-db

[![CI](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml)
[![Releases](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Code license](https://img.shields.io/badge/Code-Apache%202.0-D22128.svg)](../LICENSE)
[![Data license](https://img.shields.io/badge/Data-Upstream%20terms-555555.svg)](../DATA_LICENSE.md)

Eine reproduzierbare Datenbank mit Herkunftsnachweisen für Anime-Titelkennungen verschiedener Dienste. Sie bietet stabile Projekt-IDs und kompakte SQLite-Abfragen.

## Funktionen

- Dauerhafte `amdb:<anchor_id>`-Kennungen über mehrere Builds hinweg.
- Quellenübergreifende Zuordnungen mit belegbarer Konfidenz und Konfliktbehandlung.
- Direkte, mehrdeutigkeitsfreie Auflösung statt unkontrollierter Graph-Traversierung.
- Getrennte kompakte Laufzeit- und ausführliche Evidenzdatenbanken.
- Versionierte Releases mit komprimierten DBs, Textexporten, Manifesten und Prüfsummen.

## Datenquellen

Der Builder kombiniert 18 Eingaben aus direkten Mapping-Datensätzen und streng geprüften ergänzenden Katalogen. Ergänzungen dürfen ohne unabhängige Bestätigung keine neue Titelidentität begründen. Quellen und Lizenzen stehen im Release-Manifest.

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

`amdb:<anchor_id>` ist die stabile Titelkennung. Externe IDs sind belegte Aliasse; die interne `entity_id` gilt nur für den jeweiligen Build. Mehrdeutige Zuordnungen werden nicht willkürlich ausgewählt. [Identity contract](../docs/IDENTITY.md).

## Schnellstart

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Datenbanken und Releases

Für Anwendungen stehen `mappings.db.zst` und `manifest.json` im neuesten Release bereit. `mappings-evidence.db.zst` enthält Herkunftsnachweise; `mappings.tsv.zst` und `mappings.jsonl.zst` sind portable Exporte. Geplante Releases erscheinen bei Änderungen der Datenquellen.

- [Latest release](https://github.com/anime-db-project/anime-mapping-db/releases/latest)
- [Runtime database (zstd)](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db.zst)
- [Release manifest](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json)

```text
data/mappings/mappings.db
data/mappings/mappings-evidence.db
```

## Dokumentation

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## Lizenz und Quellenangaben

Der Code ist Apache-2.0-lizenziert. Kompilierte Daten unterliegen Drittanbieterbedingungen, darunter ODbL/DbCL und Namensnennungspflichten. Vor der Weitergabe beide Lizenzdokumente lesen. [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
