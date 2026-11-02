> **AI 支援プロジェクト:** このプロジェクトは AI の支援を受けて開発されています。

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <strong>日本語</strong> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# Anime Mapping DB

**Anime Mapping DB** は、公開アニメカタログや追跡サービス間の ID を対応付けるための独立したビルダー兼配布用 SQLite データベースです。Mapping 用 HTTP API はありません。利用側は GitHub Releases から `mappings.db` / `mappings.db.zst` を取得し、SQLite でローカルに解決します。

## 特徴

- 55 の provider namespace と 18 の入力 dataset。
- 安定した公開プロジェクト ID は `amdb:<anchor_id>`。build-local の `entity_id` は外部キーとして使用しません。
- 公開する runtime/evidence DB は read-optimized な `compact-v1` layout を使用します。
- 危険な推移的探索を行わない direct one-hop resolver。
- 相関したソースを独立票として二重計上しない evidence ベースの confidence。
- runtime `mappings.db` と provenance `mappings-evidence.db` を分離。
- AnimeAPI は GitHub 上の補助データのみ利用し、REST API は呼び出さない。
- manifest、hash、provider 件数、Zstandard asset を含む再現可能な release。

## 検証済みビルドの概要

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

## `mappings.db` に含まれるデータベース

検証済みビルドに含まれる 55 namespace です。`tmdb_tv` / `tmdb_movie` のような区別は ID の意味が異なるため意図的に分離されています。

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

## 使用するデータセット

| データセット | 役割 / 取得方法 |
| --- | --- |
| Fribb/anime-lists | 必須の直接ソース、GitHub JSON |
| Kometa-Team/Anime-IDs | 必須の直接ソース、GitHub JSON |
| Anime-Lists/anime-lists | 必須の直接ソース、GitHub XML |
| cplieger/animap | 必須の直接ソース、GitHub Release |
| cedya77/anime-offline-database | 任意、GitHub Release JSONL。旧 Manami 系統のメンテナンス fork |
| anibridge/anibridge-mappings | 任意、GitHub Release |
| Wikidata / Bahamut | 任意、QLever bulk SPARQL → WDQS fallback → ローカル CC0 bootstrap |
| rensetsu/db.notify.rensetsu-mirai | 任意、GitHub JSON |
| kawaiioverflow/arm | 任意、GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | 任意、GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | 任意、GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | 任意、GitHub JSON、CC0 |
| rensetsu/db.rensetsu.public-dump AnimeThemes | supplemental, GitHub JSON, CC0 |
| anime-and-manga/lists | optional corroborating, GitHub JSON |
| shinkro/community-mapping | optional corroborating, GitHub JSON; title-level TVDB/TMDB only |
| notseteve/AnimeAggregations | supplemental, GitHub JSON, two-anchor validation |
| Wikidata multi-ID | supplemental, QLever bulk + WDQS fallback, two-anchor validation |
| nattadasu/animeApi | 補助ソース、GitHub `database/animeapi.tsv` のみ |

## Anchor 検証付き supplemental source

AnimeAggregations、Wikidata multi-ID、AnimeAPI は、direct source から provisional graph を構築した後にだけ処理します。不足 ID を追加するには、既知の正確な anchor ID が最低 2 個あり、その間に accepted direct edge が存在し directional conflict がないことが必要です。そのため supplemental source だけで新しい title identity を作ることはできません。

AnimeAggregations は GitHub の bulk JSON のみを読み込み、VNDB や一般的な website/social link は除外します。Wikidata は QLever への 1 回の bulk SPARQL query で取得し、WDQS を fallback にします。Shinkro からは title-level の MAL↔TVDB series と MAL↔TMDB movie のみを取り込み、season/episode routing は graph に入れません。

## AnimeAPI の利用方法

AnimeAPI は既に複数の直接ソースを集約しているため、追加の独立した evidence としては数えません。まず直接ソースだけで provisional graph を作成します。その後 AnimeAPI の行は、既知の anchor が最低 2 個あり、その 2 個の間に accepted direct edge が存在し directional conflict がない場合だけ、不足している ID を追加できます。既存 target ID への相関した重複票は追加しません。`trakt_may_invalid=true` と season 専用フィールドは除外します。

取得するのは `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv` のみです。AnimeAPI REST、Geckyzz API、AnimeAPI の各サイト scraper は呼び出しません。

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## プロジェクト ID

Anime Mapping DB は 2 種類の ID を明確に分離します。`entity_id` は 1 個の `mappings.db` 内だけで有効な密な SQLite キーで、再 build で番号が変わる可能性があります。永続化・外部交換には使いません。`anchor_id` は安定した公開プロジェクト ID で、外部表現は `amdb:<integer>`（例: `amdb:18472`）です。

`mappings.db` の `entities`, `entity_nodes`, `anchor_redirects` がこの層を構成します。具体的な `(provider, external_id)` は引き続き `nodes` が所有します。merge では古い anchor を redirect し、split では最大 overlap の component が以前の anchor を維持します。retired anchor は別 title に再利用しません。詳細は [`IDENTITY.md`](IDENTITY.md) を参照してください。

## Lookup 性能

再現コマンド: `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`。同一 Linux ホスト・共通 1,200 ID × 3 round では、旧 7-source build が median 0.418 ms / p95 0.749 ms、新 18-dataset / 55-provider build が **0.354 ms / 0.497 ms**。18-dataset build では mean 0.378 ms / p99 0.655 ms でした。これは microbenchmark であり latency 保証ではありません。

## Runtime と evidence

`mappings.db` は compact-v1 layout を使用し、`metadata`, `nodes`, `edges`, `conflicts`, `entities`, `entity_nodes`, `anchor_redirects` と override table を保持します。forward lookup は `edges(a_node,b_node)` の primary key、reverse accepted lookup は 1 個の partial index を使います。`mappings-evidence.db` は繰り返し関係を `record_nodes` に正規化し、従来の `edge_evidence` は read-only compatibility view として維持します。通常の consumer は evidence DB を開く必要がありません。

## Confidence と conflict

Edge は `max_weight >= 80`、または独立した evidence group が 2 つ以上確認した場合に accepted になります。Directional conflict は曖昧な方向だけを抑止します。Resolver はグラフを推移的には探索しません。

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Release とローカル build

各 release には `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst`, `mappings.tsv.zst`, `mappings.jsonl.zst`, `manifest.json`, `SHA256SUMS` に加え、`zz-anime-mapping-db-<tag>-source.zip`, `.tar.zst`, `.7z` の 3 種類の project source archive が含まれます。archive は release commit の tracked Git tree から生成されます。`zz-` は asset 一覧で最後に置くための名前だけで、archive 内の root は通常の `anime-mapping-db-<tag>/` です。3 archive の SHA-256 も `SHA256SUMS` に含まれます。日次 build は source fingerprint が変わらない限り新 release を公開しません。

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## ライセンス

プロジェクトコードは Apache-2.0。生成 DB は各種第三者データのライセンス条件を含みます。特に AnimeAPI と anime-offline-database は ODbL 1.0 + DbCL 1.0 です。再配布前に `THIRD_PARTY_NOTICES.md` を確認してください。
