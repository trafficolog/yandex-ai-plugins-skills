from __future__ import annotations

import hashlib
import re
from typing import Any


REPORT_SCHEMA = "seo-weekly-organic-report/v1"


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _mmd_text(value: Any) -> str:
    text = str(value)
    return (
        text.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace('"', '\\"')
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def _dot_text(value: Any) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace('"', '\\"')
    )


def _mmd_id(value: str, prefix: str = "n") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"{prefix}_{cleaned}"
    return f"{prefix}_{cleaned}"


def _query_id(cluster_id: str, query: str) -> str:
    return "q_" + hashlib.sha256(f"{cluster_id}\0{query}".encode("utf-8")).hexdigest()[:12]


def _tree_nodes(tree: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    nodes = tree.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("structural_tree.nodes must be a list")
    normalized: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for raw in nodes:
        if not isinstance(raw, dict):
            raise ValueError("structural node must be an object")
        page_id = _require_string(raw.get("page_id"), "structural node page_id")
        if page_id in by_id:
            raise ValueError(f"duplicate structural page_id: {page_id}")
        item = dict(raw)
        item["page_id"] = page_id
        by_id[page_id] = item
        normalized.append(item)
    normalized.sort(key=lambda item: item["page_id"])
    return normalized, by_id


def _structural_exports(tree: dict[str, Any]) -> tuple[str, str, dict[str, dict[str, Any]]]:
    nodes, by_id = _tree_nodes(tree)
    edges = tree.get("edges", [])
    if not isinstance(edges, list):
        raise ValueError("structural_tree.edges must be a list")
    normalized_edges: list[tuple[str, str]] = []
    for raw in edges:
        if not isinstance(raw, dict):
            raise ValueError("structural edge must be an object")
        parent = _require_string(raw.get("parent_page_id"), "parent_page_id")
        child = _require_string(raw.get("child_page_id"), "child_page_id")
        if parent not in by_id or child not in by_id:
            raise ValueError("structural edge references unknown page")
        normalized_edges.append((parent, child))
    normalized_edges.sort()

    mmd = ["flowchart TD"]
    dot = ["digraph structural_tree {", "  rankdir=TB;"]
    for node in nodes:
        page_id = node["page_id"]
        title = node.get("title") or node.get("url") or node.get("proposed_url") or page_id
        label = f"{page_id} · {title}"
        mmd.append(f'  {_mmd_id(page_id)}["{_mmd_text(label)}"]')
        dot.append(f'  "{_dot_text(page_id)}" [label="{_dot_text(label)}"];')
    for parent, child in normalized_edges:
        mmd.append(f"  {_mmd_id(parent)} --> {_mmd_id(child)}")
        dot.append(f'  "{_dot_text(parent)}" -> "{_dot_text(child)}";')
    dot.append("}")
    return "\n".join(mmd) + "\n", "\n".join(dot) + "\n", by_id


def _semantic_exports(graph: dict[str, Any], labels: dict[str, dict[str, Any]]) -> tuple[str, str, set[str]]:
    nodes = graph.get("nodes")
    edges = graph.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("semantic_graph nodes/edges must be lists")
    page_ids: set[str] = set()
    for raw in nodes:
        if not isinstance(raw, dict):
            raise ValueError("semantic node must be an object")
        page_id = _require_string(raw.get("page_id"), "semantic node page_id")
        if page_id in page_ids:
            raise ValueError(f"duplicate semantic page_id: {page_id}")
        page_ids.add(page_id)
    normalized_edges: list[tuple[str, str, str]] = []
    for raw in edges:
        if not isinstance(raw, dict):
            raise ValueError("semantic edge must be an object")
        source = _require_string(raw.get("from_page_id"), "from_page_id")
        target = _require_string(raw.get("to_page_id"), "to_page_id")
        relation = _require_string(raw.get("relation"), "relation")
        if source not in page_ids or target not in page_ids:
            raise ValueError("semantic edge references unknown page")
        normalized_edges.append((source, target, relation))
    normalized_edges.sort()

    mmd = ["flowchart LR"]
    dot = ["digraph semantic_graph {", "  rankdir=LR;"]
    for page_id in sorted(page_ids):
        node = labels.get(page_id, {})
        title = node.get("title") or node.get("url") or page_id
        label = f"{page_id} · {title}"
        mmd.append(f'  {_mmd_id(page_id)}["{_mmd_text(label)}"]')
        dot.append(f'  "{_dot_text(page_id)}" [label="{_dot_text(label)}"];')
    for source, target, relation in normalized_edges:
        mmd.append(f'  {_mmd_id(source)} -->|"{_mmd_text(relation)}"| {_mmd_id(target)}')
        dot.append(f'  "{_dot_text(source)}" -> "{_dot_text(target)}" [label="{_dot_text(relation)}"];')
    dot.append("}")
    return "\n".join(mmd) + "\n", "\n".join(dot) + "\n", page_ids


def _clusters_mermaid(clusters: list[dict[str, Any]]) -> str:
    normalized: list[tuple[str, str, list[str]]] = []
    for raw in clusters:
        if not isinstance(raw, dict):
            raise ValueError("cluster must be an object")
        cluster_id = _require_string(raw.get("cluster_id"), "cluster_id")
        queries = raw.get("queries")
        if not isinstance(queries, list):
            raise ValueError("cluster.queries must be a list")
        clean_queries = sorted({_require_string(query, "cluster query") for query in queries})
        label = raw.get("label") or cluster_id
        normalized.append((cluster_id, str(label), clean_queries))
    normalized.sort(key=lambda item: item[0])
    lines = ["flowchart LR"]
    for cluster_id, label, queries in normalized:
        cluster_node = _mmd_id(cluster_id, "c")
        lines.append(f'  {cluster_node}["{_mmd_text(cluster_id + " · " + label)}"]')
        for query in queries:
            query_node = _query_id(cluster_id, query)
            lines.append(f'  {query_node}["{_mmd_text(query)}"]')
            lines.append(f"  {cluster_node} --> {query_node}")
    return "\n".join(lines) + "\n"


def _links_dot(link_plan: list[dict[str, Any]], known_pages: set[str]) -> str:
    links: list[tuple[str, str, str]] = []
    for raw in link_plan:
        if not isinstance(raw, dict):
            raise ValueError("link plan item must be an object")
        source = _require_string(raw.get("from_page_id"), "link from_page_id")
        target = _require_string(raw.get("to_page_id"), "link to_page_id")
        if known_pages and (source not in known_pages or target not in known_pages):
            raise ValueError("link plan references unknown page")
        relation = _require_string(raw.get("relation"), "link relation")
        anchor = raw.get("anchor_concept")
        label = relation if anchor is None else f"{relation} · {anchor}"
        links.append((source, target, label))
    links.sort()
    lines = ["digraph internal_links {", "  rankdir=LR;"]
    for source, target, label in links:
        lines.append(f'  "{_dot_text(source)}" -> "{_dot_text(target)}" [label="{_dot_text(label)}"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def export_graphs(report: dict[str, Any]) -> dict[str, str]:
    if not isinstance(report, dict) or report.get("schema") != REPORT_SCHEMA:
        raise ValueError("unsupported weekly report schema")
    structures = report.get("structures")
    if structures is None:
        return {}
    if not isinstance(structures, dict):
        raise ValueError("structures must be an object")

    result: dict[str, str] = {}
    labels: dict[str, dict[str, Any]] = {}
    known_pages: set[str] = set()
    tree = structures.get("structural_tree")
    if tree is not None:
        if not isinstance(tree, dict):
            raise ValueError("structural_tree must be an object")
        tree_mmd, tree_dot, labels = _structural_exports(tree)
        known_pages.update(labels)
        result["diagrams/structural-tree.mmd"] = tree_mmd
        result["diagrams/structural-tree.dot"] = tree_dot

    graph = structures.get("semantic_graph")
    if graph is not None:
        if not isinstance(graph, dict):
            raise ValueError("semantic_graph must be an object")
        graph_mmd, graph_dot, semantic_pages = _semantic_exports(graph, labels)
        known_pages.update(semantic_pages)
        result["diagrams/semantic-graph.mmd"] = graph_mmd
        result["diagrams/semantic-graph.dot"] = graph_dot

    clusters = structures.get("clusters")
    if clusters is not None:
        if not isinstance(clusters, list):
            raise ValueError("clusters must be a list")
        result["diagrams/clusters.mmd"] = _clusters_mermaid(clusters)

    link_plan = structures.get("link_plan")
    if link_plan is not None:
        if not isinstance(link_plan, list):
            raise ValueError("link_plan must be a list")
        result["diagrams/internal-links.dot"] = _links_dot(link_plan, known_pages)

    return dict(sorted(result.items()))
