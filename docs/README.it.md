> **Progetto sviluppato con l'aiuto dell'IA.**

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <strong>Italiano</strong>
</p>

# anime-mapping-db

[![CI](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml)
[![Releases](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Code license](https://img.shields.io/badge/Code-Apache%202.0-D22128.svg)](../LICENSE)
[![Data license](https://img.shields.io/badge/Data-Upstream%20terms-555555.svg)](../DATA_LICENSE.md)

Database riproducibile di corrispondenze fra ID anime di servizi diversi, con tracciabilità delle fonti. Offre ID stabili del progetto e interrogazioni SQLite compatte.

<!-- BEGIN AUTO-GENERATED DATABASE STATS -->
## Il database in numeri

Questa versione contiene **34,867 gruppi di identità AMDB indicizzati**. È una misura del database, **non un conteggio verificato di titoli anime unici**.

| Indicatore | Valore |
| --- | ---: |
| Gruppi di identità AMDB indicizzati | **34,867** |
| Namespace di ID | **55** |
| Dataset sorgenti | **18** |
| Collegamenti accettati | **1,225,854** |
| Percorsi diretti sicuri | **2,386,752** |
| Conflitti direzionali | **22,021** |
| Record sorgenti | **803,856** |
| Relazioni di prova | **2,346,897** |
| Dimensione SQLite | **79.7 MiB** |
| SQLite compresso | **16.5 MiB** |

### Prestazioni di ricerca locale

| Indicatore | Valore |
| --- | ---: |
| Mediana | **0.224 ms** |
| Media | **0.227 ms** |
| p95 | **0.253 ms** |
| p99 | **0.282 ms** |
| Query sequenziali/s | **4,402** |

Query sequenziali MappingResolver con cache calda sul DB della release, Linux / Python 3.12. 300 ID × 2 round; non misura la latenza delle API.

Snapshot della release: **2026-11-10**, [v2026.11.10.32](https://github.com/anime-db-project/anime-mapping-db/releases/tag/v2026.11.10.32). [Manifest attuale](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json).

<!-- END AUTO-GENERATED DATABASE STATS -->

## Funzionalità

- Identificatori `amdb:<anchor_id>` stabili tra ricompilazioni.
- Corrispondenze con prove, livello di affidabilità e gestione prudente dei conflitti.
- Risoluzione diretta senza attraversamenti arbitrari del grafo.
- Database runtime compatto separato dall'archivio dettagliato delle prove.
- Release con DB compressi, esportazioni testuali, manifest e checksum.

## Identità e regole di associazione

Anime Mapping DB offre `amdb:<anchor_id>` come identità stabile del progetto, indipendente da MAL, AniList e altri servizi. Può essere conservata tra build. `entity_id` invece è una chiave interna SQLite valida solo per quella specifica versione del database.

Gli ID esterni sono nodi `(provider, external_id)`. Nodi verificati possono formare una sola entità, ma due ID distinti dello stesso provider non vengono compressi in un unico titolo. Le relazioni ambigue restano irrisolte.

Le ricompilazioni mantengono gli anchor delle entità riconosciute. Le fusioni valide conservano una chiave e aggiungono redirect; le separazioni ricevono nuove chiavi senza riciclare ID dismessi. Questo garantisce riferimenti coerenti nelle banche dati collegate.

```text
(provider, external_id) ──accepted edge── (provider, external_id)
          \                         /
           \── stable amdb:<anchor_id> ──/
                   │
              anchor redirects
```

## Fonti dei dati

Il builder combina 18 input fra dataset di mapping diretti e cataloghi supplementari verificati. Gli input aggiuntivi non possono creare nuove identità senza conferme indipendenti. Fonti e licenze sono riportate nel manifest.

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

`amdb:<anchor_id>` è l'ID stabile del titolo. Gli ID esterni sono alias documentati; `entity_id` è valido solo nella singola build. Le corrispondenze ambigue non sono selezionate automaticamente. [Identity contract](../docs/IDENTITY.md).

## Input e provenienza

Il builder carica dataset pubblici, registra le prove di origine e poi crea il grafo runtime. Ogni record mantiene origine e gruppo indipendente, evitando di contare come voti distinti copie e mirror.

Le fonti dirette creano collegamenti verificabili. AnimeAPI, AnimeAggregations, riferimenti AnimeThemes e Wikidata multi-ID arricchiscono solo entità già confermate con almeno due anchor esistenti e coerenti. Così non si confondono adattamenti, stagioni e franchising.

URL, hash e versioni sono documentati nel manifest; `anime_mapping_db/config.py` definisce gli input. Per risolvere ID si legge la SQLite locale, senza REST di terzi.

```text
1. Acquisire dataset pubblici
2. Raggruppare prove per fonte indipendente
3. Valutare e validare legami diretti
4. Gestire conflitti e ID stabili
5. Audit, compressione e rilascio
```

## Struttura dei database

La compatta `mappings.db` contiene nodi, archi, conflitti direzionali, entità stabili, redirect e modifiche manuali. È ottimizzata per lookup diretti indicizzati, non per percorsi ricorsivi senza vincoli.

La separata `mappings-evidence.db` conserva fonti, osservazioni, gruppi di prova e relazioni che giustificano i mapping. I consumatori di soli ID possono ometterla. Entrambe sono verificate prima di essere pubblicate.

```text
mappings.db
  metadata · nodes · edges · conflicts
  entities · entity_nodes · anchor_redirects
  mapping_overrides · mapping_override_history

mappings-evidence.db
  metadata · datasets · nodes · evidence_groups
  records · record_nodes · edge_evidence (view)
```

## Avvio rapido

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Utilizzo del resolver

Una query usa il namespace e l'ID esterno e restituisce soltanto destinazioni dirette, accettate e non ambigue. Lo stesso numero in MAL e AniList non dimostra che le opere coincidano.

È disponibile un resolver Python oppure SQLite. Le tabelle delle entità e degli anchor contengono le identità stabili; non sostituire il lookup diretto con una traversata ricorsiva illimitata.

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

## Come utilizzare il database

Gli artefatti pubblicati sono file locali: per consultare gli ID non è necessario ricompilare o usare API key. Sono disponibili più modalità:

- **Integrazione Python.** Usare `MappingResolver` in bot, siti e cataloghi.
- **SQLite diretto.** Interrogare offline con driver SQLite per Python, Rust, Go, Node.js e altri linguaggi.
- **Import e analisi.** Caricare TSV/JSONL in altri database, indici e pipeline ETL.
- **Identità comune.** Memorizzare `amdb:<anchor_id>` e unire record di progetti differenti.
- **Controllo delle fonti.** Aprire il database delle prove per verificare mapping ambigui.

Scarica direttamente SQLite dalla release:

```bash
curl -fL -o mappings.db \
  https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db
```

Installa il pacchetto del repository (`python -m pip install -e .`) per `MappingResolver`:

```python
from anime_mapping_db.resolver import MappingResolver

resolver = MappingResolver("mappings.db")
if resolver.available():
    matches = resolver.resolve({"mal": "1"})
    print(matches)  # Verified, direct and conflict-safe provider IDs
```

Esempio di lettura dell'ID AMDB e dei relativi provider usando `sqlite3` di Python:

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

Questo SQL mostra **i membri dell'entità AMDB**, non i percorsi diretti filtrati del resolver. Per i mapping diretti usa `MappingResolver.resolve()` e salva `anchor_id`, non `entity_id`.

I percorsi TSV/JSONL si possono decomprimere con `zstd`; i campi sono documentati nella sezione release.

```bash
curl -fL -o mappings.tsv.zst \
  https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.tsv.zst
zstd -dc mappings.tsv.zst | head -n 5
```

Per unire Timestamp DB usa release compatibili e verifica manifest e SHA-256.

## Affidabilità e conflitti

L'affidabilità considera il peso massimo della fonte, gruppi di prove indipendenti e conferme aggiuntive. Una fonte forte o due gruppi indipendenti possono confermare una relazione. I legami più deboli restano candidati.

I conflitti sono direzionali: `A → B` può essere ambiguo anche se il contrario è sicuro. Gli override manuali accettano o rifiutano singoli mapping con traccia delle modifiche; attenzione ai programmi che li riutilizzano.

```text
confidence = min(100,
    max_weight
    + 8 × (distinct_evidence_groups - 1)
    + 2 × min(5, evidence_count - distinct_evidence_groups)
)

accepted: max_weight >= 80 OR distinct_evidence_groups >= 2
candidate: unconfirmed relationships
```

## Database e release

Per integrarlo scaricare `mappings.db.zst` e `manifest.json` dall'ultima release. `mappings-evidence.db.zst` conserva le prove; `mappings.tsv.zst` e `mappings.jsonl.zst` sono esportazioni portabili. Le pubblicazioni programmate avvengono quando cambiano i dati delle fonti.

- [Latest release](https://github.com/anime-db-project/anime-mapping-db/releases/latest)
- [Runtime database (zstd)](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db.zst)
- [Release manifest](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json)

```text
data/mappings/mappings.db
data/mappings/mappings-evidence.db
```

## File delle release e integrazione

Le release includono database runtime ed evidence, versioni zstd, esportazioni testuali dirette, manifest e SHA-256. I file di testo rappresentano percorsi sicuri filtrati, non archi grezzi.

`manifest.json` è la fonte autorevole per schemi, dimensioni, versioni dei dati, hash, conteggi e fingerprint. Questi valori cambiano a ogni build, perciò non conviene fissarli nel README. Verificare i checksum dopo il download.

Le release possono seguire modifiche al codice, controlli pianificati, tag o avvii manuali. Se gli input non cambiano, il controllo automatico può non pubblicare nulla. GitHub fornisce già gli archivi sorgente.

| File | Funzione |
| --- | --- |
| `mappings.db` | SQLite runtime compatta |
| `mappings.db.zst` | Runtime compresso |
| `mappings-evidence.db.zst` | Archivio prove compresso |
| `mappings.tsv.zst` | Percorsi TSV diretti |
| `mappings.jsonl.zst` | Percorsi JSON Lines diretti |
| `manifest.json` | Schemi, fonti, conteggi e hash |
| `SHA256SUMS` | Checksum SHA-256 |

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

`source_provider` — Provider origine; `source_id` — ID origine; `target_provider` — Provider destinazione; `target_id` — ID destinazione; `confidence` — Affidabilità; `evidence_count` — Record di prova; `evidence_group_count` — Gruppi indipendenti; `max_weight` — Peso maggiore; `origin` — Provenienza

## Verifiche e sviluppo

La CI verifica test, formattazione, integrità SQLite, anchor, redirect, affidabilità, conflitti e pacchetti. Accompagnare nuovi importer con test.

```bash
python -m pip install -e .
python -m pip install pytest ruff
python -m pytest -q
python -m ruff check .
```

[Contratto d'identità](../docs/IDENTITY.md)

## Documentazione

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## Licenza e attribuzioni

Codice sotto Apache-2.0. I dati compilati includono contenuti di terzi con termini distinti, fra cui ODbL/DbCL e obblighi di attribuzione. Leggere entrambi i documenti prima della ridistribuzione. [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
