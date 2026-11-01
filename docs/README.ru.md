> **Проект с поддержкой AI:** проект разработан при помощи AI.

<p align="center">
  <a href="../README.md">English</a> · <strong>Русский</strong> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# Anime Mapping DB

**Anime Mapping DB** — самостоятельный сборщик и распространяемая SQLite-база для сопоставления ID аниме между публичными каталогами и трекерами. Здесь нет mapping HTTP API: приложение скачивает `mappings.db`/`mappings.db.zst` из GitHub Releases и делает локальные SQLite lookup.

## Главное

- 31 namespace провайдеров и 13 входных datasets.
- Только direct one-hop resolution — без опасного transitive обхода.
- Confidence учитывает независимые evidence groups и не удваивает коррелированные источники.
- Runtime `mappings.db` отделён от provenance `mappings-evidence.db`.
- AnimeAPI используется только как GitHub-hosted supplemental dataset, без обращения к его REST API.
- Release содержит manifest, hashes, provider counts и Zstandard assets.

## Снимок проверенной сборки

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

## Какие базы есть в `mappings.db`

Ниже перечислены все 31 namespace и количество ID в проверенной сборке. Варианты вроде `tmdb_tv`/`tmdb_movie` разделены намеренно из-за разной семантики.

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

## Какие datasets используются

| Набор | Роль / доступ |
| --- | --- |
| Fribb/anime-lists | обязательный прямой источник, GitHub JSON |
| Kometa-Team/Anime-IDs | обязательный прямой источник, GitHub JSON |
| Anime-Lists/anime-lists | обязательный прямой источник, GitHub XML |
| cplieger/animap | обязательный прямой источник, GitHub Release |
| cedya77/anime-offline-database | optional, GitHub Release JSONL; поддерживаемый fork старого Manami lineage |
| anibridge/anibridge-mappings | optional, GitHub Release |
| Wikidata / Bahamut | optional, WDQS + локальный CC0 bootstrap при сбое |
| rensetsu/db.notify.rensetsu-mirai | optional, GitHub JSON |
| kawaiioverflow/arm | optional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | optional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | optional, GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | optional, GitHub JSON, CC0 |
| nattadasu/animeApi | supplemental, только GitHub `database/animeapi.tsv` |

## Как используется AnimeAPI

AnimeAPI не считается ещё одним независимым голосом, потому что сам агрегирует часть тех же источников. Сначала прямые источники строят provisional graph. Затем строка AnimeAPI может добавить отсутствующий ID только если в ней есть минимум два уже известных anchor-ID, между которыми уже существует accepted direct edge и нет directional conflict. AnimeAPI не создаёт evidence между самими anchors и не даёт повторный голос уже существующему target ID. `trakt_may_invalid=true` пропускается, а все season-only поля полностью исключены.

Скачивается только `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv`. Внешний AnimeAPI REST, Geckyzz API и собственные site scrapers AnimeAPI наш builder не вызывает.

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## Производительность lookup

Воспроизводимый тест: `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`. На одном и том же Linux-хосте для 1 200 общих ID × 3 раунда старая 7-source база показала median 0.418 ms / p95 0.749 ms, новая 13-dataset база — **0.403 ms / 0.552 ms**. Отдельная выборка по новой базе: median 0.446 ms, p95 0.551 ms. Это микробенчмарк, а не гарантия latency.

## Runtime и evidence

`mappings.db` содержит `metadata`, `nodes`, `edges`, `conflicts`, `mapping_overrides` и history overrides. `mappings-evidence.db` хранит `datasets`, source records, evidence groups и `edge_evidence`. Обычному consumer evidence-файл не нужен.

## Confidence и conflicts

Edge принимается, если `max_weight >= 80` либо связь подтверждена минимум двумя независимыми evidence groups. Directional conflicts блокируют только неоднозначное направление source → target-provider. Resolver намеренно не ходит транзитивно по графу.

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Releases и локальная сборка

Release включает `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst`, а также переносимые текстовые экспорты `mappings.tsv.zst` и `mappings.jsonl.zst`, плюс `manifest.json` и `SHA256SUMS`. Текстовые файлы содержат направленные безопасные маршруты resolver после применения directional conflicts и manual overrides; SQLite остаётся каноническим runtime-форматом. Автоматическая сборка идёт после изменений mapping-engine в `main`, ежедневно в 03:17 UTC, по тегам `v*` и вручную. Ежедневный запуск не публикует новый release, если source fingerprint не изменился.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Лицензии

Код проекта — Apache-2.0. Скомпилированная база включает данные с собственными лицензиями; в частности AnimeAPI и anime-offline-database используют ODbL 1.0 + DbCL 1.0. Перед распространением производной базы см. `THIRD_PARTY_NOTICES.md`.
