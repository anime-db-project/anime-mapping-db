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

## Datenbank in Zahlen

**Rund 35.000 unterschiedliche Anime-Titel** mit **34.851 stabilen AMDB-Identitäten** im geprüften Snapshot. Diese Zahl beschreibt das gemeinsame Identitätsverzeichnis und keine vollständige Abdeckung durch jeden Anbieter.

| Kennzahl | Wert |
| --- | ---: |
| Stabile AMDB-Titelidentitäten | **34,851** (≈35k) |
| Provider-ID-Namensräume | **55** |
| Eingabedatensätze | **18** |
| Akzeptierte Zuordnungskanten | **1,225,741** |
| Sichere gerichtete Exportrouten | **2,386,529** |
| Gerichtete Konflikte | **22,021** |
| Importierte Quellrecords | **803,711** |
| Evidenzbeziehungen | **2,346,745** |

Stand: **5. November 2026**, Release [`v2026.11.05.24`](https://github.com/anime-db-project/anime-mapping-db/releases/tag/v2026.11.05.24). Die Zahlen sind ein Snapshot, kein Live-Zähler. Aktuelle Werte stehen in [`manifest.json`](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json). Die AMDB-Anzahl wurde mit dem entsprechenden Timestamp-DB-Build abgeglichen.

## Funktionen

- Dauerhafte `amdb:<anchor_id>`-Kennungen über mehrere Builds hinweg.
- Quellenübergreifende Zuordnungen mit belegbarer Konfidenz und Konfliktbehandlung.
- Direkte, mehrdeutigkeitsfreie Auflösung statt unkontrollierter Graph-Traversierung.
- Getrennte kompakte Laufzeit- und ausführliche Evidenzdatenbanken.
- Versionierte Releases mit komprimierten DBs, Textexporten, Manifesten und Prüfsummen.

## Identität und Zuordnungsregeln

Anime Mapping DB stellt mit `amdb:<anchor_id>` eine eigene, dauerhaft stabile Titelkennung unabhängig von MAL, AniList und weiteren Diensten bereit. Diese darf über Builds hinweg gespeichert werden. `entity_id` ist dagegen nur ein dichter interner SQLite-Schlüssel einer bestimmten Datenbankversion.

Externe Kennungen sind `(provider, external_id)`-Knoten. Bestätigte Knoten können eine Projekteinheit bilden, allerdings dürfen nicht zwei unterschiedliche IDs desselben Anbieters in einer Einheit landen. Mehrdeutige Zuordnungen werden nicht erraten.

Bei Neubauten bleiben Anker für unveränderte oder erweiterte Einheiten erhalten. Gültige Zusammenführungen behalten einen Anker und speichern Weiterleitungen; Aufspaltungen erhalten nötigenfalls neue Kennungen. Ehemalige IDs werden nicht für fremde Titel wiederverwendet.

```text
(provider, external_id) ──accepted edge── (provider, external_id)
          \                         /
           \── stable amdb:<anchor_id> ──/
                   │
              anchor redirects
```

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

## Eingaben und Herkunft

Der Builder lädt öffentliche Massendatensätze, speichert Quellbelege und erzeugt danach den Laufzeitgraphen. Datensätze erhalten Quellen- und Evidenzgruppen, sodass Spiegel und abgeleitete Daten nicht als unabhängige Bestätigung zählen.

Direkte Quellen können Kanten begründen. Ergänzende Kataloge wie AnimeAPI, AnimeAggregations, AnimeThemes-Kennungen und Wikidata-Multi-ID ergänzen nur nach Prüfung von mindestens zwei bereits bekannten, konfliktfreien Ankern. Das verhindert die Gleichsetzung von Titel, Staffel und Franchise.

Adressen, Hashes und Versionen stehen im Release-Manifest; `anime_mapping_db/config.py` enthält die Eingabekonfiguration. Für lokale SQLite-Auflösung ist keine externe REST-API nötig.

```text
1. Öffentliche Eingabedaten laden
2. Evidenz nach Herkunft gruppieren
3. Direkte Zuordnungen prüfen und bewerten
4. Konflikte und stabile AMDB-IDs bestimmen
5. Audit, Komprimierung und Paketierung
```

## Aufbau der Datenbanken

Die kompakte `mappings.db` enthält Knoten, akzeptierte und offene Kanten, gerichtete Konflikte, stabile Einheiten, Weiterleitungen und manuelle Übersteuerungen. Sie ist für direkte indexierte Abfragen ausgelegt.

Die getrennte `mappings-evidence.db` bewahrt Datensätze, Quellbeobachtungen, Evidenzgruppen und ursprüngliche Beziehungen. Reine ID-Resolver benötigen diese Datenbank nicht. Beide Dateien werden vor der Veröffentlichung geprüft.

```text
mappings.db
  metadata · nodes · edges · conflicts
  entities · entity_nodes · anchor_redirects
  mapping_overrides · mapping_override_history

mappings-evidence.db
  metadata · datasets · nodes · evidence_groups
  records · record_nodes · edge_evidence (view)
```

## Schnellstart

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Resolver verwenden

Ein Lookup erhält Namespace und externe ID und liefert nur eindeutige direkte Ziele. Gleiche numerische Kennungen bei MAL und AniList beweisen ohne belegte Kante keine Gleichheit.

Anwendungen können den Python-Resolver oder SQLite verwenden. Die stabilen AMDB-IDs liegen in Entity- und Anchor-Tabellen; vermeiden Sie unbeschränkte rekursive Verknüpfungen.

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

## Möglichkeiten der Datenbanknutzung

Die Release-Dateien können ohne eigenen Build oder API-Schlüssel für lokale ID-Abfragen verwendet werden. Wählen Sie je nach Anwendungsfall:

- **Python-Integration.** `MappingResolver` für Zuordnungen in Bots, Webseiten und Medienkatalogen.
- **Direktes SQLite.** SQLite-Treiber in Python, Rust, Go, Node.js und weiteren Sprachen ohne Netzwerk.
- **Datenimport und Analysen.** TSV/JSONL in Datenbanken, Suchindizes und ETL-Prozesse importieren.
- **Gemeinsame Titelreferenz.** `amdb:<anchor_id>` speichern und mit anderen Projekten verknüpfen.
- **Quellenprüfung.** Die Evidenzdatenbank zur Nachverfolgung fraglicher Zuordnungen verwenden.

Die veröffentlichte SQLite-Datei kann ohne Kompilierung heruntergeladen werden:

```bash
curl -fL -o mappings.db \
  https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db
```

Für `MappingResolver` zuerst das Python-Paket installieren (`python -m pip install -e .`):

```python
from anime_mapping_db.resolver import MappingResolver

resolver = MappingResolver("mappings.db")
if resolver.available():
    matches = resolver.resolve({"mal": "1"})
    print(matches)  # Verified, direct and conflict-safe provider IDs
```

Beispiel für die stabile AMDB-ID und zugehörige Provider-IDs mit Pythons `sqlite3`:

```python
import sqlite3

with sqlite3.connect("file:mappings.db?mode=ro", uri=True) as db:
    rows = db.execute("""
        SELECT entity.anchor_id, other.provider, other.external_id
        FROM nodes AS seed
        JOIN entity_nodes AS seed_member ON seed_member.node_id = seed.id
        JOIN entities AS entity ON entity.entity_id = seed_member.entity_id
        JOIN entity_nodes AS member ON member.entity_id = entity.entity_id
        JOIN nodes AS other ON other.id = member.node_id
        WHERE seed.provider = ? AND seed.external_id = ?
        ORDER BY other.provider, other.external_id
    """, ("mal", "1")).fetchall()

for anchor_id, provider, external_id in rows:
    print(f"amdb:{anchor_id}", provider, external_id)
```

Dieses SQL gibt **Mitglieder einer AMDB-Entität** wieder, nicht die streng gefilterten direkten Resolver-Routen. Für diese `MappingResolver.resolve()` verwenden und `anchor_id` statt `entity_id` speichern.

Portable TSV-/JSONL-Routen können mit `zstd` entpackt werden. Die Felder stehen im Release-Abschnitt.

```bash
curl -fL -o mappings.tsv.zst \
  https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.tsv.zst
zstd -dc mappings.tsv.zst | head -n 5
```

Beim gemeinsamen Einsatz mit Timestamp DB kompatible Versionen auswählen sowie Manifeste und Prüfsummen validieren.

## Konfidenz und Konflikte

Die Konfidenz berücksichtigt die stärkste Quelle, unabhängige Evidenzgruppen und zusätzliche Belege. Eine ausreichend starke Einzelquelle oder zwei unabhängige Gruppen können eine Kante bestätigen. Schwächere Verbindungen bleiben Kandidaten.

Konflikte sind gerichtet: `A → B` kann uneindeutig sein, obwohl die Umkehrung sicher ist. Manuelle Entscheidungen können gezielt annehmen oder verwerfen und bewahren eine Historie. Ihre Folgen für andere Verbraucher müssen berücksichtigt werden.

```text
confidence = min(100,
    max_weight
    + 8 × (distinct_evidence_groups - 1)
    + 2 × min(5, evidence_count - distinct_evidence_groups)
)

accepted: max_weight >= 80 OR distinct_evidence_groups >= 2
candidate: unconfirmed relationships
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

## Release-Dateien und Nutzung

Jedes Release enthält Laufzeit- und Evidenzdatenbanken, zstd-Dateien, portable gerichtete Exporte, ein Manifest und SHA-256. Die Textformate enthalten bereinigte eindeutige Resolver-Routen statt roher Graphkanten.

`manifest.json` ist die maßgebliche Quelle für Schemas, Dateigrößen, Quellversionen, Hashes, Zahlen und Fingerprints. Diese Werte ändern sich; feste Gesamtzahlen im README wären veraltet. Prüfen Sie heruntergeladene Dateien anhand der Checksums.

Releases werden nach Änderungen, regelmäßigen Quellprüfungen, Tags oder manuell erzeugt. Unveränderte Quellen können einen geplanten Release verhindern. GitHub liefert Quellarchive bereits standardmäßig.

| Datei | Zweck |
| --- | --- |
| `mappings.db` | Kompakte Laufzeit-SQLite |
| `mappings.db.zst` | Komprimierte Runtime-DB |
| `mappings-evidence.db.zst` | Komprimierte Evidenz-DB |
| `mappings.tsv.zst` | Gerichtete TSV-Routen |
| `mappings.jsonl.zst` | Gerichtete JSON-Lines-Routen |
| `manifest.json` | Schema, Quellen, Umfang und Hashes |
| `SHA256SUMS` | SHA-256-Prüfsummen |

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

`source_provider` — Quellanbieter; `source_id` — Quell-ID; `target_provider` — Zielanbieter; `target_id` — Ziel-ID; `confidence` — Konfidenz; `evidence_count` — Beleganzahl; `evidence_group_count` — Unabhängige Gruppen; `max_weight` — Maximalgewicht; `origin` — Herkunft

## Prüfung und Entwicklung

CI prüft Tests, Formatierung, SQLite-Integrität, Anker, Redirects, Vertrauen, Konflikte und Release-Pakete. Neue Importer sollten zusammen mit Tests geändert werden.

```bash
python -m pip install -e .
python -m pip install pytest ruff
python -m pytest -q
python -m ruff check .
```

[Identitätsvertrag](../docs/IDENTITY.md)

## Dokumentation

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## Lizenz und Quellenangaben

Der Code ist Apache-2.0-lizenziert. Kompilierte Daten unterliegen Drittanbieterbedingungen, darunter ODbL/DbCL und Namensnennungspflichten. Vor der Weitergabe beide Lizenzdokumente lesen. [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
