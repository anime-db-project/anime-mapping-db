> **Progetto assistito dall’IA:** questo progetto è stato sviluppato con l’aiuto dell’IA.

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <strong>Italiano</strong>
</p>

# Anime Mapping DB

**Anime Mapping DB** è un builder autonomo e un database SQLite distribuibile per collegare identificatori anime tra cataloghi e servizi di tracking pubblici. Non esiste una mapping HTTP API: i consumer scaricano `mappings.db`/`mappings.db.zst` dalle GitHub Releases e risolvono gli ID localmente.

## Caratteristiche

- 55 namespace di provider e 18 dataset di input.
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
| Unique provider/ID nodes | 429,740 |
| Source records | 803,456 |
| Evidence edges | 2,343,467 |
| Runtime edges | 1,231,762 |
| Accepted runtime edges | 1,223,386 |
| Directional conflicts | 21,860 |
| `mappings.db` | ~116.7 MiB |
| `mappings.db.zst` | ~20.2 MiB |

## Database presenti in `mappings.db`

Tutti i 55 namespace della build validata. Varianti come `tmdb_tv` e `tmdb_movie` sono separate intenzionalmente per preservarne la semantica.

| Namespace | Database / ID | Count |
| --- | --- | ---: |
| `allcinema` | AllCinema | 9,752 |
| `anidb` | AniDB | 16,341 |
| `anikore` | Anikore | 655 |
| `anilist` | AniList | 22,435 |
| `animecharacters` | Anime Characters Database | 2,363 |
| `animeclick` | AnimeClick | 2,153 |
| `animecountdown` | AnimeCountdown | 14,711 |
| `animefillerlist` | Anime Filler List | 88 |
| `animemorial` | Anime Memorial | 376 |
| `animenfo` | AnimeNfo | 4,868 |
| `animeplanet` | Anime-Planet | 25,126 |
| `animetaizen` | Anime Taizen | 3,252 |
| `animethemes` | AnimeThemes | 5,017 |
| `anisearch` | aniSearch | 20,042 |
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
| `hikka` | Hikka | 27,157 |
| `imdb` | IMDb | 7,162 |
| `kaize` | Kaize slug | 23,233 |
| `kaize_id` | Kaize numeric ID | 9,956 |
| `kitsu` | Kitsu | 21,692 |
| `lain` | Lain MediaDB | 521 |
| `letterboxd_lid` | Letterboxd LID | 1,269 |
| `letterboxd_slug` | Letterboxd slug | 1,269 |
| `letterboxd_uid` | Letterboxd UID | 1,269 |
| `livechart` | LiveChart.me | 12,367 |
| `mal` | MyAnimeList | 28,231 |
| `marumeganel` | Marumegane | 464 |
| `mediaarts` | Media Arts Database | 971 |
| `nanime` | N-Anime | 536 |
| `nautiljon` | Nautiljon slug | 8,979 |
| `nautiljon_id` | Nautiljon numeric ID | 9,002 |
| `netflix` | Netflix | 328 |
| `niconico` | Niconico | 842 |
| `notify` | Notify.moe | 16,861 |
| `otakotaku` | Otak Otaku | 3,131 |
| `shikimori` | Shikimori | 27,711 |
| `shoboi` | Shoboi / Syoboi Calendar | 6,525 |
| `silveryasha` | SilverYasha | 5,703 |
| `simkl` | SIMKL | 14,711 |
| `tmdb_movie` | TMDB movie | 4,660 |
| `tmdb_tv` | TMDB TV | 4,465 |
| `trakt` | Trakt title | 6,100 |
| `tv_animation_museum` | TV Animation Museum | 38 |
| `tvdb` | TVDB series | 4,854 |
| `tvdb_movie` | TVDB movie | 1,116 |
| `wikidata` | Wikidata QID | 7,276 |

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

## Prestazioni

Benchmark riproducibile: `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`. Sullo stesso host Linux: vecchia build a 7 fonti median 0.418 ms / p95 0.749 ms; nuova build a 18 dataset / 55 provider **0.380 ms / 0.516 ms**. La build a 18 dataset dà anche mean 0.394 ms / p99 0.575 ms. È un microbenchmark, non una garanzia di latenza.

## Runtime ed evidence

`mappings.db` contiene le tabelle runtime per lookup e override. `mappings-evidence.db` conserva dataset, record sorgente, evidence group e provenance. Un consumer normale non necessita del file evidence.

## Confidence e conflitti

Un edge viene accettato se `max_weight >= 80` oppure se almeno due evidence group indipendenti lo confermano. I conflitti direzionali bloccano soltanto la rotta ambigua. Il resolver non attraversa il grafo in modo transitivo.

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Release e build locale

Ogni release contiene `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst`, oltre agli export testuali portabili `mappings.tsv.zst` e `mappings.jsonl.zst`, più `manifest.json` e `SHA256SUMS`. I file di testo contengono route dirette sicure per il resolver dopo l’applicazione dei conflitti direzionali e degli override manuali; SQLite resta il formato runtime canonico. L’automazione parte dopo modifiche al motore su `main`, ogni giorno alle 03:17 UTC, con tag `v*` o manualmente. Nessuna release giornaliera se il source fingerprint non cambia.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Licenze

Il codice del progetto è Apache-2.0. Il database compilato combina dati di terze parti con obblighi propri; AnimeAPI e anime-offline-database usano ODbL 1.0 + DbCL 1.0. Vedi `THIRD_PARTY_NOTICES.md`.
