> **Progetto assistito dall’IA:** questo progetto è stato sviluppato con l’aiuto dell’IA.

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <strong>Italiano</strong>
</p>

# Anime Mapping DB

**Anime Mapping DB** è un builder autonomo e un database SQLite distribuibile per collegare identificatori anime tra cataloghi e servizi di tracking pubblici. Non esiste una mapping HTTP API: i consumer scaricano `mappings.db`/`mappings.db.zst` dalle GitHub Releases e risolvono gli ID localmente.

## Caratteristiche

- 55 namespace di provider e 18 dataset di input.
- ID pubblico stabile del progetto: `amdb:<anchor_id>`; `entity_id` resta locale alla build e non è mai una chiave esterna.
- I database runtime/evidence pubblicati usano il layout `compact-v1` ottimizzato per la lettura.
- Risoluzione diretta a un solo hop, senza traversal transitivo rischioso.
- Confidence basata sulle evidence senza raddoppiare fonti correlate.
- Runtime separato dal database di provenance/evidence.
- AnimeAPI usata solo come dataset supplementare ospitato su GitHub, mai tramite REST API.
- Release riproducibili con manifest, hash, conteggi dei provider e Zstandard.

## Stato della build validata

| Metric | Value |
| --- | ---: |
| Dataset inputs | 18 |
| Provider namespaces | 55 |
| Unique provider/ID nodes | 430,209 |
| Source records | 803,634 |
| Evidence edges | 2,346,017 |
| Runtime edges | 1,233,485 |
| Accepted runtime edges | 1,225,311 |
| Directional conflicts | 21,975 |
| Stable AMDB entities | 34,845 |
| Resolver-safe text routes | 2,385,942 |
| `mappings.db` | 83,537,920 B (~79.7 MiB) |
| `mappings.db.zst` | 17,258,973 B (~16.5 MiB) |
| `mappings-evidence.db.zst` | 23,559,041 B (~22.5 MiB) |

## Database presenti in `mappings.db`

Tutti i 55 namespace della build validata. Varianti come `tmdb_tv` e `tmdb_movie` sono separate intenzionalmente per preservarne la semantica.

| Namespace | Database / ID | Count |
| --- | --- | ---: |
| `allcinema` | AllCinema | 9,752 |
| `anidb` | AniDB | 16,345 |
| `anikore` | Anikore | 655 |
| `anilist` | AniList | 22,437 |
| `animecharacters` | Anime Characters Database | 2,364 |
| `animeclick` | AnimeClick | 2,154 |
| `animecountdown` | AnimeCountdown | 14,711 |
| `animefillerlist` | Anime Filler List | 88 |
| `animemorial` | Anime Memorial | 376 |
| `animenfo` | AnimeNfo | 4,868 |
| `animeplanet` | Anime-Planet | 25,127 |
| `animetaizen` | Anime Taizen | 3,254 |
| `animethemes` | AnimeThemes | 5,017 |
| `anisearch` | aniSearch | 20,088 |
| `anison` | Anison | 8,226 |
| `ann` | Anime News Network | 12,402 |
| `annict` | Annict | 13,353 |
| `bahamut` | Bahamut Animation Crazy | 783 |
| `bangumi` | Bangumi | 4,268 |
| `bilibili` | Bilibili Bangumi | 829 |
| `crunchyroll` | Crunchyroll series | 2,427 |
| `douban` | Douban | 850 |
| `funimation` | Funimation | 534 |
| `hidive` | HIDIVE | 490 |
| `hikka` | Hikka | 27,168 |
| `imdb` | IMDb | 7,162 |
| `kaize` | Kaize slug | 23,233 |
| `kaize_id` | Kaize numeric ID | 9,956 |
| `kitsu` | Kitsu | 21,693 |
| `lain` | Lain MediaDB | 521 |
| `letterboxd_lid` | Letterboxd LID | 1,269 |
| `letterboxd_slug` | Letterboxd slug | 1,269 |
| `letterboxd_uid` | Letterboxd UID | 1,269 |
| `livechart` | LiveChart.me | 12,375 |
| `mal` | MyAnimeList | 28,241 |
| `marumeganel` | Marumegane | 464 |
| `mediaarts` | Media Arts Database | 971 |
| `nanime` | N-Anime | 536 |
| `nautiljon` | Nautiljon slug | 8,979 |
| `nautiljon_id` | Nautiljon numeric ID | 9,002 |
| `netflix` | Netflix | 328 |
| `niconico` | Niconico | 842 |
| `notify` | Notify.moe | 16,861 |
| `otakotaku` | Otak Otaku | 3,131 |
| `shikimori` | Shikimori | 27,727 |
| `shoboi` | Shoboi / Syoboi Calendar | 6,525 |
| `silveryasha` | SilverYasha | 5,703 |
| `simkl` | SIMKL | 14,711 |
| `tmdb_movie` | TMDB movie | 5,027 |
| `tmdb_tv` | TMDB TV | 4,465 |
| `trakt` | Trakt title | 6,100 |
| `tv_animation_museum` | TV Animation Museum | 38 |
| `tvdb` | TVDB series | 4,852 |
| `tvdb_movie` | TVDB movie | 1,116 |
| `wikidata` | Wikidata QID | 7,277 |

`manifest.json` contains the same provider counts for every release.

## Dataset utilizzati

