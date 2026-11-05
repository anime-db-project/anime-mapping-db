"""Keep every localized README's database facts in sync with published releases.

The generated section alone is managed; translators own the rest of each README.
Source of truth: the *current release* manifest, shipped runtime SQLite and
per-release local read-only lookup benchmark.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

BEGIN = "<!-- BEGIN AUTO-GENERATED DATABASE STATS -->"
END = "<!-- END AUTO-GENERATED DATABASE STATS -->"
REPO = "anime-db-project/anime-mapping-db"
LANGUAGES = ("en", "ru", "ja", "de", "es", "fr", "it")

# Titles identify the older hand-maintained statistics block on first upgrade.
WORDS: dict[str, dict[str, str | list[str]]] = {
    "en": {
        "title": "Database at a glance",
        "sub": "This release contains **{identities} indexed AMDB identity groups**. This measures indexed identity groups, **not a verified count of distinct anime works**.",
        "metric": "Metric",
        "value": "Value",
        "labels": [
            "Indexed AMDB identity groups",
            "Provider ID namespaces",
            "Source datasets",
            "Accepted mapping edges",
            "Safe directed export routes",
            "Directional conflicts",
            "Source records",
            "Evidence relationships",
            "Runtime SQLite size",
            "Compressed SQLite size",
        ],
        "bench": "Local lookup performance",
        "bench_note": "Warm-cache, sequential, read-only MappingResolver calls against the released SQLite on {environment}. {sampled} IDs × {rounds} rounds. Not network/API latency.",
        "speed": [
            "Median lookup",
            "Mean lookup",
            "p95 lookup",
            "p99 lookup",
            "Sequential queries per second",
        ],
        "snapshot": "Release snapshot",
        "latest": "Current release manifest",
        "pending": "No measured benchmark was provided for this snapshot.",
    },
    "ru": {
        "title": "Статистика базы данных",
        "sub": "В этом релизе **{identities} проиндексированных AMDB-сущностей**. Это количество групп идентификаторов в базе, **а не подтверждённое число уникальных аниме**.",
        "metric": "Показатель",
        "value": "Значение",
        "labels": [
            "Индексированные группы идентификаторов AMDB",
            "Пространства внешних ID",
            "Наборы источников",
            "Подтверждённые связи ID",
            "Безопасные направленные маршруты",
            "Направленные конфликты",
            "Записи источников",
            "Evidence-связи",
            "Размер SQLite",
            "Размер сжатой SQLite",
        ],
        "bench": "Скорость локальных запросов",
        "bench_note": "Последовательные запросы MappingResolver к релизной SQLite с прогретым кэшем, {environment}. {sampled} ID × {rounds} повторения. Это не задержка сетевых API.",
        "speed": [
            "Медианная задержка",
            "Средняя задержка",
            "Задержка p95",
            "Задержка p99",
            "Последовательные запросы/с",
        ],
        "snapshot": "Снимок релиза",
        "latest": "Актуальный манифест",
        "pending": "Для этого снимка нет опубликованного результата замеров.",
    },
    "ja": {
        "title": "データベースの規模",
        "sub": "このリリースには **{identities}件の AMDB ID グループ**があります。これはデータベース上の識別子数であり、**重複のないアニメ作品数を証明する数値ではありません**。",
        "metric": "指標",
        "value": "値",
        "labels": [
            "インデックスされた AMDB ID グループ",
            "プロバイダー ID 空間",
            "入力データセット",
            "確認済みの対応エッジ",
            "安全な方向付き出力経路",
            "方向付き競合",
            "元レコード",
            "証拠関係",
            "SQLite サイズ",
            "圧縮 SQLite サイズ",
        ],
        "bench": "ローカル検索速度",
        "bench_note": "リリース SQLite に対するキャッシュ済み MappingResolver の逐次読み取り、{environment}。{sampled} ID × {rounds} 回。ネットワーク API の遅延ではありません。",
        "speed": [
            "中央値",
            "平均",
            "p95",
            "p99",
            "逐次検索/秒",
        ],
        "snapshot": "リリース時点",
        "latest": "最新マニフェスト",
        "pending": "このスナップショットのベンチマークはありません。",
    },
    "de": {
        "title": "Datenbank in Zahlen",
        "sub": "Dieses Release enthält **{identities} indexierte AMDB-Identitätsgruppen**. Das ist eine Datenbankkennzahl, **keine verifizierte Anzahl unterschiedlicher Anime-Titel**.",
        "metric": "Kennzahl",
        "value": "Wert",
        "labels": [
            "Indexierte AMDB-Identitätsgruppen",
            "Provider-ID-Namensräume",
            "Quelldatensätze",
            "Akzeptierte Mapping-Kanten",
            "Sichere gerichtete Routen",
            "Gerichtete Konflikte",
            "Quellrecords",
            "Evidenzbeziehungen",
            "SQLite-Größe",
            "Komprimierte SQLite-Größe",
        ],
        "bench": "Lokale Abfrageleistung",
        "bench_note": "Sequentielle MappingResolver-Lookups auf der Release-SQLite mit warmem Cache, {environment}. {sampled} IDs × {rounds} Runden; keine Netzwerklatenz.",
        "speed": [
            "Median",
            "Mittelwert",
            "p95",
            "p99",
            "Sequentielle Abfragen/s",
        ],
        "snapshot": "Release-Snapshot",
        "latest": "Aktuelles Manifest",
        "pending": "Für diesen Snapshot liegt kein Benchmark vor.",
    },
    "es": {
        "title": "La base de datos en cifras",
        "sub": "Esta versión contiene **{identities} grupos de identidades AMDB indexados**. Es una métrica interna del catálogo, **no un recuento verificado de títulos de anime únicos**.",
        "metric": "Indicador",
        "value": "Valor",
        "labels": [
            "Grupos de identidades AMDB indexados",
            "Espacios de ID",
            "Datasets de origen",
            "Relaciones aceptadas",
            "Rutas dirigidas seguras",
            "Conflictos dirigidos",
            "Registros de origen",
            "Relaciones de evidencia",
            "Tamaño SQLite",
            "SQLite comprimido",
        ],
        "bench": "Velocidad de consulta local",
        "bench_note": "Consultas secuenciales MappingResolver con caché caliente sobre SQLite publicada, {environment}. {sampled} IDs × {rounds} rondas. No es latencia de red/API.",
        "speed": [
            "Mediana",
            "Media",
            "p95",
            "p99",
            "Consultas secuenciales/s",
        ],
        "snapshot": "Versión de referencia",
        "latest": "Manifiesto actual",
        "pending": "No existe un benchmark para esta instantánea.",
    },
    "fr": {
        "title": "La base en chiffres",
        "sub": "Cette version contient **{identities} groupes d'identités AMDB indexés**. Il s'agit d'une mesure de la base, **pas du nombre vérifié de titres d'anime distincts**.",
        "metric": "Indicateur",
        "value": "Valeur",
        "labels": [
            "Groupes d'identités AMDB indexés",
            "Espaces d'ID fournisseurs",
            "Jeux sources",
            "Liens acceptés",
            "Routes dirigées sûres",
            "Conflits directionnels",
            "Enregistrements sources",
            "Relations de preuves",
            "Taille SQLite",
            "SQLite compressée",
        ],
        "bench": "Performance des recherches locales",
        "bench_note": "Appels séquentiels MappingResolver sur SQLite publiée avec cache chaud, {environment}. {sampled} IDs × {rounds} tours ; pas de latence réseau/API.",
        "speed": [
            "Médiane",
            "Moyenne",
            "p95",
            "p99",
            "Requêtes séquentielles/s",
        ],
        "snapshot": "Instantané de version",
        "latest": "Manifeste actuel",
        "pending": "Aucune mesure publiée pour cet instantané.",
    },
    "it": {
        "title": "Il database in numeri",
        "sub": "Questa versione contiene **{identities} gruppi di identità AMDB indicizzati**. È una misura del database, **non un conteggio verificato di titoli anime unici**.",
        "metric": "Indicatore",
        "value": "Valore",
        "labels": [
            "Gruppi di identità AMDB indicizzati",
            "Namespace di ID",
            "Dataset sorgenti",
            "Collegamenti accettati",
            "Percorsi diretti sicuri",
            "Conflitti direzionali",
            "Record sorgenti",
            "Relazioni di prova",
            "Dimensione SQLite",
            "SQLite compresso",
        ],
        "bench": "Prestazioni di ricerca locale",
        "bench_note": "Query sequenziali MappingResolver con cache calda sul DB della release, {environment}. {sampled} ID × {rounds} round; non misura la latenza delle API.",
        "speed": [
            "Mediana",
            "Media",
            "p95",
            "p99",
            "Query sequenziali/s",
        ],
        "snapshot": "Snapshot della release",
        "latest": "Manifest attuale",
        "pending": "Nessun benchmark disponibile per questo snapshot.",
    },
}


def display_num(value: int) -> str:
    return f"{value:,}"


def mib(value: int) -> str:
    return f"{value / (1024 * 1024):,.1f} MiB"


def read_entities(path: Path) -> int:
    if not path.is_file():
        raise ValueError(f"Runtime database does not exist: {path}")
    with sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True) as db:
        count = int(db.execute("SELECT COUNT(*) FROM entities").fetchone()[0])
    if count <= 0:
        raise ValueError("Runtime database contains no AMDB entities")
    return count


def render_stats(
    manifest: dict[str, Any],
    entities: int,
    performance: dict[str, Any] | None,
    locale: str,
) -> str:
    t = WORDS[locale]
    tag = str(manifest.get("release_tag", ""))
    if not re.fullmatch(r"v[A-Za-z0-9_.-]+", tag):
        raise ValueError(f"Invalid release tag: {tag!r}")
    counts = manifest["counts"]
    providers = manifest["providers"]
    assets = manifest["assets"]
    rows = [
        entities,
        len(providers),
        counts["datasets"],
        counts["accepted_edges"],
        manifest["text_export"]["rows"],
        counts["conflicts"],
        counts["records"],
        counts["evidence"],
    ]
    metrics = [display_num(int(item)) for item in rows] + [
        mib(int(assets["runtime"]["size"])),
        mib(int(assets["runtime_zstd"]["size"])),
    ]
    lines = [
        BEGIN,
        f"## {t['title']}",
        "",
        t["sub"].format(identities=display_num(entities)),
        "",
        f"| {t['metric']} | {t['value']} |",
        "| --- | ---: |",
    ]
    lines.extend(
        f"| {label} | **{value}** |"
        for label, value in zip(t["labels"], metrics, strict=True)
    )
    lines.extend(["", f"### {t['bench']}", ""])
    if performance is None:
        lines.append(str(t["pending"]))
    else:
        if int(performance["database_bytes"]) != int(assets["runtime"]["size"]):
            raise ValueError("Benchmark file belongs to a different runtime asset")
        label = t["speed"]
        vals = [
            f"{float(performance[k]):.3f} ms"
            for k in ("median_ms", "mean_ms", "p95_ms", "p99_ms")
        ]
        vals.append(display_num(round(float(performance["lookups_per_second"]))))
        lines.extend([f"| {t['metric']} | {t['value']} |", "| --- | ---: |"])
        lines.extend(
            f"| {name} | **{value}** |" for name, value in zip(label, vals, strict=True)
        )
        lines.extend(
            [
                "",
                t["bench_note"].format(
                    environment=performance.get("environment", "CPython / Linux"),
                    sampled=performance["sampled_ids"],
                    rounds=performance["rounds"],
                ),
            ]
        )
    date = str(manifest["built_at"]).split("T")[0]
    url = f"https://github.com/{REPO}/releases/tag/{tag}"
    latest = f"https://github.com/{REPO}/releases/latest/download/manifest.json"
    lines.extend(
        [
            "",
            f"{t['snapshot']}: **{date}**, [{tag}]({url}). [{t['latest']}]({latest}).",
            "",
            END,
            "",
        ]
    )
    return "\n".join(lines)


def refresh_readmes(
    root: Path,
    manifest: dict[str, Any],
    runtime: Path,
    performance: dict[str, Any] | None,
    check: bool = False,
) -> list[str]:
    entities = read_entities(runtime)
    replacements: list[tuple[Path, str]] = []
    changed: list[str] = []
    for locale in LANGUAGES:
        path = root / ("README.md" if locale == "en" else f"docs/README.{locale}.md")
        current = path.read_text(encoding="utf-8")
        section = render_stats(manifest, entities, performance, locale)
        if BEGIN in current or END in current:
            if current.count(BEGIN) != 1 or current.count(END) != 1:
                raise ValueError(f"Broken generated block markers in {path}")
            start = current.index(BEGIN)
            finish = current.index(END, start) + len(END)
            # The block owns its trailing newline; avoid accumulating whitespace.
            updated = current[:start] + section.rstrip("\n") + current[finish:]
        else:
            title = str(WORDS[locale]["title"])
            pattern = re.compile(
                rf"^## {re.escape(title)}\n.*?(?=^## |\Z)", re.M | re.S
            )
            if len(pattern.findall(current)) != 1:
                raise ValueError(f"Statistics section missing or duplicated: {path}")
            updated = pattern.sub(lambda _: section + "\n", current, count=1)
        replacements.append((path, updated))
        if updated != current:
            changed.append(str(path.relative_to(root)))
    if not check:
        for path, updated in replacements:
            if path.read_text(encoding="utf-8") != updated:
                path.write_text(updated, encoding="utf-8")
    return changed


def main() -> int:
    p = argparse.ArgumentParser(
        description="Generate all seven mapping README statistics blocks"
    )
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--performance", type=Path)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    manifest = json.loads(a.manifest.read_text(encoding="utf-8"))
    perf = (
        json.loads(a.performance.read_text(encoding="utf-8")) if a.performance else None
    )
    changed = refresh_readmes(a.root, manifest, a.runtime, perf, check=a.check)
    print(
        f"README statistics: {len(changed)} changes ({', '.join(changed) or 'up to date'})"
    )
    return 1 if a.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
