> **AI 支援プロジェクト:** このプロジェクトは AI の支援を受けて開発されています。

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <strong>日本語</strong> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# Anime Mapping DB

**Anime Mapping DB** は、公開アニメカタログや追跡サービス間の ID を対応付けるための独立したビルダー兼配布用 SQLite データベースです。Mapping 用 HTTP API はありません。利用側は GitHub Releases から `mappings.db` / `mappings.db.zst` を取得し、SQLite でローカルに解決します。

## 特徴

- 31 の provider namespace と 13 の入力 dataset。
- 危険な推移的探索を行わない direct one-hop resolver。
- 相関したソースを独立票として二重計上しない evidence ベースの confidence。
- runtime `mappings.db` と provenance `mappings-evidence.db` を分離。
- AnimeAPI は GitHub 上の補助データのみ利用し、REST API は呼び出さない。
- manifest、hash、provider 件数、Zstandard asset を含む再現可能な release。

## 検証済みビルドの概要

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

## `mappings.db` に含まれるデータベース

検証済みビルドに含まれる 31 namespace です。`tmdb_tv` / `tmdb_movie` のような区別は ID の意味が異なるため意図的に分離されています。

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

## 使用するデータセット

| データセット | 役割 / 取得方法 |
| --- | --- |
| Fribb/anime-lists | 必須の直接ソース、GitHub JSON |
| Kometa-Team/Anime-IDs | 必須の直接ソース、GitHub JSON |
| Anime-Lists/anime-lists | 必須の直接ソース、GitHub XML |
| cplieger/animap | 必須の直接ソース、GitHub Release |
| cedya77/anime-offline-database | 任意、GitHub Release JSONL。旧 Manami 系統のメンテナンス fork |
| anibridge/anibridge-mappings | 任意、GitHub Release |
| Wikidata / Bahamut | 任意、WDQS + 障害時のローカル CC0 bootstrap |
| rensetsu/db.notify.rensetsu-mirai | 任意、GitHub JSON |
| kawaiioverflow/arm | 任意、GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | 任意、GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | 任意、GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | 任意、GitHub JSON、CC0 |
| nattadasu/animeApi | 補助ソース、GitHub `database/animeapi.tsv` のみ |

## AnimeAPI の利用方法

AnimeAPI は既に複数の直接ソースを集約しているため、追加の独立した evidence としては数えません。まず直接ソースだけで provisional graph を作成します。その後 AnimeAPI の行は、既知の anchor が最低 2 個あり、その 2 個の間に accepted direct edge が存在し directional conflict がない場合だけ、不足している ID を追加できます。既存 target ID への相関した重複票は追加しません。`trakt_may_invalid=true` と season 専用フィールドは除外します。

取得するのは `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv` のみです。AnimeAPI REST、Geckyzz API、AnimeAPI の各サイト scraper は呼び出しません。

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## Lookup 性能

再現コマンド: `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`。同一 Linux ホスト・共通 1,200 ID × 3 round では、旧 7-source build が median 0.418 ms / p95 0.749 ms、新 13-dataset build が **0.403 ms / 0.552 ms**。新 DB の別サンプルは median 0.446 ms / p95 0.551 ms でした。これは microbenchmark であり latency 保証ではありません。

## Runtime と evidence

`mappings.db` は lookup と override に必要な runtime table のみを保持します。`mappings-evidence.db` は dataset、source record、evidence group、provenance を保持します。通常の consumer は evidence DB を開く必要がありません。

## Confidence と conflict

Edge は `max_weight >= 80`、または独立した evidence group が 2 つ以上確認した場合に accepted になります。Directional conflict は曖昧な方向だけを抑止します。Resolver はグラフを推移的には探索しません。

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Release とローカル build

各 release には `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst` に加えて、移植しやすいテキスト export `mappings.tsv.zst` と `mappings.jsonl.zst`、`manifest.json`, `SHA256SUMS` が含まれます。テキスト export は directional conflict と manual override を適用した後の、resolver で安全な有向 route を収録します。SQLite は引き続き canonical runtime format です。`main` の engine 変更、毎日 03:17 UTC、`v*` tag、手動実行で build されます。日次チェックで source fingerprint が同じなら新 release は公開されません。

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## ライセンス

プロジェクトコードは Apache-2.0。生成 DB は各種第三者データのライセンス条件を含みます。特に AnimeAPI と anime-offline-database は ODbL 1.0 + DbCL 1.0 です。再配布前に `THIRD_PARTY_NOTICES.md` を確認してください。
