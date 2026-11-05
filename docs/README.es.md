> **Proyecto desarrollado con ayuda de IA.**

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <strong>Español</strong> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# anime-mapping-db

[![CI](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml)
[![Releases](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Code license](https://img.shields.io/badge/Code-Apache%202.0-D22128.svg)](../LICENSE)
[![Data license](https://img.shields.io/badge/Data-Upstream%20terms-555555.svg)](../DATA_LICENSE.md)

Base reproducible de correspondencias entre identificadores de anime de distintos servicios, con trazabilidad. Ofrece IDs estables propios y consultas SQLite compactas.

## Funciones

- IDs `amdb:<anchor_id>` estables entre compilaciones.
- Correspondencias con evidencia, confianza y resolución prudente de conflictos.
- Resolución directa sin recorridos arbitrarios del grafo.
- Bases separadas para ejecución y evidencias detalladas.
- Versiones con bases comprimidas, exportaciones de texto, manifiestos y sumas SHA-256.

## Fuentes de datos

El generador combina 18 entradas entre datasets directos y catálogos complementarios validados. Los datos complementarios no establecen identidades nuevas sin confirmación independiente. Las fuentes y licencias se documentan en el manifiesto.

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

`amdb:<anchor_id>` identifica un título de forma estable. Los IDs externos son alias respaldados por evidencia; el `entity_id` interno solo vale para la compilación. No se eligen automáticamente relaciones ambiguas. [Identity contract](../docs/IDENTITY.md).

## Inicio rápido

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Bases de datos y versiones

Para integraciones, descargue `mappings.db.zst` y `manifest.json` de la última versión. `mappings-evidence.db.zst` conserva evidencia; `mappings.tsv.zst` y `mappings.jsonl.zst` son exportaciones portables. La publicación programada depende de cambios en las fuentes.

- [Latest release](https://github.com/anime-db-project/anime-mapping-db/releases/latest)
- [Runtime database (zstd)](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db.zst)
- [Release manifest](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json)

```text
data/mappings/mappings.db
data/mappings/mappings-evidence.db
```

## Documentación

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## Licencia y atribuciones

Código bajo Apache-2.0. La base compilada contiene datos sujetos a términos externos, incluidos ODbL/DbCL y obligaciones de atribución. Lea ambos documentos antes de redistribuir. [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
