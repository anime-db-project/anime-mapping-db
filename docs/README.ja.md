> **AI 支援プロジェクト:** AI の支援を受けて開発されています。

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <strong>日本語</strong> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# anime-mapping-db

[![CI](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml)
[![Releases](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Code license](https://img.shields.io/badge/Code-Apache%202.0-D22128.svg)](../LICENSE)
[![Data license](https://img.shields.io/badge/Data-Upstream%20terms-555555.svg)](../DATA_LICENSE.md)

アニメ作品のサービス間 ID 対応を、出典とともに再現可能な形でまとめるデータベースです。安定した独自 ID と軽量な SQLite 検索を提供します。

## 主な機能

- ビルドをまたいで維持される `amdb:<anchor_id>`。
- 根拠と信頼度を記録した複数サービスの ID 対応。
- 曖昧な関係を無理につながない直接参照型リゾルバー。
- 実行用の軽量 DB と検証・出典用 DB の分離。
- 圧縮 DB、テキスト出力、マニフェスト、チェックサムを含む GitHub Releases。

## 作品 ID と対応規則

Anime Mapping DB は外部サービスに依存しない安定した作品 ID `amdb:<anchor_id>` を提供します。これは再ビルド後も保持できます。一方、SQLite の `entity_id` はビルドごとの内部キーであり、公開 ID として保存してはいけません。

外部 ID は `(provider, external_id)` のノードです。確認できたノードは同一作品に属しますが、同一プロバイダーの異なる二つの ID を一つに潰しません。根拠が曖昧な場合や方向付き競合がある場合は推測せず未解決のままにします。

再ビルドでは同じ作品の anchor を保持します。正当な統合では代表 ID とリダイレクトを残し、分割では新しい ID を割り当てます。廃止した ID を無関係な作品に再利用しません。関連データベースの参照の安定性を守るためです。

```text
(provider, external_id) ──accepted edge── (provider, external_id)
          \                         /
           \── stable amdb:<anchor_id> ──/
                   │
              anchor redirects
```

## データソース

ビルダーは直接対応表と検証済み補助カタログを含む 18 種類の入力を統合します。補助データだけで新しい作品同一性を作ることはありません。入力と利用条件はリリースのマニフェストに記録されます。

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

`amdb:<anchor_id>` は安定した作品 ID です。外部 ID は根拠のある別名として扱い、内部 `entity_id` はビルドごとの値です。競合する対応先は自動選択しません。 [Identity contract](../docs/IDENTITY.md).

## 入力データと出典

公開バルクデータを読み込み、実行用の対応グラフを作る前に出典情報を記録します。各レコードに元データと独立した証拠グループを結び付け、ミラーを別々の証拠として数えません。

直接ソースは作品間の対応を裏付けます。AnimeAPI、AnimeAggregations、AnimeThemes の参照データ、Wikidata の複数 ID は、二つ以上の矛盾しない既存 anchor に照合した場合だけ補完を行います。作品とシーズンや派生作品の混同を防ぎます。

元 URL、ハッシュ、バージョンはリリースマニフェストに記録されます。入力の設定は `anime_mapping_db/config.py` にあります。配布 SQLite の検索時に外部 REST API は必要ありません。

```text
1. 公開データの取得
2. 独立した出典ごとの証拠グループ化
3. 直接リンクの評価と検証
4. 競合判定と安定した作品 ID
5. 監査、軽量化、リリース作成
```

## データベース設計

軽量な `mappings.db` は ID ノード、対応エッジ、方向付き競合、安定した作品、リダイレクトと手動修正を持ちます。無制限のグラフ探索ではなく、直接のインデックス検索向けです。

`mappings-evidence.db` は入力データ、観測レコード、独立性グループ、対応の根拠を保存します。通常の ID 検索アプリには実行用 DB だけで十分です。両方とも検査後に公開します。

```text
mappings.db
  metadata · nodes · edges · conflicts
  entities · entity_nodes · anchor_redirects
  mapping_overrides · mapping_override_history

mappings-evidence.db
  metadata · datasets · nodes · evidence_groups
  records · record_nodes · edge_evidence (view)
```

## クイックスタート

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## リゾルバーの利用

照会はプロバイダー名と外部 ID を受け取り、確認済みで曖昧でない直接の対応先のみを返します。MAL と AniList の同じ数値は、それだけでは同一作品を意味しません。

Python の MappingResolver または SQLite を利用できます。安定 ID は entity/anchor テーブルで管理されます。安全な直接照会を再帰的なグラフ探索に置き換えないでください。

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

## 信頼度と競合

信頼度はソースの最大重み、独立した証拠グループ数、補助記録から計算します。十分強い一つのソースか二つの独立グループがあれば受理できます。弱いリンクは候補として残ります。

競合は方向付きです。`A → B` が曖昧でも逆方向は安全な場合があります。手動上書きは採用・拒否を監査履歴とともに保持します。他アプリへの影響を考慮して変更してください。

```text
confidence = min(100,
    max_weight
    + 8 × (distinct_evidence_groups - 1)
    + 2 × min(5, evidence_count - distinct_evidence_groups)
)

accepted: max_weight >= 80 OR distinct_evidence_groups >= 2
candidate: unconfirmed relationships
```

## データベースとリリース

アプリから使う場合は最新リリースの `mappings.db.zst` と `manifest.json` を取得してください。`mappings-evidence.db.zst` は出典、`mappings.tsv.zst` と `mappings.jsonl.zst` は移植用の出力です。定期リリースはソース変更時に公開されます。

- [Latest release](https://github.com/anime-db-project/anime-mapping-db/releases/latest)
- [Runtime database (zstd)](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db.zst)
- [Release manifest](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json)

```text
data/mappings/mappings.db
data/mappings/mappings-evidence.db
```

## リリースと導入

リリースには実行用・証拠用 SQLite、zstd 圧縮版、移植可能なテキスト出力、マニフェスト、SHA-256 が含まれます。テキスト出力は矛盾を除いた方向付きルートであり、未加工のグラフではありません。

`manifest.json` がスキーマ、生成サイズ、元データのバージョン、ハッシュ、件数、fingerprint の基準です。値はビルドごとに変わるため、README に固定の件数を記載しません。ダウンロード後はハッシュを検証してください。

プロジェクトの変更、定期確認、タグ、手動実行でリリースを作成できます。元データに変更がない定期確認では公開を省略できます。GitHub 標準のソースアーカイブを重複添付しません。

| ファイル | 用途 |
| --- | --- |
| `mappings.db` | 実行用の軽量 SQLite |
| `mappings.db.zst` | アプリ向け圧縮実行 DB |
| `mappings-evidence.db.zst` | 出典・証拠 DB の圧縮版 |
| `mappings.tsv.zst` | 安全な方向付き TSV |
| `mappings.jsonl.zst` | 安全な方向付き JSON Lines |
| `manifest.json` | スキーマ、元データ、件数、ハッシュ |
| `SHA256SUMS` | SHA-256 チェックサム |

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

`source_provider` — 元プロバイダー; `source_id` — 元 ID; `target_provider` — 先プロバイダー; `target_id` — 先 ID; `confidence` — 信頼度; `evidence_count` — 証拠レコード数; `evidence_group_count` — 独立グループ数; `max_weight` — 最大重み; `origin` — ルートの出典

## 検証と開発

CI はテスト、書式、SQLite の整合性、anchor とリダイレクト、信頼度、競合、出力、パッケージを確認します。新しいインポーターには対応するテストも追加してください。

```bash
python -m pip install -e .
python -m pip install pytest ruff
python -m pytest -q
python -m ruff check .
```

[ID の仕様](../docs/IDENTITY.md)

## ドキュメント

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## ライセンスと出典

コードは Apache-2.0 です。生成データには ODbL/DbCL や出典表示義務を含む外部の条件が適用されます。再配布前にライセンス文書を確認してください。 [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
