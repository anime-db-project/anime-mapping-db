from __future__ import annotations

import argparse
import json
import random
import sqlite3
import statistics
import time
from pathlib import Path

from anime_mapping_db.resolver import MappingResolver


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark direct mappings.db ID lookups"
    )
    parser.add_argument("--db", type=Path, default=Path("data/mappings/mappings.db"))
    parser.add_argument("--samples", type=int, default=1200)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261101)
    args = parser.parse_args()

    db = args.db.resolve()
    with sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT n.provider, n.external_id
            FROM nodes AS n
            JOIN (
                SELECT a_node AS node_id FROM edges WHERE status='accepted'
                UNION
                SELECT b_node AS node_id FROM edges WHERE status='accepted'
            ) AS used ON used.node_id=n.id
            ORDER BY n.provider, n.external_id
            """
        ).fetchall()

    rng = random.Random(args.seed)
    sample_count = min(max(1, args.samples), len(rows))
    sample = rng.sample(rows, sample_count)
    resolver = MappingResolver(db)

    # Warm the OS page cache and Python code paths without including warmup in results.
    for provider, external_id in sample[: min(100, sample_count)]:
        resolver.resolve({str(provider): str(external_id)})

    timings_ms: list[float] = []
    result_sizes: list[int] = []
    for _round in range(max(1, args.rounds)):
        for provider, external_id in sample:
            start = time.perf_counter_ns()
            result = resolver.resolve({str(provider): str(external_id)})
            elapsed = time.perf_counter_ns() - start
            timings_ms.append(elapsed / 1_000_000)
            result_sizes.append(len(result))

    payload = {
        "database": str(db),
        "database_bytes": db.stat().st_size,
        "sampled_ids": sample_count,
        "rounds": max(1, args.rounds),
        "lookups": len(timings_ms),
        "median_ms": round(statistics.median(timings_ms), 4),
        "mean_ms": round(statistics.fmean(timings_ms), 4),
        "p95_ms": round(percentile(timings_ms, 0.95), 4),
        "p99_ms": round(percentile(timings_ms, 0.99), 4),
        "max_ms": round(max(timings_ms), 4),
        "mean_targets": round(statistics.fmean(result_sizes), 3),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
