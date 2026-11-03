> **KI-unterstütztes Projekt:** Dieses Projekt wurde mit Hilfe von KI entwickelt.

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <strong>Deutsch</strong> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# Anime Mapping DB

**Anime Mapping DB** ist ein eigenständiger Builder und eine veröffentlichte SQLite-Datenbank zur Zuordnung von Anime-IDs zwischen öffentlichen Katalogen und Tracking-Diensten. Es gibt keine Mapping-HTTP-API: Anwendungen laden `mappings.db` bzw. `mappings.db.zst` aus GitHub Releases und lösen IDs lokal mit SQLite auf.

## Highlights

- 55 Provider-Namespaces und 18 Eingabe-Datensätze.
- Stabile öffentliche Projekt-ID: `amdb:<anchor_id>`; die build-lokale `entity_id` ist niemals ein externer Schlüssel.
- Veröffentlichte Runtime-/Evidence-Datenbanken verwenden das leseoptimierte `compact-v1`-Layout.
- Nur direkte One-Hop-Auflösung, kein unsicheres transitives Traversieren.
- Evidence-basierte Confidence ohne künstliche Doppelstimmen korrelierter Quellen.
- Kleine Runtime-Datenbank getrennt von der Provenance-Datenbank.
- AnimeAPI nur als GitHub-gehostete Zusatzquelle, nie über dessen REST API.
- Releases enthalten Manifest, Hashes, Provider-Zählungen und Zstandard-Dateien.

## Stand der validierten Datenbank

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

## Datenbanken in `mappings.db`

Alle 55 Namespaces der validierten Build-Version. Varianten wie `tmdb_tv` und `tmdb_movie` sind wegen unterschiedlicher Semantik absichtlich getrennt.

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

## Verwendete Datensätze

| Datensatz | Rolle / Zugriff |
| --- | --- |
| Fribb/anime-lists | erforderliche direkte Quelle, GitHub JSON |
| Kometa-Team/Anime-IDs | erforderliche direkte Quelle, GitHub JSON |
| Anime-Lists/anime-lists | erforderliche direkte Quelle, GitHub XML |
| cplieger/animap | erforderliche direkte Quelle, GitHub Release |
| cedya77/anime-offline-database | optional, GitHub Release JSONL; gepflegter Fork der Manami-Linie |
| anibridge/anibridge-mappings | optional, GitHub Release |
| Wikidata / Bahamut | optional, QLever bulk SPARQL → WDQS fallback → lokaler CC0-Bootstrap |
| rensetsu/db.notify.rensetsu-mirai | optional, GitHub JSON |
| kawaiioverflow/arm | optional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | optional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | optional, GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | optional, GitHub JSON, CC0 |
| rensetsu/db.rensetsu.public-dump AnimeThemes | supplemental, GitHub JSON, CC0 |
| anime-and-manga/lists | optional corroborating, GitHub JSON |
| shinkro/community-mapping | optional corroborating, GitHub JSON; title-level TVDB/TMDB only |
| notseteve/AnimeAggregations | supplemental, GitHub JSON, two-anchor validation |
| Wikidata multi-ID | supplemental, QLever bulk + WDQS fallback, two-anchor validation |
| nattadasu/animeApi | ergänzend, nur GitHub `database/animeapi.tsv` |

## Anchor-validierte Zusatzquellen

AnimeAggregations, Wikidata multi-ID und AnimeAPI werden erst nach dem vorläufigen Graphen aus direkten Quellen verarbeitet. Ein fehlender Identifier darf nur ergänzt werden, wenn mindestens zwei bereits bekannte exakte Anchor-IDs durch eine akzeptierte direkte und konfliktfreie Kante verbunden sind. Die Zusatzquellen können daher keine neue Titelidentität aus dem Nichts erzeugen.

AnimeAggregations wird ausschließlich als fertige GitHub-Bulkdatei gelesen; VNDB sowie generische Website-/Social-Links werden ausgeschlossen. Wikidata wird mit einer einzigen Bulk-SPARQL-Abfrage über QLever und WDQS als Fallback geladen. Aus Shinkro werden nur title-level MAL↔TVDB-Series- und MAL↔TMDB-Movie-Zuordnungen importiert; Season-/Episode-Routing bleibt außerhalb des Graphen.

