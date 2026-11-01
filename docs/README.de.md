> **KI-unterstütztes Projekt:** Dieses Projekt wurde mit Hilfe von KI entwickelt.

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <strong>Deutsch</strong> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# Anime Mapping DB

**Anime Mapping DB** ist ein eigenständiger Builder und eine veröffentlichte SQLite-Datenbank zur Zuordnung von Anime-IDs zwischen öffentlichen Katalogen und Tracking-Diensten. Es gibt keine Mapping-HTTP-API: Anwendungen laden `mappings.db` bzw. `mappings.db.zst` aus GitHub Releases und lösen IDs lokal mit SQLite auf.

## Highlights

- 31 Provider-Namespaces und 13 Eingabe-Datensätze.
- Nur direkte One-Hop-Auflösung, kein unsicheres transitives Traversieren.
- Evidence-basierte Confidence ohne künstliche Doppelstimmen korrelierter Quellen.
- Kleine Runtime-Datenbank getrennt von der Provenance-Datenbank.
- AnimeAPI nur als GitHub-gehostete Zusatzquelle, nie über dessen REST API.
- Releases enthalten Manifest, Hashes, Provider-Zählungen und Zstandard-Dateien.

## Stand der validierten Datenbank

| Metric | Value |
| --- | ---: |
| Dataset inputs | 13 |
| Provider namespaces | 31 |
| Unique provider/ID nodes | 371,128 |
| Source records | 654,827 |
| Evidence edges | 2,169,089 |
| Runtime edges | 1,111,505 |
| Accepted runtime edges | 1,104,610 |
| Directional conflicts | 19,724 |
| `mappings.db` | ~104.5 MiB |
| `mappings.db.zst` | ~17.9 MiB |

## Datenbanken in `mappings.db`

Alle 31 Namespaces der validierten Build-Version. Varianten wie `tmdb_tv` und `tmdb_movie` sind wegen unterschiedlicher Semantik absichtlich getrennt.

| Namespace | Database / ID | Count |
| --- | --- | ---: |
| `anidb` | AniDB | 16,341 |
| `anilist` | AniList | 22,415 |
| `animecountdown` | AnimeCountdown | 14,711 |
| `animeplanet` | Anime-Planet | 25,126 |
| `anisearch` | aniSearch | 20,042 |
| `ann` | Anime News Network | 12,402 |
| `annict` | Annict | 13,353 |
| `bahamut` | Bahamut Animation Crazy | 783 |
| `hikka` | Hikka | 27,157 |
| `imdb` | IMDb | 7,162 |
| `kaize` | Kaize slug | 23,233 |
| `kaize_id` | Kaize numeric ID | 9,956 |
| `kitsu` | Kitsu | 21,692 |
| `letterboxd_lid` | Letterboxd LID | 1,269 |
| `letterboxd_slug` | Letterboxd slug | 1,269 |
| `letterboxd_uid` | Letterboxd UID | 1,269 |
| `livechart` | LiveChart.me | 12,367 |
| `mal` | MyAnimeList | 28,119 |
| `nautiljon` | Nautiljon slug | 8,979 |
| `nautiljon_id` | Nautiljon numeric ID | 9,002 |
| `notify` | Notify.moe | 16,861 |
| `otakotaku` | Otak Otaku | 3,131 |
| `shikimori` | Shikimori | 27,711 |
| `shoboi` | Shoboi / Syoboi Calendar | 6,525 |
| `silveryasha` | SilverYasha | 5,703 |
| `simkl` | SIMKL | 14,711 |
| `tmdb_movie` | TMDB movie | 3,304 |
| `tmdb_tv` | TMDB TV | 4,465 |
| `trakt` | Trakt title | 6,100 |
| `tvdb` | TVDB series | 4,854 |
| `tvdb_movie` | TVDB movie | 1,116 |

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
| Wikidata / Bahamut | optional, WDQS + lokaler CC0-Bootstrap bei Ausfall |
| rensetsu/db.notify.rensetsu-mirai | optional, GitHub JSON |
| kawaiioverflow/arm | optional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | optional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | optional, GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | optional, GitHub JSON, CC0 |
| nattadasu/animeApi | ergänzend, nur GitHub `database/animeapi.tsv` |

## AnimeAPI-Integration

AnimeAPI wird nicht als zusätzliche unabhängige Stimme gezählt, da es mehrere unserer direkten Quellen selbst aggregiert. Zuerst entsteht der vorläufige Graph aus direkten Quellen. Ein AnimeAPI-Eintrag darf einen fehlenden Ziel-Identifier nur ergänzen, wenn mindestens zwei bereits bekannte Anker eine akzeptierte direkte, konfliktfreie Verbindung besitzen. Bestehende Ziel-IDs erhalten keine zusätzliche korrelierte Stimme. Ungültig markierte Trakt-Zeilen und alle Season-Felder werden ausgeschlossen.

Der Builder lädt ausschließlich `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv`; weder AnimeAPI REST noch Geckyzz noch AnimeAPIs Site-Scraper werden aufgerufen.

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## Lookup-Performance

Reproduzierbar mit `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`. Auf demselben Linux-Host: alte 7-Quellen-Build median 0.418 ms / p95 0.749 ms; neue 13-Dataset-Build **0.403 ms / 0.552 ms**. Eine separate Stichprobe der neuen DB ergab median 0.446 ms / p95 0.551 ms. Dies ist ein Mikrobenchmark, keine Latenzgarantie.

## Runtime und Evidence

`mappings.db` enthält nur Runtime-Tabellen für direkte Lookups und Overrides. `mappings-evidence.db` enthält Datasets, Source Records, Evidence Groups und Provenance. Normale Consumer benötigen die Evidence-Datei nicht.

## Confidence und Konflikte

Eine Edge wird akzeptiert, wenn `max_weight >= 80` oder mindestens zwei unabhängige Evidence Groups zustimmen. Directional Conflicts sperren nur die mehrdeutige Richtung. Der Resolver läuft absichtlich nicht transitiv durch den Graphen.

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Releases und lokale Builds

Jedes Release enthält `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst`, `manifest.json` und `SHA256SUMS`. Automatisierung läuft nach Engine-Änderungen auf `main`, täglich um 03:17 UTC, für `v*`-Tags und manuell. Unveränderte tägliche Source-Fingerprints erzeugen kein Release.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Lizenzen

Projektcode: Apache-2.0. Die kompilierte Datenbank kombiniert Drittanbieter-Daten mit eigenen Lizenzpflichten; AnimeAPI und anime-offline-database sind insbesondere ODbL 1.0 + DbCL 1.0. Siehe `THIRD_PARTY_NOTICES.md`.
