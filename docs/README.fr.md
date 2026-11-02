> **Projet assisté par IA :** ce projet a été développé avec l’aide de l’IA.

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <strong>Français</strong> · <a href="README.it.md">Italiano</a>
</p>

# Anime Mapping DB

**Anime Mapping DB** est un constructeur autonome et une base SQLite distribuable pour faire correspondre des identifiants d’anime entre catalogues et services de suivi publics. Il n’existe pas d’API HTTP de mapping : les consommateurs téléchargent `mappings.db`/`mappings.db.zst` depuis GitHub Releases et résolvent les IDs localement.

## Points forts

- 55 espaces de noms de fournisseurs et 18 jeux de données entrants.
- Identifiant public stable du projet : `amdb:<anchor_id>` ; `entity_id` reste local à la build et n’est jamais une clé externe.
- Les bases runtime/evidence publiées utilisent le layout `compact-v1` optimisé pour la lecture.
- Résolution directe en un seul saut, sans parcours transitif risqué.
- Confidence basée sur les preuves sans doubler artificiellement les sources corrélées.
- Base runtime séparée de la base de provenance/evidence.
- AnimeAPI uniquement comme source supplémentaire hébergée sur GitHub, jamais via son API REST.
- Releases reproductibles avec manifest, hash, compteurs de fournisseurs et Zstandard.

## État de la build validée

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

## Bases présentes dans `mappings.db`

Les 55 namespaces de la build validée. Les variantes comme `tmdb_tv` et `tmdb_movie` sont volontairement séparées pour conserver leur sémantique.

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

## Jeux de données utilisés

| Jeu de données | Rôle / accès |
| --- | --- |
| Fribb/anime-lists | source directe requise, GitHub JSON |
| Kometa-Team/Anime-IDs | source directe requise, GitHub JSON |
| Anime-Lists/anime-lists | source directe requise, GitHub XML |
| cplieger/animap | source directe requise, GitHub Release |
| cedya77/anime-offline-database | optionnel, GitHub Release JSONL ; fork maintenu de la lignée Manami |
| anibridge/anibridge-mappings | optionnel, GitHub Release |
| Wikidata / Bahamut | optionnel, QLever bulk SPARQL → WDQS fallback → bootstrap CC0 local |
| rensetsu/db.notify.rensetsu-mirai | optionnel, GitHub JSON |
| kawaiioverflow/arm | optionnel, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | optionnel, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | optionnel, GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | optionnel, GitHub JSON, CC0 |
| rensetsu/db.rensetsu.public-dump AnimeThemes | supplemental, GitHub JSON, CC0 |
| anime-and-manga/lists | optional corroborating, GitHub JSON |
| shinkro/community-mapping | optional corroborating, GitHub JSON; title-level TVDB/TMDB only |
| notseteve/AnimeAggregations | supplemental, GitHub JSON, two-anchor validation |
| Wikidata multi-ID | supplemental, QLever bulk + WDQS fallback, two-anchor validation |
| nattadasu/animeApi | enrichissement, uniquement GitHub `database/animeapi.tsv` |

## Sources supplémentaires validées par anchors

AnimeAggregations, Wikidata multi-ID et AnimeAPI ne sont traités qu’après la construction du graphe provisoire à partir des sources directes. Un identifiant manquant n’est ajouté que si au moins deux anchors exacts déjà connus sont reliés par une arête directe acceptée et sans conflit. Ces sources ne peuvent donc pas créer seules une nouvelle identité de titre.

AnimeAggregations est consommé uniquement sous forme de fichier bulk GitHub ; VNDB et les liens génériques de sites/réseaux sociaux sont exclus. Wikidata est chargé par une seule requête SPARQL bulk via QLever, avec WDQS en fallback. Pour Shinkro, seules les correspondances title-level MAL↔TVDB series et MAL↔TMDB movie sont importées ; le routage saison/épisode reste hors du graphe.

## Utilisation d’AnimeAPI

AnimeAPI n’est pas compté comme une nouvelle preuve indépendante car il agrège plusieurs sources que nous utilisons déjà directement. Le graphe provisoire est d’abord construit à partir des sources directes. Une ligne AnimeAPI ne peut ajouter un identifiant manquant que si au moins deux anchors connus sont déjà reliés par une arête directe acceptée et sans conflit. Aucun vote corrélé n’est ajouté pour un target déjà présent. `trakt_may_invalid=true` et tous les champs de saison sont ignorés.

Le builder télécharge uniquement `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv`; il n’appelle ni le REST AnimeAPI, ni l’API Geckyzz, ni les scrapers de sites d’AnimeAPI.

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## Identité du projet

Anime Mapping DB distingue deux types d’identifiants. `entity_id` est une clé SQLite dense, locale à une build précise ; elle peut être renumérotée et ne doit pas être persistée hors de ce fichier. `anchor_id` est l’identifiant public stable du projet, sous la forme `amdb:<integer>`, par exemple `amdb:18472`.

Les tables `entities`, `entity_nodes` et `anchor_redirects` constituent cette couche. Les `(provider, external_id)` concrets restent dans `nodes`. Lors d’un merge, les anciens anchors sont redirigés ; lors d’un split, le composant avec le plus fort recouvrement conserve l’ancien anchor. Les numéros retirés ne sont jamais réutilisés pour un autre titre. Contrat complet : [`IDENTITY.md`](IDENTITY.md).

## Performances

Benchmark reproductible : `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`. Sur le même hôte Linux : ancienne build 7 sources median 0.418 ms / p95 0.749 ms ; nouvelle build 18 datasets / 55 providers **0.354 ms / 0.497 ms**. La build à 18 datasets donne aussi mean 0.378 ms / p99 0.655 ms. Il s’agit d’un microbenchmark, pas d’une garantie de latence.

## Runtime et evidence

`mappings.db` utilise le layout compact-v1 et contient `metadata`, `nodes`, `edges`, `conflicts`, `entities`, `entity_nodes`, `anchor_redirects` ainsi que les tables d’overrides. Le lookup direct utilise la clé primaire `edges(a_node,b_node)` et le lookup inverse accepté un unique index partiel. `mappings-evidence.db` normalise les relations répétées via `record_nodes`; l’ancien contrat `edge_evidence` reste disponible comme vue de compatibilité en lecture seule. Un consumer normal n’a pas besoin de la base evidence.

## Confidence et conflits

Une arête est acceptée si `max_weight >= 80` ou si au moins deux evidence groups indépendants la confirment. Les conflits directionnels bloquent uniquement la route ambiguë. Le resolver ne parcourt pas le graphe de façon transitive.

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Releases et build locale

Chaque release contient `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst`, les exports `mappings.tsv.zst`/`mappings.jsonl.zst`, `manifest.json`, `SHA256SUMS` et trois archives des sources du projet : `zz-anime-mapping-db-<tag>-source.zip`, `.tar.zst` et `.7z`. Elles sont générées depuis le tracked Git tree exact du commit publié. Le préfixe `zz-` ne sert qu’à les placer en fin de liste ; à l’intérieur, la racine reste `anime-mapping-db-<tag>/`. Les trois SHA-256 sont également ajoutés à `SHA256SUMS`. Aucun release quotidien n’est publié si le fingerprint des sources est inchangé.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Licences

Le code du projet est sous Apache-2.0. La base compilée combine des données tierces avec leurs propres obligations ; AnimeAPI et anime-offline-database sont notamment ODbL 1.0 + DbCL 1.0. Voir `THIRD_PARTY_NOTICES.md`.