## AnimeAPI-Integration

AnimeAPI wird nicht als zusätzliche unabhängige Stimme gezählt, da es mehrere unserer direkten Quellen selbst aggregiert. Zuerst entsteht der vorläufige Graph aus direkten Quellen. Ein AnimeAPI-Eintrag darf einen fehlenden Ziel-Identifier nur ergänzen, wenn mindestens zwei bereits bekannte Anker eine akzeptierte direkte, konfliktfreie Verbindung besitzen. Bestehende Ziel-IDs erhalten keine zusätzliche korrelierte Stimme. Ungültig markierte Trakt-Zeilen und alle Season-Felder werden ausgeschlossen.

Der Builder lädt ausschließlich `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv`; weder AnimeAPI REST noch Geckyzz noch AnimeAPIs Site-Scraper werden aufgerufen.

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## Projektidentität

Anime Mapping DB trennt zwei ID-Arten. `entity_id` ist ein dichter, build-lokaler SQLite-Schlüssel und darf nicht außerhalb einer konkreten `mappings.db` persistiert werden. `anchor_id` ist die stabile öffentliche Projekt-ID; die Textform lautet `amdb:<integer>`, zum Beispiel `amdb:18472`.

Die Runtime-Tabellen `entities`, `entity_nodes` und `anchor_redirects` bilden diese Schicht. Konkrete `(provider, external_id)` bleiben in `nodes`. Bei einem Merge werden alte Anchors umgeleitet; bei einem Split behält die Komponente mit der größten Überlappung den bisherigen Anchor. Ausgemusterte Anchor-Nummern werden nicht für andere Titel wiederverwendet. Details: [`IDENTITY.md`](IDENTITY.md).

## Lookup-Performance

Reproduzierbar mit `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`. Auf demselben Linux-Host: alte 7-Quellen-Build median 0.418 ms / p95 0.749 ms; neue 18-Dataset-/55-Provider-Build **0.354 ms / 0.497 ms**. Die 18-Dataset-Build ergab zusätzlich mean 0.378 ms / p99 0.655 ms. Dies ist ein Mikrobenchmark, keine Latenzgarantie.

## Runtime und Evidence

`mappings.db` verwendet das compact-v1-Layout und enthält `metadata`, `nodes`, `edges`, `conflicts`, `entities`, `entity_nodes`, `anchor_redirects` sowie Override-Tabellen. Vorwärts-Lookups nutzen den Primärschlüssel `edges(a_node,b_node)`, akzeptierte Rückwärts-Lookups einen einzigen partiellen Index. `mappings-evidence.db` normalisiert wiederholte Beziehungen in `record_nodes`; der frühere `edge_evidence`-Vertrag bleibt als schreibgeschützte Compatibility-View erhalten. Normale Consumer benötigen die Evidence-Datei nicht.

## Confidence und Konflikte

Eine Edge wird akzeptiert, wenn `max_weight >= 80` oder mindestens zwei unabhängige Evidence Groups zustimmen. Directional Conflicts sperren nur die mehrdeutige Richtung. Der Resolver läuft absichtlich nicht transitiv durch den Graphen.

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Releases und lokale Builds

Jedes Release enthält `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst`, die portablen Exporte `mappings.tsv.zst` / `mappings.jsonl.zst`, `manifest.json` und `SHA256SUMS`. GitHub erzeugt für jedes Release automatisch die Standardarchive **Source code (zip)** und **Source code (tar.gz)**; das Projekt lädt daher bewusst keine doppelten eigenen Quellcodearchive hoch. Die Textdateien enthalten gerichtete resolver-sichere Routen nach Anwendung von Conflicts/Overrides; SQLite bleibt das kanonische Runtime-Format. Automatisierung läuft nach Änderungen am Mapping-Engine auf `main`, täglich um 03:17 UTC, für `v*`-Tags und manuell. Ein täglicher Lauf ohne geänderten Source-Fingerprint veröffentlicht kein neues Release.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Lizenzen

Projektcode: Apache-2.0. Die kompilierte Datenbank kombiniert Drittanbieter-Daten mit eigenen Lizenzpflichten; AnimeAPI und anime-offline-database sind insbesondere ODbL 1.0 + DbCL 1.0. Siehe `THIRD_PARTY_NOTICES.md`.
