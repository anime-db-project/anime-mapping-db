> **Проект разработан при помощи AI.**

<p align="center">
  <a href="../README.md">English</a> · <strong>Русский</strong> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# anime-mapping-db

[![CI](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml)
[![Releases](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Code license](https://img.shields.io/badge/Code-Apache%202.0-D22128.svg)](../LICENSE)
[![Data license](https://img.shields.io/badge/Data-Upstream%20terms-555555.svg)](../DATA_LICENSE.md)

Воспроизводимая база соответствий идентификаторов аниме между сервисами с сохранением происхождения данных. Предоставляет стабильные ID проекта и компактный SQLite для других приложений.

## Возможности

- Стабильные идентификаторы `amdb:<anchor_id>`, сохраняющиеся между пересборками.
- Сопоставления разных сервисов с оценкой достоверности и учётом происхождения данных.
- Безопасный прямой поиск без произвольного обхода графа и догадок при конфликтах.
- Разделение компактной runtime-базы и подробной базы доказательств.
- Версионированные GitHub Releases с базами, текстовыми экспортами, манифестами и контрольными суммами.

## Источники данных

Сборщик объединяет 18 входных наборов: прямые базы сопоставлений и проверяемые дополнительные каталоги. Дополнительные записи не создают идентичность без независимого подтверждения; точные входные данные и лицензии указаны в манифесте релиза.

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

`amdb:<anchor_id>` — стабильный ID тайтла. Внешние ID связаны с ним подтверждёнными соответствиями, а внутренний `entity_id` действителен лишь в рамках сборки. Неоднозначные маршруты не выбираются автоматически. [Identity contract](../docs/IDENTITY.md).

## Быстрый старт

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Базы данных и релизы

Для использования скачайте `mappings.db.zst` и `manifest.json` из последнего релиза. `mappings-evidence.db.zst` содержит происхождение связей, `mappings.tsv.zst` и `mappings.jsonl.zst` — переносимые экспорты. Плановые релизы публикуются при изменении исходных данных.

- [Latest release](https://github.com/anime-db-project/anime-mapping-db/releases/latest)
- [Runtime database (zstd)](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db.zst)
- [Release manifest](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json)

```text
data/mappings/mappings.db
data/mappings/mappings-evidence.db
```

## Документация

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## Лицензия и атрибуция

Код — Apache-2.0. Скомпилированная база включает сторонние данные с отдельными условиями, в том числе ODbL/DbCL и требованиями атрибуции. Перед распространением прочитайте оба документа о лицензиях. [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
