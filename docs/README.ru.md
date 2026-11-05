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

## Идентичность и правила сопоставления

Anime Mapping DB выдаёт собственный стабильный ID тайтла `amdb:<anchor_id>`, независимый от MAL, AniList и других сервисов. Его можно сохранять между пересборками. В отличие от него `entity_id` — плотный внутренний ключ SQLite, который действителен только внутри конкретного файла базы и не подходит для публичного обмена.

Внешние ID представлены узлами `(provider, external_id)`. Проверенные узлы могут составлять одну сущность проекта, однако два различных ID одного провайдера не объединяются в один тайтл. Неоднозначные соответствия и конфликты остаются неразрешёнными, вместо того чтобы выбирать наиболее похожий вариант.

При пересборке старые anchors сохраняются для неизменных или дополненных сущностей. Подтверждённое слияние оставляет стабильный anchor с редиректом от прежнего, а разделение получает новые ID без повторного использования завершённых идентификаторов. Это важно для других баз, которые ссылаются на тайтл независимо от версии mappings.db.

```text
(provider, external_id) ──accepted edge── (provider, external_id)
          \                         /
           \── stable amdb:<anchor_id> ──/
                   │
              anchor redirects
```

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

## Обработка источников и происхождение данных

Сборщик получает открытые bulk-наборы и фиксирует доказательства происхождения записей до формирования runtime-графа. Каждая запись связана с источником и группой доказательств. Зеркала и производные наборы не считаются автоматически независимыми подтверждениями.

Прямые источники формируют связи на основе evidence. Дополнительные каталоги AnimeAPI, AnimeAggregations, связанные с AnimeThemes ID и Wikidata multi-ID только обогащают уже известные сущности, проверяя как минимум два существующих непротиворечивых anchor. Это защищает от ошибочного объединения сезона, адаптации и всей франшизы.

Адреса и хеши источников, а также версии фиксируются в манифесте релиза. Актуальная конфигурация входных данных находится в `anime_mapping_db/config.py`. Во время разрешения ID не требуется сторонний веб-API: приложение читает локальную SQLite.

```text
1. Загрузка открытых наборов данных
2. Группировка доказательств по происхождению
3. Оценка и проверка прямых связей
4. Разрешение конфликтов и создание стабильных ID
5. Аудит, компактирование и упаковка релиза
```

## Устройство баз данных

Компактная `mappings.db` содержит узлы resolver, связи со статусами, направленные конфликты, стабильные сущности и редиректы, а также ручные исключения. Структура оптимизирована под прямой индексированный поиск, а не произвольный рекурсивный обход графа.

Отдельная `mappings-evidence.db` хранит наборы данных, записи источников, группы доказательств и исходные связи, обосновывающие решения. Приложению, которому нужно лишь сопоставлять ID, достаточно runtime-базы. Обе базы проходят проверки перед публикацией.

```text
mappings.db
  metadata · nodes · edges · conflicts
  entities · entity_nodes · anchor_redirects
  mapping_overrides · mapping_override_history

mappings-evidence.db
  metadata · datasets · nodes · evidence_groups
  records · record_nodes · edge_evidence (view)
```

## Быстрый старт

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Использование resolver

Поиск принимает namespace источника и внешний ID и возвращает только однозначные, принятые прямые соответствия. Одинаковое число в MAL и AniList ничего не доказывает без подтверждённой связи.

Можно использовать Python resolver или SQL-запросы к `mappings.db`. Для стабильных ID служат сущности и таблицы anchors; не заменяйте безопасный прямой resolver неограниченным рекурсивным обходом.

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

## Достоверность и конфликты

Достоверность учитывает максимальный вес источника, число независимых групп доказательств и дополнительные подтверждения. Достаточно сильный источник либо две независимые группы могут подтвердить ребро. Слабые варианты остаются кандидатами и не возвращаются обычным resolver.

Конфликты направленные: маршрут `A → B` может быть неоднозначным, даже если обратное направление безопасно. Ручные исключения разрешают принять или отклонить конкретную связь с сохранением истории. Изменять такие правила следует осторожно: ими пользуются другие приложения.

```text
confidence = min(100,
    max_weight
    + 8 × (distinct_evidence_groups - 1)
    + 2 × min(5, evidence_count - distinct_evidence_groups)
)

accepted: max_weight >= 80 OR distinct_evidence_groups >= 2
candidate: unconfirmed relationships
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

## Релизы и подключение к приложениям

Релиз включает runtime- и evidence-базы, zstd-архивы, переносимые текстовые маршруты, машиночитаемый манифест и SHA-256. Текстовые экспорты содержат направленные разрешённые соответствия после исключения неоднозначностей, а не сырые рёбра графа.

`manifest.json` — источник актуальных сведений о схемах, размерах, версиях источников, хешах, количестве записей и fingerprint. Эти значения меняются между сборками, поэтому постоянные цифры в README быстро устаревают. Проверяйте хеши перед использованием скачанных файлов.

Публикация запускается при изменениях проекта, по расписанию, по тегу или вручную. Плановая проверка может не создавать новый релиз, если входные данные не изменились. Стандартные архивы исходников GitHub предоставляет самостоятельно.

| Файл | Назначение |
| --- | --- |
| `mappings.db` | Компактная runtime-база SQLite |
| `mappings.db.zst` | Сжатая база для приложений |
| `mappings-evidence.db.zst` | Сжатая база доказательств |
| `mappings.tsv.zst` | Переносимые направленные TSV-маршруты |
| `mappings.jsonl.zst` | Переносимые маршруты JSON Lines |
| `manifest.json` | Версии, источники, статистика и хеши |
| `SHA256SUMS` | Контрольные суммы SHA-256 |

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

`source_provider` — Исходный провайдер; `source_id` — Исходный ID; `target_provider` — Целевой провайдер; `target_id` — Целевой ID; `confidence` — Достоверность; `evidence_count` — Количество evidence-записей; `evidence_group_count` — Независимые группы; `max_weight` — Наибольший вес источника; `origin` — Происхождение маршрута

## Проверки и разработка

CI проверяет тесты и форматирование, целостность SQLite, идентификаторы и редиректы, модель confidence, конфликты, текстовые экспорты и архивы. Сборка должна содержать подтверждённые связи без нарушения правил идентичности. Новые импортеры следует сопровождать тестами.

```bash
python -m pip install -e .
python -m pip install pytest ruff
python -m pytest -q
python -m ruff check .
```

[Контракт идентичности](../docs/IDENTITY.md)

## Документация

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## Лицензия и атрибуция

Код — Apache-2.0. Скомпилированная база включает сторонние данные с отдельными условиями, в том числе ODbL/DbCL и требованиями атрибуции. Перед распространением прочитайте оба документа о лицензиях. [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
