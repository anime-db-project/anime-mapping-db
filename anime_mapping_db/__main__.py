from __future__ import annotations

import argparse
import json
from pathlib import Path

from anime_mapping_db.anchors import materialize_anchor_index
from anime_mapping_db.config import mappings_db_path, mappings_evidence_db_path
from anime_mapping_db.release import package_release
from anime_mapping_db.updater import (
    mapping_status,
    update_mapping_database,
    update_if_stale,
)


def _previous_runtime(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".previous")


def _materialize(runtime: Path) -> dict[str, int]:
    previous = _previous_runtime(runtime)
    stats = materialize_anchor_index(
        runtime,
        previous_path=previous if previous.is_file() else None,
    )
    return stats.as_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and package Anime Mapping DB")
    sub = parser.add_subparsers(dest="command", required=False)

    build = sub.add_parser("build", help="build or refresh local mapping databases")
    build.add_argument("--force", action="store_true", help="rebuild all sources")

    sub.add_parser("status", help="print local database status")

    anchors = sub.add_parser("anchors", help="materialize stable project anchor IDs")
    anchors.add_argument("--runtime", type=Path, default=None)
    anchors.add_argument("--previous", type=Path, default=None)
    anchors.add_argument("--force", action="store_true")

    package = sub.add_parser("package-release", help="create release assets")
    package.add_argument("--tag", required=True, help="release tag written to manifest")
    package.add_argument("--output", type=Path, default=Path("release"))
    package.add_argument("--runtime", type=Path, default=None)
    package.add_argument("--evidence", type=Path, default=None)

    args = parser.parse_args()
    command = args.command or "status"
    if command == "status":
        print(
            json.dumps(mapping_status(), ensure_ascii=False, indent=2, sort_keys=True)
        )
        return
    if command == "build":
        stats = update_mapping_database(force=True) if args.force else update_if_stale()
        runtime = mappings_db_path()
        anchor_stats = _materialize(runtime)
        payload = mapping_status()
        payload["anchors"] = anchor_stats
        if stats is not None:
            payload["build"] = {
                "datasets": stats.datasets,
                "records": stats.records,
                "evidence": stats.evidence,
                "edges": stats.edges,
                "accepted_edges": stats.accepted_edges,
                "conflicts": stats.conflicts,
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if command == "anchors":
        runtime = args.runtime or mappings_db_path()
        previous = args.previous
        if previous is None:
            candidate = _previous_runtime(runtime)
            previous = candidate if candidate.is_file() else None
        stats = materialize_anchor_index(
            runtime,
            previous_path=previous,
            force=bool(args.force),
        )
        print(json.dumps(stats.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return
    if command == "package-release":
        runtime = args.runtime or mappings_db_path()
        _materialize(runtime)
        manifest = package_release(
            runtime,
            args.evidence or mappings_evidence_db_path(),
            args.output,
            release_tag=args.tag,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
        return
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
