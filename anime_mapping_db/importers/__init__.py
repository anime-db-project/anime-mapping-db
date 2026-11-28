from __future__ import annotations

from anime_mapping_db.aniliberty import import_aniliberty_enrichment
from anime_mapping_db.anime365 import import_anime365_enrichment
from anime_mapping_db.importers.direct import (
    import_anibridge,
    import_anime_and_manga_lists,
    import_anime_lists,
    import_animap,
    import_animethemes,
    import_anitrakt_movie,
    import_anitrakt_tv,
    import_arm,
    import_fribb,
    import_kometa,
    import_manami,
    import_notify_rensetsu,
    import_shinkro,
    import_silveryasha,
)
from anime_mapping_db.importers.enrichment import (
    import_animeaggregations_enrichment,
    import_animeapi_enrichment,
    import_animethemes_enrichment,
)
from anime_mapping_db.importers.malsync import (
    import_malsync_crunchyroll,
    import_malsync_netflix,
)
from anime_mapping_db.importers.media_index import import_media_index_enrichment
from anime_mapping_db.importers.sovetromantica import import_sovetromantica_enrichment
from anime_mapping_db.importers.wikidata import (
    import_wikidata_bahamut,
    import_wikidata_enrichment,
)

IMPORTERS = {
    "fribb": import_fribb,
    "kometa": import_kometa,
    "anime_lists": import_anime_lists,
    "animap": import_animap,
    "manami": import_manami,
    "anibridge": import_anibridge,
    "wikidata_bahamut": import_wikidata_bahamut,
    "notify_rensetsu": import_notify_rensetsu,
    "arm": import_arm,
    "anitrakt_tv": import_anitrakt_tv,
    "anitrakt_movie": import_anitrakt_movie,
    "silveryasha": import_silveryasha,
    "animethemes": import_animethemes,
    "anime_and_manga_lists": import_anime_and_manga_lists,
    "shinkro": import_shinkro,
}

SUPPLEMENTAL_IMPORTERS = {
    "animeapi": import_animeapi_enrichment,
    "animethemes": import_animethemes_enrichment,
    "animeaggregations": import_animeaggregations_enrichment,
    "wikidata_multi": import_wikidata_enrichment,
    "media_index": import_media_index_enrichment,
    "aniliberty": import_aniliberty_enrichment,
    "anime365": import_anime365_enrichment,
    "sovetromantica": import_sovetromantica_enrichment,
    "malsync_crunchyroll": import_malsync_crunchyroll,
    "malsync_netflix": import_malsync_netflix,
}

__all__ = [
    "IMPORTERS",
    "SUPPLEMENTAL_IMPORTERS",
    "import_anibridge",
    "import_aniliberty_enrichment",
    "import_anime365_enrichment",
    "import_anime_and_manga_lists",
    "import_anime_lists",
    "import_animeaggregations_enrichment",
    "import_animeapi_enrichment",
    "import_media_index_enrichment",
    "import_malsync_crunchyroll",
    "import_malsync_netflix",
    "import_animap",
    "import_animethemes",
    "import_animethemes_enrichment",
    "import_anitrakt_movie",
    "import_anitrakt_tv",
    "import_arm",
    "import_fribb",
    "import_kometa",
    "import_manami",
    "import_notify_rensetsu",
    "import_shinkro",
    "import_sovetromantica_enrichment",
    "import_silveryasha",
    "import_wikidata_bahamut",
    "import_wikidata_enrichment",
]
