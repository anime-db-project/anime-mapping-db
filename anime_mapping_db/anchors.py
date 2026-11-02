from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

ANCHOR_NAMESPACE = "amdb"
ANCHOR_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class AnchorBuildStats:
    entities: int
    nodes: int
    reused: int
    created: int
    merged: int
    redirects: int
    split_components: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AnchorIdentity:
    entity_id: int
    anchor_id: int

    @property
    def reference(self) -> str:
        return format_anchor(self.anchor_id)


def format_anchor(anchor_id: int) -> str:
    value = int(anchor_id)
    if value <= 0:
        raise ValueError("anchor_id must be positive")
    return f"{ANCHOR_NAMESPACE}:{value}"


def parse_anchor(value: int | str) -> int:
    if isinstance(value, int):
        anchor_id = value
    else:
        text = str(value).strip().casefold()
        prefix = f"{ANCHOR_NAMESPACE}:"
        if text.startswith(prefix):
            text = text[len(prefix) :]
        if not text.isdigit():
            raise ValueError(f"invalid anchor reference: {value!r}")
        anchor_id = int(text)
    if anchor_id <= 0:
        raise ValueError("anchor_id must be positive")
    return anchor_id


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def _has_anchor_schema(conn: sqlite3.Connection) -> bool:
    return {"entities", "entity_nodes", "anchor_redirects"}.issubset(_tables(conn))


def _existing_stats(conn: sqlite3.Connection) -> AnchorBuildStats | None:
    if not _has_anchor_schema(conn):
        return None
    try:
        entities = int(conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0])
        nodes = int(conn.execute("SELECT COUNT(*) FROM entity_nodes").fetchone()[0])
        redirects = int(
            conn.execute("SELECT COUNT(*) FROM anchor_redirects").fetchone()[0]
        )
        graph_nodes = int(conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
        schema = conn.execute(
            "SELECT value FROM metadata WHERE key='anchor_schema_version'"
        ).fetchone()
    except sqlite3.DatabaseError:
        return None
    if schema is None or str(schema[0]) != str(ANCHOR_SCHEMA_VERSION):
        return None
    if nodes != graph_nodes:
        return None
    return AnchorBuildStats(
        entities=entities,
        nodes=nodes,
        reused=entities,
        created=0,
        merged=0,
        redirects=redirects,
        split_components=0,
    )


def _load_anchor_state(
    path: Path | None,
) -> tuple[dict[tuple[str, str], int], dict[int, int], int]:
    if path is None:
        return {}, {}, 0
    path = Path(path)
    if not path.is_file():
        return {}, {}, 0
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=10.0)) as conn:
            if not _has_anchor_schema(conn):
                return {}, {}, 0
            node_to_anchor = {
                (str(provider), str(external_id)): int(anchor_id)
                for provider, external_id, anchor_id in conn.execute(
                    """
                    SELECT n.provider, n.external_id, e.anchor_id
                    FROM entity_nodes AS en
                    JOIN entities AS e ON e.entity_id=en.entity_id
                    JOIN nodes AS n ON n.id=en.node_id
                    """
                )
            }
            redirects = {
                int(old_anchor): int(anchor)
                for old_anchor, anchor in conn.execute(
                    "SELECT old_anchor_id, anchor_id FROM anchor_redirects"
                )
            }
            maximum = max(
                [0, *node_to_anchor.values(), *redirects.keys(), *redirects.values()]
            )
            return node_to_anchor, redirects, maximum
    except sqlite3.DatabaseError:
        return {}, {}, 0


def _union_find_components(conn: sqlite3.Connection) -> list[list[int]]:
    node_rows = conn.execute("SELECT id, provider FROM nodes ORDER BY id").fetchall()
    parent = {int(node_id): int(node_id) for node_id, _provider in node_rows}
    rank = {node_id: 0 for node_id in parent}
    providers = {int(node_id): str(provider) for node_id, provider in node_rows}
    component_providers = {
        int(node_id): {str(provider)} for node_id, provider in node_rows
    }

    def find(node: int) -> int:
        root = node
        while parent[root] != root:
            root = parent[root]
        while parent[node] != node:
            next_node = parent[node]
            parent[node] = root
            node = next_node
        return root

    def union(left: int, right: int) -> bool:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return True
        # A project entity represents one catalog entry per provider. Refuse a
        # transitive merge that would collapse two MAL/AniList/etc. titles into
        # one entity even when pairwise mapping edges happen to connect them.
        if component_providers[left_root] & component_providers[right_root]:
            return False
        if rank[left_root] < rank[right_root]:
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root
        component_providers[left_root].update(component_providers[right_root])
        component_providers.pop(right_root, None)
        if rank[left_root] == rank[right_root]:
            rank[left_root] += 1
        return True

    conflicts = {
        (int(source_node), str(target_provider))
        for source_node, target_provider in conn.execute(
            "SELECT source_node, target_provider FROM conflicts"
        )
    }
    rejected: set[tuple[int, int]] = set()
    accepted_overrides: set[tuple[int, int]] = set()
    try:
        override_rows = conn.execute(
            """
            SELECT source.id, target.id, o.action
            FROM mapping_overrides AS o
            JOIN nodes AS source
              ON source.provider=o.source_provider AND source.external_id=o.source_id
            JOIN nodes AS target
              ON target.provider=o.target_provider AND target.external_id=o.target_id
            WHERE o.action IN ('accept', 'reject')
            """
        )
    except sqlite3.OperationalError:
        override_rows = ()
    for source_node, target_node, action in override_rows:
        pair = tuple(sorted((int(source_node), int(target_node))))
        if str(action) == "reject":
            rejected.add(pair)
        else:
            accepted_overrides.add(pair)

    for a_node, b_node in conn.execute(
        """
        SELECT a_node, b_node
        FROM edges
        WHERE status='accepted'
        ORDER BY confidence DESC, evidence_group_count DESC, max_weight DESC,
                 a_node, b_node
        """
    ):
        left, right = int(a_node), int(b_node)
        pair = tuple(sorted((left, right)))
        if pair in rejected:
            continue
        if (left, providers[right]) in conflicts:
            continue
        if (right, providers[left]) in conflicts:
            continue
        union(left, right)

    for left, right in accepted_overrides:
        union(left, right)

    grouped: dict[int, list[int]] = defaultdict(list)
    for node_id in parent:
        grouped[find(node_id)].append(node_id)
    return [sorted(nodes) for nodes in grouped.values()]


