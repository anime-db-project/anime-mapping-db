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

<!-- BEGIN AUTO-GENERATED DATABASE STATS -->
## Статистика базы данных

**≈35,000 уникальных аниме-тайтлов**

**34,853 проверенных стабильных AMDB ID.** Это масштаб каталога идентичностей, а не полное покрытие каждого источника.

| Показатель | Значение |
| --- | ---: |
| Стабильные AMDB-тайтлы | **34,853** |
| Пространства внешних ID | **55** |
| Наборы источников | **18** |
| Подтверждённые связи ID | **1,225,745** |
| Безопасные направленные маршруты | **2,386,537** |
| Направленные конфликты | **22,021** |
| Записи источников | **803,716** |
| Evidence-связи | **2,346,750** |
| Размер SQLite | **79.7 MiB** |
| Размер сжатой SQLite | **16.5 MiB** |

### Скорость локальных запросов

| Показатель | Значение |
| --- | ---: |
| Медианная задержка | **0.473 ms** |
| Средняя задержка | **0.476 ms** |
| Задержка p95 | **0.519 ms** |
| Задержка p99 | **0.570 ms** |
| Последовательные запросы/с | **2,093** |
| Получение источников и сборка БД | **99 s** |

Последовательные запросы MappingResolver к релизной SQLite с прогретым кэшем, Linux / Python 3.12. 300 ID × 2 повторения. Это не задержка сетевых API.

Снимок релиза: **2026-11-05**, [v2026.11.05.25](https://github.com/anime-db-project/anime-mapping-db/releases/tag/v2026.11.05.25). [Актуальный манифест](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json).

<!-- END AUTO-GENERATED DATABASE STATS -->

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

## Способы использования базы

Артефакты релиза — обычные файлы: для локального поиска ID не требуется запускать сборщик или получать API-ключ. Выберите подходящий способ:

- **Интеграция через Python.** Используйте `MappingResolver` для безопасного сопоставления ID в Telegram-боте, сайте, парсере или медиакаталоге.
- **Прямые запросы SQLite.** Работайте через SQLite в Python, Rust, Go, Node.js и других языках без внешнего API.
- **Импорт и аналитика.** Загружайте `mappings.tsv.zst` или `mappings.jsonl.zst` в другие базы данных, поисковые индексы и ETL-пайплайны.
- **Общий ID между приложениями.** Сохраняйте `amdb:<anchor_id>` в собственном каталоге и связывайте записи с другими проектами по этому ID.
- **Аудит и проверка.** Подключайте отдельную evidence-базу, чтобы изучить происхождение сомнительных сопоставлений.

Скачайте готовую SQLite из релиза — пересобирать проект не требуется:

```bash
curl -fL -o mappings.db \
  https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db
```

Для Python resolver установите пакет из репозитория (`python -m pip install -e .`):

```python
from anime_mapping_db.resolver import MappingResolver

resolver = MappingResolver("mappings.db")
if resolver.available():
    matches = resolver.resolve({"mal": "1"})
    print(matches)  # Verified, direct and conflict-safe provider IDs
```

Пример извлечения стабильного AMDB ID и связанных внешних ID через стандартный модуль Python `sqlite3`:

```python
import sqlite3

with sqlite3.connect("file:mappings.db?mode=ro", uri=True) as db:
    rows = db.execute("""
        SELECT entity.anchor_id, other.provider, other.external_id
        FROM nodes AS seed
        JOIN entity_nodes AS seed_member ON seed_member.node_id = seed.id
        JOIN entities AS entity ON entity.entity_id = seed_member.entity_id
        JOIN entity_nodes AS member ON member.entity_id = entity.entity_id
        JOIN nodes AS other ON other.id = member.node_id
        WHERE seed.provider = ? AND seed.external_id = ?
        ORDER BY other.provider, other.external_id
    """, ("mal", "1")).fetchall()

for anchor_id, provider, external_id in rows:
    print(f"amdb:{anchor_id}", provider, external_id)
```

Второй пример показывает **состав AMDB-сущности**, а не строго прямые маршруты resolver. Для прямых соответствий с фильтрацией конфликтов используйте `MappingResolver.resolve()`. Сохраняйте `anchor_id`, а не временный `entity_id`.

Для обработки текстовых маршрутов скачайте TSV или JSONL и распакуйте с помощью `zstd`. Формат полей описан в разделе релизов.

```bash
curl -fL -o mappings.tsv.zst \
  https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.tsv.zst
zstd -dc mappings.tsv.zst | head -n 5
```

При совместном использовании с базой таймкодов фиксируйте совместимые версии релизов и проверяйте манифесты и SHA-256.

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
