> **Projet développé avec l'aide de l'IA.**

<p align="center">
  <a href="../README.md">English</a> · <a href="README.ru.md">Русский</a> · <a href="README.ja.md">日本語</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <strong>Français</strong> · <a href="README.it.md">Italiano</a>
</p>

# anime-mapping-db

[![CI](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/ci.yml)
[![Releases](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml/badge.svg)](https://github.com/anime-db-project/anime-mapping-db/actions/workflows/release.yml)
[![Python](https://img.shields.io/badge/Python-3.11--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Code license](https://img.shields.io/badge/Code-Apache%202.0-D22128.svg)](../LICENSE)
[![Data license](https://img.shields.io/badge/Data-Upstream%20terms-555555.svg)](../DATA_LICENSE.md)

Base reproductible des correspondances d'identifiants d'anime entre services, avec traçabilité des sources. Elle fournit des IDs stables et des recherches SQLite compactes.

## Fonctionnalités

- Identifiants `amdb:<anchor_id>` stables entre les reconstructions.
- Correspondances justifiées par des preuves, une confiance et une gestion des conflits.
- Résolution directe sans parcours arbitraire du graphe.
- Séparation des bases légères d'exécution et des preuves détaillées.
- Versions GitHub avec bases compressées, exports textuels, manifestes et sommes de contrôle.

## Identité et règles de rapprochement

Anime Mapping DB fournit une identité stable propre au projet, `amdb:<anchor_id>`, sans dépendre de MAL, AniList ou d'une autre plateforme. Elle peut être conservée entre builds. `entity_id`, en revanche, n'est qu'une clé SQLite interne d'une compilation donnée.

Les identifiants externes sont des nœuds `(provider, external_id)`. Des nœuds confirmés peuvent appartenir à une même œuvre, mais deux IDs différents du même fournisseur ne sont jamais fusionnés en une seule entité. Les cas ambigus restent indéterminés.

Une reconstruction préserve les anchors des œuvres conservées ou enrichies. Les fusions légitimes produisent des redirections et les scissions de nouveaux IDs, sans réutiliser d'anciens numéros pour des œuvres sans rapport. Les bases associées conservent ainsi leurs références.

```text
(provider, external_id) ──accepted edge── (provider, external_id)
          \                         /
           \── stable amdb:<anchor_id> ──/
                   │
              anchor redirects
```

## Sources de données

Le constructeur regroupe 18 entrées, entre jeux de données directs et catalogues complémentaires vérifiés. Ces compléments ne peuvent pas créer une identité sans confirmation indépendante. Entrées et licences figurent dans le manifeste.

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

`amdb:<anchor_id>` est l'identifiant stable d'un titre. Les IDs externes sont des alias justifiés; `entity_id` est propre à une compilation. Les relations ambiguës ne sont pas choisies automatiquement. [Identity contract](../docs/IDENTITY.md).

## Sources et provenance

Le constructeur télécharge des jeux de données publics et consigne les observations et leur provenance avant de former le graphe d'exécution. Les enregistrements dérivés d'une même source sont groupés afin de ne pas multiplier artificiellement les preuves.

Les sources directes peuvent établir des liens. AnimeAPI, AnimeAggregations, références AnimeThemes et Wikidata multi-ID n'enrichissent que des entités déjà prouvées par au moins deux anchors existants et compatibles. Cela évite de confondre adaptation, saison et franchise.

Adresses, empreintes et versions sont enregistrées dans le manifeste ; `anime_mapping_db/config.py` décrit les entrées. Les consommateurs n'ont pas besoin d'une API REST externe, seulement de SQLite.

```text
1. Télécharger les sources publiques
2. Regrouper les preuves par origine
3. Évaluer les correspondances directes
4. Résoudre les conflits et attribuer des IDs stables
5. Auditer, compacter et publier
```

## Structure des bases

La base légère `mappings.db` contient nœuds, liens, conflits directionnels, entités stables, redirections et corrections manuelles. Elle vise les recherches directes indexées et non les parcours récursifs arbitraires.

La base séparée `mappings-evidence.db` conserve jeux d'entrée, observations, groupes de preuves et relations d'origine. Elle est facultative pour une simple application de correspondance d'IDs. Les deux fichiers sont contrôlés avant publication.

```text
mappings.db
  metadata · nodes · edges · conflicts
  entities · entity_nodes · anchor_redirects
  mapping_overrides · mapping_override_history

mappings-evidence.db
  metadata · datasets · nodes · evidence_groups
  records · record_nodes · edge_evidence (view)
```

## Démarrage rapide

Python 3.11+:

```bash
git clone https://github.com/anime-db-project/anime-mapping-db.git
cd anime-mapping-db
python -m pip install -e .
python -m anime_mapping_db build --force
python -m anime_mapping_db status
```

## Utilisation du résolveur

Une recherche part d'un espace de noms et d'un ID externe pour ne retourner que des relations directes, acceptées et non ambiguës. Deux valeurs numériques identiques chez MAL et AniList ne suffisent pas.

Le résolveur Python ou SQLite peuvent être utilisés. Les tables d'entités et d'anchors portent les identifiants stables ; une traversée récursive non contrainte n'est pas équivalente à une résolution sûre.

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

## Confiance et conflits

La confiance combine le poids de la meilleure source, les groupes de preuves indépendants et la corroboration. Une source forte ou deux groupes indépendants peuvent faire accepter une arête. Les preuves insuffisantes restent candidates.

Les conflits sont directionnels : `A → B` peut être ambigu même si l'inverse est sûr. Les exceptions manuelles acceptent ou rejettent un lien avec historique. Leur impact sur les autres applications doit être examiné.

```text
confidence = min(100,
    max_weight
    + 8 × (distinct_evidence_groups - 1)
    + 2 × min(5, evidence_count - distinct_evidence_groups)
)

accepted: max_weight >= 80 OR distinct_evidence_groups >= 2
candidate: unconfirmed relationships
```

## Bases de données et versions

Pour les intégrations, récupérer `mappings.db.zst` et `manifest.json` dans la dernière version. `mappings-evidence.db.zst` conserve les preuves ; `mappings.tsv.zst` et `mappings.jsonl.zst` sont des exports portables. Les publications planifiées dépendent des changements des sources.

- [Latest release](https://github.com/anime-db-project/anime-mapping-db/releases/latest)
- [Runtime database (zstd)](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/mappings.db.zst)
- [Release manifest](https://github.com/anime-db-project/anime-mapping-db/releases/latest/download/manifest.json)

```text
data/mappings/mappings.db
data/mappings/mappings-evidence.db
```

## Fichiers de publication et intégration

Les publications contiennent SQLite runtime et evidence, fichiers zstd, exports dirigés portables, manifeste et SHA-256. Les formats texte donnent les routes sûres après filtrage des ambiguïtés, et non les arêtes brutes.

`manifest.json` fait autorité pour les schémas, tailles, versions des sources, hashes, volumes et fingerprints. Ces chiffres changent entre builds ; vérifiez les empreintes des téléchargements plutôt que les valeurs figées d'un README.

Les publications répondent aux changements du projet, contrôles planifiés, tags et exécutions manuelles. Un contrôle sans nouvelle source peut ne rien publier. Les archives de code source sont fournies par GitHub.

| Fichier | Rôle |
| --- | --- |
| `mappings.db` | SQLite runtime compacte |
| `mappings.db.zst` | Base runtime compressée |
| `mappings-evidence.db.zst` | Base de preuves compressée |
| `mappings.tsv.zst` | Routes TSV dirigées |
| `mappings.jsonl.zst` | Routes JSON Lines dirigées |
| `manifest.json` | Schémas, sources, chiffres et empreintes |
| `SHA256SUMS` | Contrôles SHA-256 |

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

`source_provider` — Fournisseur source; `source_id` — ID source; `target_provider` — Fournisseur cible; `target_id` — ID cible; `confidence` — Confiance; `evidence_count` — Nombre de preuves; `evidence_group_count` — Groupes indépendants; `max_weight` — Poids maximal; `origin` — Origine

## Validation et développement

La CI teste le formatage, l'intégrité SQLite, les anchors, redirections, conflits, niveaux de confiance et fichiers distribués. Les nouveaux importeurs doivent être accompagnés de tests.

```bash
python -m pip install -e .
python -m pip install pytest ruff
python -m pytest -q
python -m ruff check .
```

[Contrat d'identité](../docs/IDENTITY.md)

## Documentation

- [Identity and matching](../docs/IDENTITY.md)
- [Data licensing](../DATA_LICENSE.md) · [Third-party notices](../THIRD_PARTY_NOTICES.md)
- [anime-db-bot](https://github.com/anime-db-project/anime-db-bot) · [anime-timestamp-db](https://github.com/anime-db-project/anime-timestamp-db)

## Licence et attribution

Code sous Apache-2.0. Les données compilées conservent les conditions tierces, notamment ODbL/DbCL et les obligations d'attribution. Lire les deux documents avant redistribution. [Apache-2.0](../LICENSE) · [DATA_LICENSE.md](../DATA_LICENSE.md) · [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
