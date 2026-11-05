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

## Identidad y reglas de correspondencia

Anime Mapping DB ofrece `amdb:<anchor_id>` como identidad estable y propia de cada anime, independiente de MAL, AniList y otros servicios. Se puede conservar entre compilaciones. `entity_id`, en cambio, es una clave SQLite interna válida solo para una compilación concreta.

Los IDs externos son nodos `(provider, external_id)`. Los nodos verificados pueden formar una entidad, pero dos IDs distintos del mismo proveedor no pueden confundirse como una misma obra. Los casos ambiguos quedan sin resolver.

Las recompilaciones conservan anchors existentes cuando identifican las mismas entidades. Las uniones legítimas crean redirecciones y las separaciones asignan nuevas claves sin reutilizar IDs retirados. Así pueden consultarse títulos desde otras bases entre versiones.

```text
(provider, external_id) ──accepted edge── (provider, external_id)
          \                         /
           \── stable amdb:<anchor_id> ──/
                   │
              anchor redirects
```

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

## Datos de entrada y procedencia

El generador importa datasets públicos, registra evidencia de origen y después materializa el grafo runtime. Cada observación mantiene una fuente y un grupo de evidencia, impidiendo contar espejos como confirmaciones independientes.

Las fuentes directas aportan aristas verificables. AnimeAPI, AnimeAggregations, las referencias de AnimeThemes y Wikidata multi-ID solo complementan entidades tras validar al menos dos anchors existentes sin conflictos. Así se evitan uniones entre adaptaciones, temporadas y franquicias.

Las URLs, hashes y versiones de origen constan en el manifiesto. La configuración está en `anime_mapping_db/config.py`. Las consultas utilizan SQLite local y no requieren REST externos.

```text
1. Obtener datasets públicos
2. Agrupar evidencias por procedencia
3. Evaluar relaciones directas
4. Resolver conflictos y asignar IDs estables
5. Auditar, compactar y publicar
```

## Diseño de las bases

La base compacta `mappings.db` almacena nodos, relaciones, conflictos dirigidos, entidades estables, redirecciones y excepciones manuales. Está optimizada para consultas directas mediante índices, no recorridos arbitrarios del grafo.

`mappings-evidence.db` conserva fuentes, observaciones y grupos de evidencia que justifican las relaciones. Los consumidores que solo necesitan convertir IDs pueden omitirla. Ambas bases pasan pruebas antes de publicarse.

```text
mappings.db
  metadata · nodes · edges · conflicts
  entities · entity_nodes · anchor_redirects
  mapping_overrides · mapping_override_history

mappings-evidence.db
  metadata · datasets · nodes · evidence_groups
  records · record_nodes · edge_evidence (view)
```

## Inicio rápido

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Uso del resolver

Una consulta recibe namespace e ID externo y devuelve objetivos directos aceptados y no ambiguos. El mismo número en MAL y AniList no demuestra identidad sin una relación verificada.

Use el resolver Python o SQLite. Las entidades y anchors contienen los IDs estables; no sustituya el resolver conservador por consultas recursivas sin límites.

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

## Confianza y conflictos

La confianza combina el peso más alto de la fuente, grupos de evidencia independientes y observaciones de apoyo. Una fuente suficientemente fiable o dos grupos independientes permiten aceptar una relación. Los candidatos débiles no aparecen en la resolución habitual.

Los conflictos son direccionales: `A → B` puede ser ambiguo mientras la dirección inversa es segura. Las excepciones manuales aceptan o rechazan relaciones con historial auditable; revíselas porque pueden afectar a otros consumidores.

```text
confidence = min(100,
    max_weight
    + 8 × (distinct_evidence_groups - 1)
    + 2 × min(5, evidence_count - distinct_evidence_groups)
)

accepted: max_weight >= 80 OR distinct_evidence_groups >= 2
candidate: unconfirmed relationships
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

## Archivos de publicación e integración

Los lanzamientos contienen las bases runtime y de evidencia, compresión zstd, exportaciones textuales portables, manifiesto y SHA-256. Los textos son rutas dirigidas y filtradas, no aristas sin verificar.

`manifest.json` es la referencia para versiones de esquema, tamaños, orígenes, hashes, cifras y fingerprints. Cambian entre builds; evite usar números fijos de README como cobertura actual. Compruebe las sumas tras descargar.

La publicación se ejecuta tras cambios de código, por calendario, por tags o manualmente. Si no cambia la huella de las fuentes, una ejecución programada puede no publicar. GitHub genera los archivos de código fuente.

| Archivo | Función |
| --- | --- |
| `mappings.db` | SQLite compacta para consultas |
| `mappings.db.zst` | Base runtime comprimida |
| `mappings-evidence.db.zst` | Evidencia comprimida |
| `mappings.tsv.zst` | Rutas dirigidas TSV |
| `mappings.jsonl.zst` | Rutas dirigidas JSON Lines |
| `manifest.json` | Esquemas, fuentes, cifras y hashes |
| `SHA256SUMS` | Sumas SHA-256 |

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

`source_provider` — Proveedor inicial; `source_id` — ID inicial; `target_provider` — Proveedor destino; `target_id` — ID destino; `confidence` — Confianza; `evidence_count` — Registros de evidencia; `evidence_group_count` — Grupos independientes; `max_weight` — Peso máximo; `origin` — Procedencia

## Validación y desarrollo

CI comprueba pruebas, formato, integridad SQLite, anchors, redirecciones, confianza, conflictos y artefactos de release. Acompañe cada importador nuevo con pruebas.

```bash
python -m pip install -e .
python -m pip install pytest ruff
python -m pytest -q
python -m ruff check .
```

[Contrato de identidad](../docs/IDENTITY.md)

## Documentación

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## Licencia y atribuciones

Código bajo Apache-2.0. La base compilada contiene datos sujetos a términos externos, incluidos ODbL/DbCL y obligaciones de atribución. Lea ambos documentos antes de redistribuir. [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
