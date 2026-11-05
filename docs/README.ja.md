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

## クイックスタート

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
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

## ドキュメント

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## ライセンスと出典

コードは Apache-2.0 です。生成データには ODbL/DbCL や出典表示義務を含む外部の条件が適用されます。再配布前にライセンス文書を確認してください。 [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
