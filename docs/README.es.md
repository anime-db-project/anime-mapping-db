> **Proyecto asistido por IA:** este proyecto fue desarrollado con ayuda de IA.

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <strong>Español</strong> · <a href="README.fr.md">Français</a> · <a href="README.it.md">Italiano</a>
</p>

# Anime Mapping DB

**Anime Mapping DB** es un constructor independiente y una base SQLite distribuible para relacionar identificadores de anime entre catálogos y servicios de seguimiento públicos. No existe una API HTTP de mappings: los consumidores descargan `mappings.db`/`mappings.db.zst` desde GitHub Releases y resuelven IDs localmente.

## Características

- 55 namespaces de proveedores y 18 datasets de entrada.
- ID público estable del proyecto: `amdb:<anchor_id>`; `entity_id` es local a la build y nunca es una clave externa.
- Las bases runtime/evidence publicadas usan el layout `compact-v1` optimizado para lectura.
- Resolución directa de un solo salto, sin recorrido transitivo inseguro.
- Confidence basada en evidence sin duplicar votos de fuentes correlacionadas.
- Runtime separado de la base de procedencia/evidence.
- AnimeAPI se usa solo como dataset suplementario alojado en GitHub, nunca mediante su REST API.
- Releases reproducibles con manifest, hashes, conteos de proveedores y Zstandard.

## Estado de la compilación validada

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

## Bases presentes en `mappings.db`

Los 55 namespaces de la compilación validada. Variantes como `tmdb_tv` y `tmdb_movie` se separan intencionadamente por su semántica.

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

## Datasets utilizados

| Dataset | Función / acceso |
| --- | --- |
| Fribb/anime-lists | fuente directa obligatoria, GitHub JSON |
| Kometa-Team/Anime-IDs | fuente directa obligatoria, GitHub JSON |
| Anime-Lists/anime-lists | fuente directa obligatoria, GitHub XML |
| cplieger/animap | fuente directa obligatoria, GitHub Release |
| cedya77/anime-offline-database | opcional, GitHub Release JSONL; fork mantenido de la línea Manami |
| anibridge/anibridge-mappings | opcional, GitHub Release |
| Wikidata / Bahamut | opcional, QLever bulk SPARQL → WDQS fallback → bootstrap CC0 local |
| rensetsu/db.notify.rensetsu-mirai | opcional, GitHub JSON |
| kawaiioverflow/arm | opcional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | opcional, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | opcional, GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | opcional, GitHub JSON, CC0 |
| rensetsu/db.rensetsu.public-dump AnimeThemes | supplemental, GitHub JSON, CC0 |
| anime-and-manga/lists | optional corroborating, GitHub JSON |
| shinkro/community-mapping | optional corroborating, GitHub JSON; title-level TVDB/TMDB only |
| notseteve/AnimeAggregations | supplemental, GitHub JSON, two-anchor validation |
| Wikidata multi-ID | supplemental, QLever bulk + WDQS fallback, two-anchor validation |
| nattadasu/animeApi | suplementario, solo GitHub `database/animeapi.tsv` |

## Fuentes suplementarias validadas por anchors

AnimeAggregations, Wikidata multi-ID y AnimeAPI se procesan solo después de construir el grafo provisional con las fuentes directas. Un ID ausente solo puede añadirse cuando existen al menos dos anchors exactos ya conocidos unidos por una arista directa aceptada y sin conflicto. Por tanto, estas fuentes amplias no pueden crear por sí solas una nueva identidad de título.

AnimeAggregations se consume únicamente como archivo bulk de GitHub; VNDB y enlaces genéricos de sitios/redes sociales se excluyen. Wikidata se descarga con una sola consulta SPARQL bulk mediante QLever y WDQS como fallback. De Shinkro solo se importan las relaciones title-level MAL↔TVDB series y MAL↔TMDB movie; el routing de temporadas/episodios queda fuera del grafo.

## Cómo se usa AnimeAPI

AnimeAPI no se considera un voto independiente adicional porque agrega varias fuentes que también consumimos directamente. Primero se construye un grafo provisional con fuentes directas. Una fila de AnimeAPI solo puede añadir un ID ausente cuando contiene al menos dos anchors ya conocidos unidos por una arista directa aceptada y sin conflicto. No añade evidencia entre los anchors ni un voto duplicado a un target ya presente. Se omite Trakt cuando `trakt_may_invalid=true` y se descartan todos los campos de temporada.

Solo se descarga `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv`; no se llama al REST de AnimeAPI, al API externo Geckyzz ni a los scrapers de sitios de AnimeAPI.

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## Identidad del proyecto

Anime Mapping DB separa dos tipos de ID. `entity_id` es una clave SQLite densa y local a una compilación concreta; puede cambiar tras un rebuild y no debe persistirse fuera de ese archivo. `anchor_id` es el ID público y estable del proyecto, con forma textual `amdb:<integer>`, por ejemplo `amdb:18472`.

Las tablas `entities`, `entity_nodes` y `anchor_redirects` forman esta capa. Los `(provider, external_id)` concretos siguen perteneciendo a `nodes`. En un merge los anchors antiguos se redirigen; en un split el componente con mayor solapamiento conserva el anchor anterior. Los anchors retirados no se reutilizan para otros títulos. Contrato completo: [`IDENTITY.md`](IDENTITY.md).

## Rendimiento

Benchmark reproducible: `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`. En el mismo host Linux: base anterior de 7 fuentes median 0.418 ms / p95 0.749 ms; nueva base de 18 datasets / 55 providers **0.354 ms / 0.497 ms**. La build de 18 datasets también dio mean 0.378 ms / p99 0.655 ms. Es un microbenchmark, no una garantía de latencia.

## Runtime y evidence

`mappings.db` usa el layout compact-v1 e incluye `metadata`, `nodes`, `edges`, `conflicts`, `entities`, `entity_nodes`, `anchor_redirects` y las tablas de overrides. El lookup directo usa la PK `edges(a_node,b_node)` y el lookup inverso aceptado usa un único índice parcial. `mappings-evidence.db` normaliza relaciones repetidas mediante `record_nodes`; el antiguo contrato `edge_evidence` se conserva como vista de compatibilidad de solo lectura. Un consumidor normal no necesita abrir la base de evidence.

## Confidence y conflictos

Una arista se acepta si `max_weight >= 80` o si la confirman al menos dos evidence groups independientes. Los conflictos direccionales bloquean solo la ruta ambigua. El resolver no recorre el grafo transitivamente.

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Releases y compilación local

Cada release contiene `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst`, los exports portables `mappings.tsv.zst` / `mappings.jsonl.zst`, `manifest.json` y `SHA256SUMS`. GitHub genera automáticamente los archivos estándar **Source code (zip)** y **Source code (tar.gz)** para cada Release, por lo que el proyecto no sube archivos de código fuente duplicados. Los exports de texto contienen rutas dirigidas y seguras para el resolver después de aplicar conflicts/overrides; SQLite sigue siendo el formato runtime canónico. La automatización se ejecuta tras cambios del mapping engine en `main`, diariamente a las 03:17 UTC, con tags `v*` y manualmente. Un chequeo diario sin cambios en el source fingerprint no publica un nuevo release.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Licencias

El código está bajo Apache-2.0. La base compilada combina datos de terceros con sus propias obligaciones; AnimeAPI y anime-offline-database usan ODbL 1.0 + DbCL 1.0. Consulta `THIRD_PARTY_NOTICES.md`.