| Dataset | Ruolo / accesso |
| --- | --- |
| Fribb/anime-lists | fonte diretta obbligatoria, GitHub JSON |
| Kometa-Team/Anime-IDs | fonte diretta obbligatoria, GitHub JSON |
| Anime-Lists/anime-lists | fonte diretta obbligatoria, GitHub XML |
| cplieger/animap | fonte diretta obbligatoria, GitHub Release |
| cedya77/anime-offline-database | opzionale, GitHub Release JSONL; fork mantenuto della linea Manami |
| anibridge/anibridge-mappings | opzionale, GitHub Release |
| Wikidata / Bahamut | opzionale, QLever bulk SPARQL → WDQS fallback → bootstrap CC0 locale |
| rensetsu/db.notify.rensetsu-mirai | opzionale, GitHub JSON |
| kawaiioverflow/arm | opzionale, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | opzionale, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | opzionale, GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | opzionale, GitHub JSON, CC0 |
| rensetsu/db.rensetsu.public-dump AnimeThemes | supplemental, GitHub JSON, CC0 |
| anime-and-manga/lists | optional corroborating, GitHub JSON |
| shinkro/community-mapping | optional corroborating, GitHub JSON; title-level TVDB/TMDB only |
| notseteve/AnimeAggregations | supplemental, GitHub JSON, two-anchor validation |
| Wikidata multi-ID | supplemental, QLever bulk + WDQS fallback, two-anchor validation |
| nattadasu/animeApi | supplementare, solo GitHub `database/animeapi.tsv` |

## Fonti supplementari validate tramite anchor

AnimeAggregations, Wikidata multi-ID e AnimeAPI vengono elaborati solo dopo la costruzione del grafo provvisorio dalle fonti dirette. Un ID mancante può essere aggiunto soltanto quando almeno due anchor esatti già noti sono collegati da un edge diretto accettato e privo di conflitti. Queste fonti quindi non possono creare da sole una nuova identità del titolo.

AnimeAggregations viene letto esclusivamente come file bulk GitHub; VNDB e i link generici a siti/social sono esclusi. Wikidata viene scaricato con una singola query SPARQL bulk tramite QLever, con WDQS come fallback. Da Shinkro vengono importati solo i mapping title-level MAL↔TVDB series e MAL↔TMDB movie; il routing di stagioni/episodi resta fuori dal grafo.

## Come viene usata AnimeAPI

AnimeAPI non viene contata come un nuovo voto indipendente perché aggrega varie fonti che consumiamo già direttamente. Prima viene costruito il grafo provvisorio dalle fonti dirette. Una riga AnimeAPI può aggiungere un ID mancante solo se contiene almeno due anchor già noti collegati da un edge diretto accettato e privo di conflitti. Non aggiunge evidence tra gli anchor e non duplica il voto di un target già esistente. `trakt_may_invalid=true` e tutti i campi season vengono esclusi.

Il builder scarica solo `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv`; non chiama REST AnimeAPI, Geckyzz API né gli scraper dei siti di AnimeAPI.

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## Identità del progetto

Anime Mapping DB separa due tipi di ID. `entity_id` è una chiave SQLite densa e locale a una singola build; può essere rinumerata e non va persistita fuori da quel file. `anchor_id` è l’ID pubblico stabile del progetto, con forma testuale `amdb:<integer>`, per esempio `amdb:18472`.

Le tabelle `entities`, `entity_nodes` e `anchor_redirects` formano questo livello. Gli `(provider, external_id)` concreti restano in `nodes`. In caso di merge i vecchi anchor vengono reindirizzati; in caso di split il componente con la maggiore sovrapposizione conserva l’anchor precedente. Gli anchor ritirati non vengono riutilizzati per altri titoli. Contratto completo: [`IDENTITY.md`](IDENTITY.md).

## Prestazioni

Benchmark riproducibile: `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`. Sullo stesso host Linux: vecchia build a 7 fonti median 0.418 ms / p95 0.749 ms; nuova build a 18 dataset / 55 provider **0.354 ms / 0.497 ms**. La build a 18 dataset dà anche mean 0.378 ms / p99 0.655 ms. È un microbenchmark, non una garanzia di latenza.

## Runtime ed evidence

`mappings.db` usa il layout compact-v1 e contiene `metadata`, `nodes`, `edges`, `conflicts`, `entities`, `entity_nodes`, `anchor_redirects` e le tabelle di override. Il lookup forward usa la PK `edges(a_node,b_node)` e quello reverse accepted un singolo indice parziale. `mappings-evidence.db` normalizza le relazioni ripetute tramite `record_nodes`; il vecchio contratto `edge_evidence` resta disponibile come compatibility view in sola lettura. Un consumer normale non deve aprire il database evidence.

## Confidence e conflitti

Un edge viene accettato se `max_weight >= 80` oppure se almeno due evidence group indipendenti lo confermano. I conflitti direzionali bloccano soltanto la rotta ambigua. Il resolver non attraversa il grafo in modo transitivo.

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Release e build locale

Ogni release contiene `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst`, gli export portabili `mappings.tsv.zst` / `mappings.jsonl.zst`, `manifest.json` e `SHA256SUMS`. GitHub genera automaticamente gli archivi standard **Source code (zip)** e **Source code (tar.gz)** per ogni Release, quindi il progetto non carica archivi sorgente personalizzati duplicati. Gli export testuali contengono route dirette resolver-safe dopo l’applicazione di conflicts/overrides; SQLite resta il formato runtime canonico. L’automazione parte dopo modifiche al mapping engine su `main`, ogni giorno alle 03:17 UTC, con tag `v*` e manualmente. Un controllo giornaliero senza modifiche al source fingerprint non pubblica un nuovo release.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Licenze

Il codice del progetto è Apache-2.0. Il database compilato combina dati di terze parti con obblighi propri; AnimeAPI e anime-offline-database usano ODbL 1.0 + DbCL 1.0. Vedi `THIRD_PARTY_NOTICES.md`.
