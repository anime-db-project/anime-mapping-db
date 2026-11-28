"""Create human-readable release notes and a machine-readable coverage report."""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def _connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def build_report(
    manifest: dict, runtime: Path, evidence: Path, previous: dict, performance: dict
) -> dict:
    with closing(_connect(runtime)) as conn:
        groups = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        histogram = dict(
            conn.execute(
                """
                SELECT members, COUNT(*) FROM (
                    SELECT COUNT(*) AS members FROM entity_nodes GROUP BY entity_id
                ) GROUP BY members ORDER BY members
                """
            )
        )
    with closing(_connect(evidence)) as conn:
        # Count each provider ID only once per dataset. Staging DB uses edge_evidence.
        counts = dict(
            conn.execute(
                """
                WITH membership AS (
                    SELECT record_id, a_node AS node_id FROM edge_evidence
                    UNION SELECT record_id, b_node FROM edge_evidence
                )
                SELECT d.name, COUNT(DISTINCT m.node_id)
                FROM datasets d JOIN records r ON r.dataset_id=d.id
                JOIN membership m ON m.record_id=r.id
                GROUP BY d.name
                """
            )
        )
    old_providers = previous.get("providers", {})
    old_counts = previous.get("counts", {})
    old_sources = {item["name"]: item for item in previous.get("sources", [])}
    providers = manifest["providers"]
    source_rows = []
    for item in manifest["sources"]:
        old = old_sources.get(item["name"])
        source_rows.append(
            {
                "name": item["name"],
                "distinct_ids": counts.get(item["name"], 0),
                "records": item["record_count"],
                "record_delta": item["record_count"] - old["record_count"]
                if old
                else None,
                "snapshot_changed": old is None or item["sha256"] != old["sha256"],
                "downloaded_at": item["downloaded_at"],
            }
        )
    return {
        "release_tag": manifest["release_tag"],
        "previous_release": previous.get("release_tag"),
        "amdb_groups": groups,
        "total_external_ids": sum(providers.values()),
        "namespaces": len(providers),
        "group_size_distribution": histogram,
        "counts": manifest["counts"],
        "count_deltas": {
            key: value - old_counts[key]
            for key, value in manifest["counts"].items()
            if key in old_counts
        },
        "safe_directed_routes": manifest["text_export"]["rows"],
        "providers": [
            {
                "namespace": key,
                "ids": providers.get(key, 0),
                "delta": providers.get(key, 0) - old_providers.get(key, 0)
                if previous
                else None,
            }
            for key in sorted(
                providers.keys() | old_providers.keys(),
                key=lambda key: (-providers.get(key, 0), key),
            )
        ],
        "sources": source_rows,
        "assets": {
            key: {"name": item["name"], "bytes": item["size"]}
            for key, item in manifest["assets"].items()
        },
        "performance": {
            key: performance[key]
            for key in (
                "environment",
                "sampled_ids",
                "rounds",
                "median_ms",
                "mean_ms",
                "p95_ms",
                "p99_ms",
                "lookups_per_second",
            )
        },
    }


def _delta(value: int | None) -> str:
    return "—" if value is None else f"{value:+,}"


def render(report: dict) -> str:
    counts = report["counts"]
    lines = [
        "## Database overview",
        "",
        f"**{report['amdb_groups']:,} indexed AMDB groups · "
        f"{report['total_external_ids']:,} external IDs · "
        f"{report['namespaces']} namespaces**",
        "",
        "AMDB groups are not a verified count of distinct anime works.",
        "",
        f"Comparison: {report['previous_release'] or 'first release'}.",
        "",
        "| Metric | Value | Change |",
        "| --- | ---: | ---: |",
    ]
    for key, label in (
        ("datasets", "Source datasets"),
        ("accepted_edges", "Accepted edges"),
        ("conflicts", "Directional conflicts"),
        ("records", "Source records"),
        ("evidence", "Evidence relationships"),
    ):
        lines.append(
            f"| {label} | {counts[key]:,} | {_delta(report['count_deltas'].get(key))} |"
        )
    lines.extend(
        [
            f"| Safe directed routes | {report['safe_directed_routes']:,} | — |",
            "",
            "## Coverage by namespace",
            "",
            "| Namespace | IDs | Change |",
            "| --- | ---: | ---: |",
        ]
    )
    for item in report["providers"]:
        lines.append(
            f"| {item['namespace']} | {item['ids']:,} | {_delta(item['delta'])} |"
        )
    lines.extend(
        [
            "",
            "## Source contributions",
            "",
            "Distinct IDs within each input; totals overlap and are not additive.",
            "",
            "| Dataset | IDs | Records | Record change | Snapshot |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for item in report["sources"]:
        status = "changed" if item["snapshot_changed"] else "unchanged"
        lines.append(
            f"| {item['name']} | {item['distinct_ids']:,} | "
            f"{item['records']:,} | {_delta(item['record_delta'])} | {status} |"
        )
    lines.extend(["", "## Assets", "", "| File | Size (MiB) |", "| --- | ---: |"])
    for item in report["assets"].values():
        lines.append(f"| {item['name']} | {item['bytes'] / 1048576:.2f} |")
    perf = report["performance"]
    lines.extend(
        [
            "",
            "## Local lookup performance",
            "",
            f"Median **{perf['median_ms']:.3f} ms**, mean {perf['mean_ms']:.3f} ms, "
            f"p95 {perf['p95_ms']:.3f} ms, p99 {perf['p99_ms']:.3f} ms; "
            f"**{perf['lookups_per_second']:,.0f} queries/s**.",
            "",
            f"Warm-cache sequential lookups; {perf['environment']}, "
            f"{perf['sampled_ids']} IDs × {perf['rounds']} rounds. Not API latency.",
            "",
            "Full machine-readable coverage: statistics.json. Provenance: manifest.json. "
            "Verify assets against SHA256SUMS.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in (
        "manifest", "runtime", "evidence", "previous", "performance", "output", "notes"
    ):
        parser.add_argument(f"--{arg}", required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    previous = json.loads(args.previous.read_text(encoding="utf-8"))
    performance = json.loads(args.performance.read_text(encoding="utf-8"))
    report = build_report(manifest, args.runtime, args.evidence, previous, performance)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.notes.write_text(render(report), encoding="utf-8")


if __name__ == "__main__":
    main()