def _component_keys(
    conn: sqlite3.Connection, components: Iterable[list[int]]
) -> list[tuple[tuple[tuple[str, str], ...], list[int]]]:
    identities = {
        int(node_id): (str(provider), str(external_id))
        for node_id, provider, external_id in conn.execute(
            "SELECT id, provider, external_id FROM nodes"
        )
    }
    result = []
    for nodes in components:
        signature = tuple(sorted(identities[node_id] for node_id in nodes))
        result.append((signature, nodes))
    result.sort(key=lambda item: item[0])
    return result


def _collapse_redirect(anchor: int, redirects: Mapping[int, int]) -> int:
    seen: set[int] = set()
    current = int(anchor)
    while current in redirects and current not in seen:
        seen.add(current)
        current = int(redirects[current])
    return current


def materialize_anchor_index(
    runtime_path: Path,
    *,
    previous_path: Path | None = None,
    force: bool = False,
) -> AnchorBuildStats:
    """Materialize stable project identities on top of the accepted mapping graph.

    ``entity_id`` is a dense build-local primary key. ``anchor_id`` is the public,
    stable identifier. Existing anchor assignments are reused from ``previous_path``;
    merges create redirects, while splits keep the old anchor on the component with
    the largest overlap and allocate new anchors to the remaining components.
    """

    runtime_path = Path(runtime_path)
    if not runtime_path.is_file():
        raise FileNotFoundError(runtime_path)

    previous_nodes, previous_redirects, previous_max = _load_anchor_state(previous_path)
    with closing(sqlite3.connect(runtime_path, timeout=30.0)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        if not force:
            existing = _existing_stats(conn)
            if existing is not None:
                return existing

        components = _component_keys(conn, _union_find_components(conn))
        node_identity = {
            int(node_id): (str(provider), str(external_id))
            for node_id, provider, external_id in conn.execute(
                "SELECT id, provider, external_id FROM nodes"
            )
        }

        overlaps: list[Counter[int]] = []
        anchor_candidates: dict[int, list[tuple[int, tuple[tuple[str, str], ...]]]] = (
            defaultdict(list)
        )
        for signature, nodes in components:
            counts: Counter[int] = Counter()
            for node_id in nodes:
                previous_anchor = previous_nodes.get(node_identity[node_id])
                if previous_anchor is not None:
                    counts[_collapse_redirect(previous_anchor, previous_redirects)] += 1
            overlaps.append(counts)
            for anchor_id, count in counts.items():
                anchor_candidates[anchor_id].append((count, signature))

        winners: dict[int, tuple[tuple[str, str], ...]] = {}
        for anchor_id, candidates in anchor_candidates.items():
            winners[anchor_id] = sorted(
                candidates, key=lambda item: (-item[0], item[1])
            )[0][1]

        next_anchor = previous_max + 1
        assignments: list[int] = []
        redirects = {
            int(old): _collapse_redirect(target, previous_redirects)
            for old, target in previous_redirects.items()
        }
        reused = created = merged = split_components = 0
        for (signature, _nodes), counts in zip(components, overlaps, strict=True):
            reusable = sorted(
                anchor_id for anchor_id in counts if winners.get(anchor_id) == signature
            )
            if reusable:
                anchor_id = reusable[0]
                reused += 1
                for merged_anchor in reusable[1:]:
                    redirects[merged_anchor] = anchor_id
                    merged += 1
            else:
                anchor_id = next_anchor
                next_anchor += 1
                created += 1
                if counts:
                    split_components += 1
            assignments.append(anchor_id)

        active_anchors = set(assignments)
        normalized_redirects: dict[int, int] = {}
        for old_anchor in sorted(redirects):
            target = _collapse_redirect(redirects[old_anchor], redirects)
            if old_anchor != target and target in active_anchors:
                normalized_redirects[old_anchor] = target

        conn.executescript(
            """
            DROP TABLE IF EXISTS entity_nodes;
            DROP TABLE IF EXISTS anchor_redirects;
            DROP TABLE IF EXISTS entities;

            CREATE TABLE entities (
                entity_id INTEGER PRIMARY KEY,
                anchor_id INTEGER NOT NULL UNIQUE CHECK(anchor_id > 0)
            );

            CREATE TABLE entity_nodes (
                entity_id INTEGER NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
                node_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                PRIMARY KEY(entity_id, node_id),
                UNIQUE(node_id)
            ) WITHOUT ROWID;

            CREATE TABLE anchor_redirects (
                old_anchor_id INTEGER PRIMARY KEY CHECK(old_anchor_id > 0),
                anchor_id INTEGER NOT NULL CHECK(anchor_id > 0),
                reason TEXT NOT NULL DEFAULT 'merged',
                CHECK(old_anchor_id <> anchor_id),
                FOREIGN KEY(anchor_id) REFERENCES entities(anchor_id)
            ) WITHOUT ROWID;

            CREATE INDEX anchor_redirects_target_idx
                ON anchor_redirects(anchor_id, old_anchor_id);
            """
        )

        for entity_id, ((_signature, nodes), anchor_id) in enumerate(
            zip(components, assignments, strict=True), start=1
        ):
            conn.execute(
                "INSERT INTO entities(entity_id, anchor_id) VALUES (?, ?)",
                (entity_id, anchor_id),
            )
            conn.executemany(
                "INSERT INTO entity_nodes(entity_id, node_id) VALUES (?, ?)",
                ((entity_id, node_id) for node_id in nodes),
            )

        conn.executemany(
            "INSERT INTO anchor_redirects(old_anchor_id, anchor_id, reason) VALUES (?, ?, 'merged')",
            sorted(normalized_redirects.items()),
        )

        metadata = {
            "anchor_schema_version": str(ANCHOR_SCHEMA_VERSION),
            "anchor_namespace": ANCHOR_NAMESPACE,
            "anchor_format": f"{ANCHOR_NAMESPACE}:<integer>",
            "anchor_entities": str(len(components)),
            "anchor_nodes": str(len(node_identity)),
            "anchor_redirects": str(len(normalized_redirects)),
        }
        conn.executemany(
            "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
            metadata.items(),
        )
        conn.execute("ANALYZE")
        conn.commit()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or str(integrity[0]) != "ok":
            raise RuntimeError(
                f"anchor materialization integrity check failed: {integrity!r}"
            )

    return AnchorBuildStats(
        entities=len(components),
        nodes=len(node_identity),
        reused=reused,
        created=created,
        merged=merged,
        redirects=len(normalized_redirects),
        split_components=split_components,
    )


class AnchorResolver:
    """Resolve public ``amdb:<anchor_id>`` identities without exposing entity_id."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{self.path.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10.0)
        conn.execute("PRAGMA query_only=ON")
        return conn

    def anchor_for(self, identity: Mapping[str, str]) -> AnchorIdentity | None:
        normalized = {
            str(provider).strip().casefold(): str(external_id).strip()
            for provider, external_id in identity.items()
            if str(provider).strip() and str(external_id).strip()
        }
        if not normalized or not self.path.is_file():
            return None
        with closing(self._connect()) as conn:
            found: set[tuple[int, int]] = set()
            for provider, external_id in normalized.items():
                row = conn.execute(
                    """
                    SELECT e.entity_id, e.anchor_id
                    FROM nodes AS n
                    JOIN entity_nodes AS en ON en.node_id=n.id
                    JOIN entities AS e ON e.entity_id=en.entity_id
                    WHERE n.provider=? AND n.external_id=?
                    """,
                    (provider, external_id),
                ).fetchone()
                if row is not None:
                    found.add((int(row[0]), int(row[1])))
            if len(found) != 1:
                return None
            entity_id, anchor_id = next(iter(found))
            return AnchorIdentity(entity_id=entity_id, anchor_id=anchor_id)

    def ids_for(self, anchor: int | str) -> dict[str, tuple[str, ...]]:
        anchor_id = parse_anchor(anchor)
        if not self.path.is_file():
            return {}
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT anchor_id FROM anchor_redirects WHERE old_anchor_id=?",
                (anchor_id,),
            ).fetchone()
            if row is not None:
                anchor_id = int(row[0])
            rows = conn.execute(
                """
                SELECT n.provider, n.external_id
                FROM entities AS e
                JOIN entity_nodes AS en ON en.entity_id=e.entity_id
                JOIN nodes AS n ON n.id=en.node_id
                WHERE e.anchor_id=?
                ORDER BY n.provider, n.external_id
                """,
                (anchor_id,),
            ).fetchall()
        grouped: dict[str, list[str]] = defaultdict(list)
        for provider, external_id in rows:
            grouped[str(provider)].append(str(external_id))
        return {provider: tuple(values) for provider, values in grouped.items()}
