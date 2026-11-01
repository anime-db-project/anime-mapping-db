> **Projet assisté par IA :** ce projet a été développé avec l’aide de l’IA.

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <strong>Français</strong> · <a href="README.it.md">Italiano</a>
</p>

# Anime Mapping DB

**Anime Mapping DB** est un constructeur autonome et une base SQLite distribuable pour faire correspondre des identifiants d’anime entre catalogues et services de suivi publics. Il n’existe pas d’API HTTP de mapping : les consommateurs téléchargent `mappings.db`/`mappings.db.zst` depuis GitHub Releases et résolvent les IDs localement.

## Points forts

- 31 espaces de noms de fournisseurs et 13 jeux de données entrants.
- Résolution directe en un seul saut, sans parcours transitif risqué.
- Confidence basée sur les preuves sans doubler artificiellement les sources corrélées.
- Base runtime séparée de la base de provenance/evidence.
- AnimeAPI uniquement comme source supplémentaire hébergée sur GitHub, jamais via son API REST.
- Releases reproductibles avec manifest, hash, compteurs de fournisseurs et Zstandard.

## État de la build validée

| Metric | Value |
| --- | ---: |
| Dataset inputs | 13 |
| Provider namespaces | 31 |
| Unique provider/ID nodes | 371,128 |
| Source records | 654,827 |
| Evidence edges | 2,169,089 |
| Runtime edges | 1,111,505 |
| Accepted runtime edges | 1,104,610 |
| Directional conflicts | 19,724 |
| `mappings.db` | ~104.5 MiB |
| `mappings.db.zst` | ~17.9 MiB |

## Bases présentes dans `mappings.db`

Les 31 namespaces de la build validée. Les variantes comme `tmdb_tv` et `tmdb_movie` sont volontairement séparées pour conserver leur sémantique.

| Namespace | Database / ID | Count |
| --- | --- | ---: |
| `anidb` | AniDB | 16,341 |
| `anilist` | AniList | 22,415 |
| `animecountdown` | AnimeCountdown | 14,711 |
| `animeplanet` | Anime-Planet | 25,126 |
| `anisearch` | aniSearch | 20,042 |
| `ann` | Anime News Network | 12,402 |
| `annict` | Annict | 13,353 |
| `bahamut` | Bahamut Animation Crazy | 783 |
| `hikka` | Hikka | 27,157 |
| `imdb` | IMDb | 7,162 |
| `kaize` | Kaize slug | 23,233 |
| `kaize_id` | Kaize numeric ID | 9,956 |
| `kitsu` | Kitsu | 21,692 |
| `letterboxd_lid` | Letterboxd LID | 1,269 |
| `letterboxd_slug` | Letterboxd slug | 1,269 |
| `letterboxd_uid` | Letterboxd UID | 1,269 |
| `livechart` | LiveChart.me | 12,367 |
| `mal` | MyAnimeList | 28,119 |
| `nautiljon` | Nautiljon slug | 8,979 |
| `nautiljon_id` | Nautiljon numeric ID | 9,002 |
| `notify` | Notify.moe | 16,861 |
| `otakotaku` | Otak Otaku | 3,131 |
| `shikimori` | Shikimori | 27,711 |
| `shoboi` | Shoboi / Syoboi Calendar | 6,525 |
| `silveryasha` | SilverYasha | 5,703 |
| `simkl` | SIMKL | 14,711 |
| `tmdb_movie` | TMDB movie | 3,304 |
| `tmdb_tv` | TMDB TV | 4,465 |
| `trakt` | Trakt title | 6,100 |
| `tvdb` | TVDB series | 4,854 |
| `tvdb_movie` | TVDB movie | 1,116 |

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
| Wikidata / Bahamut | optionnel, WDQS + bootstrap CC0 local en cas de panne |
| rensetsu/db.notify.rensetsu-mirai | optionnel, GitHub JSON |
| kawaiioverflow/arm | optionnel, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt TV | optionnel, GitHub JSON |
| rensetsu/db.trakt.extended-anitrakt Movies | optionnel, GitHub JSON |
| rensetsu/db.rensetsu.public-dump SilverYasha | optionnel, GitHub JSON, CC0 |
| nattadasu/animeApi | enrichissement, uniquement GitHub `database/animeapi.tsv` |

## Utilisation d’AnimeAPI

AnimeAPI n’est pas compté comme une nouvelle preuve indépendante car il agrège plusieurs sources que nous utilisons déjà directement. Le graphe provisoire est d’abord construit à partir des sources directes. Une ligne AnimeAPI ne peut ajouter un identifiant manquant que si au moins deux anchors connus sont déjà reliés par une arête directe acceptée et sans conflit. Aucun vote corrélé n’est ajouté pour un target déjà présent. `trakt_may_invalid=true` et tous les champs de saison sont ignorés.

Le builder télécharge uniquement `https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/animeapi.tsv`; il n’appelle ni le REST AnimeAPI, ni l’API Geckyzz, ni les scrapers de sites d’AnimeAPI.

```text
Direct datasets → provisional accepted graph → AnimeAPI TSV → anchor validation → final graph
```

## Performances

Benchmark reproductible : `python scripts/benchmark_lookup.py --db data/mappings/mappings.db --samples 1200 --rounds 3`. Sur le même hôte Linux : ancienne build 7 sources median 0.418 ms / p95 0.749 ms ; nouvelle build 13 datasets **0.403 ms / 0.552 ms**. Un autre échantillon de la nouvelle DB donne median 0.446 ms / p95 0.551 ms. Il s’agit d’un microbenchmark, pas d’une garantie de latence.

## Runtime et evidence

`mappings.db` contient uniquement les tables nécessaires aux lookups et overrides. `mappings-evidence.db` conserve les datasets, enregistrements source, evidence groups et la provenance. Les consommateurs normaux n’en ont pas besoin.

## Confidence et conflits

Une arête est acceptée si `max_weight >= 80` ou si au moins deux evidence groups indépendants la confirment. Les conflits directionnels bloquent uniquement la route ambiguë. Le resolver ne parcourt pas le graphe de façon transitive.

```text
confidence = min(100, max_weight + 8×(groups-1) + 2×min(5, evidence-groups))
accepted = max_weight >= 80 OR groups >= 2
```

## Releases et build locale

Chaque release contient `mappings.db`, `mappings.db.zst`, `mappings-evidence.db.zst`, `manifest.json` et `SHA256SUMS`. Automatisation après changement du moteur sur `main`, chaque jour à 03:17 UTC, pour les tags `v*` et manuellement. Aucun release quotidien si le fingerprint des sources est inchangé.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Licences

Le code du projet est sous Apache-2.0. La base compilée combine des données tierces avec leurs propres obligations ; AnimeAPI et anime-offline-database sont notamment ODbL 1.0 + DbCL 1.0. Voir `THIRD_PARTY_NOTICES.md`.
