> **Проект с поддержкой AI:** проект разработан при помощи AI.

<p align="center">
  <a href="../README.md">English</a> · <strong>Русский</strong> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# Anime Mapping DB

**Anime Mapping DB** — самостоятельный сборщик и распространяемая SQLite-база для сопоставления ID аниме между публичными каталогами и трекерами. Здесь нет mapping HTTP API: приложение скачивает `mappings.db`/`mappings.db.zst` из GitHub Releases и делает локальные SQLite lookup.

## Главное

- 55 namespace провайдеров и 18 входных datasets.
- Только direct one-hop resolution — без опасного transitive обхода.
- Confidence учитывает независимые evidence groups и не удваивает коррелированные источники.
- Runtime `mappings.db` отделён от provenance `mappings-evidence.db`.
- AnimeAPI используется только как GitHub-hosted supplemental dataset, без обращения к его REST API.
- Release содержит manifest, hashes, provider counts и Zstandard assets.

## Снимок проверенной сборки

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

## Какие базы есть в `mappings.db`

Ниже перечислены все 55 namespace и количество ID в проверенной сборке. Варианты вроде `tmdb_tv`/`tmdb_movie` разделены намеренно из-за разной семантики.

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

## Какие datasets используются

| Набор | Роль / доступ |
| --- | --- |
| Fribb/anime-lists | обязательный прямой источник, GitHub JSON |
| Kometa-Team/Anime-IDs | обязательный прямой источник, GitHub JSON |
| Anime-Lists/anime-lists | обязательный прямой источник, GitHub XML |
| cplieger/animap | обязательный прямой источник, GitHub Release |
| cedya77/anime-offline-database | optional, GitHub Release JSONL; поддерживаемый fork старого Manami lineage |
| anibridge/anibridge-mappings | optional, GitHub Release |
| Wikidata / Bahamut | optional, QLever bulk SPARQL → WDQS fallback → локальный CC0 bootstrap |
| rensetsu/db.notify.rensetsu-mirai | optional, GitHub JSON |
| kawaiioverflow/arm | optional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | optional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | optional, GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | optional, GitHub JSON, CC0 |
| rensetsu/db.rensetsu.public-dump AnimeThemes | supplemental, GitHub JSON, CC0 |
| anime-and-manga/lists | optional corroborating, GitHub JSON |
| shinkro/community-mapping | optional corroborating, GitHub JSON; только title-level TVDB/TMDB |
| notseteve/AnimeAggregations | supplemental, GitHub JSON, two-anchor validation |
| Wikidata multi-ID | supplemental, QLever bulk + WDQS fallback, two-anchor validation |
| nattadasu/animeApi | supplemental, только GitHub `database/animeapi.tsv` |

## Anchor-validated supplemental-источники

AnimeAggregations, Wikidata multi-ID и AnimeAPI обрабатываются только после построения provisional graph из прямых источников. Чтобы добавить отсутствующий ID, запись должна содержать минимум два уже известных точных anchor-ID, между которыми существует accepted direct edge без directional conflict. Поэтому эти широкие агрегаты не могут сами создать новую идентичность тайтла с нуля.

AnimeAggregations берётся только готовым bulk JSON из GitHub; VNDB, обычные website/social links и другие неэквивалентные отношения исключаются. Wikidata забирается одним bulk SPARQL-запросом через QLever с WDQS fallback. Shinkro является прямым evidence, но из него импортируются только title-level MAL↔TVDB series и MAL↔TMDB movie; season/episode routing не попадает в граф.

## Как используется AnimeAPI

AnimeAPI не считается ещё одним независимым голосом, потому что сам агрегирует часть тех же источников. Сначала прямые источники строят provisional graph. Затем строка AnimeAPI может добавить отсутствующий ID только если в ней есть минимум два уже известных anchor-ID, между которыми уже существует accepted direct edge и нет directional conflict. AnimeAPI не создаёт evidence между самими anchors и не даёт повторный голос уже существующему target ID. `trakt_may_invalid=true` пропускается, а все season-only поля полностью исключены.

Скачивается только `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv`. Внешний AnimeAPI REST, Geckyzz API и собственные site scrapers AnimeAPI наш builder не вызывает.

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## Производительность lookup

Воспроизводимый тест: `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`. На одном и том же Linux-хосте для 1 200 общих ID × 3 раунда старая 7-source база показала median 0.418 ms / p95 0.749 ms, новая 18-dataset/55-provider база — **0.380 ms / 0.516 ms**. Для 18-dataset сборки: mean 0.394 ms, p99 0.575 ms. Это микробенчмарк, а не гарантия latency.

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
