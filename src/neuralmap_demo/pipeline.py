from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import hashlib
import json
import re


@dataclass(frozen=True)
class NormalizedConversation:
    conversation_id: str
    title: str
    root_node_id: str


@dataclass(frozen=True)
class NormalizedNode:
    conversation_id: str
    node_id: str
    parent_id: str | None
    message_id: str | None


@dataclass(frozen=True)
class NormalizedMessage:
    conversation_id: str
    node_id: str
    message_id: str
    role: str
    text: str


@dataclass(frozen=True)
class TextSpan:
    span_id: str
    conversation_id: str
    message_id: str
    text: str
    start_offset: int
    end_offset: int
    sha256: str


@dataclass(frozen=True)
class GraphEdge:
    conversation_id: str
    parent_node_id: str
    child_node_id: str


@dataclass(frozen=True)
class ExchangeUnit:
    exchange_id: str
    conversation_id: str
    user_message_id: str
    assistant_message_id: str | None
    user_text: str
    assistant_text: str | None
    source_node_path: list[str]


@dataclass(frozen=True)
class SemanticBoundary:
    boundary_id: str
    previous_exchange_id: str
    current_exchange_id: str
    label: str
    reason: str


def _stable_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def load_archive(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_archive(archive: dict):
    conversations = []
    nodes = []
    messages = []
    spans = []
    edges = []

    for conv in archive["conversations"]:
        cid = conv["conversation_id"]
        conversations.append(
            NormalizedConversation(cid, conv["title"], conv["root_node_id"])
        )

        for node in conv["nodes"]:
            msg = node.get("message")
            mid = msg["message_id"] if msg else None
            nodes.append(NormalizedNode(cid, node["node_id"], node["parent_id"], mid))

            if node["parent_id"] is not None:
                edges.append(GraphEdge(cid, node["parent_id"], node["node_id"]))

            if msg:
                text = msg["text"]
                messages.append(
                    NormalizedMessage(cid, node["node_id"], mid, msg["role"], text)
                )
                spans.append(
                    TextSpan(
                        span_id=_stable_hash(cid, mid, text)[:16],
                        conversation_id=cid,
                        message_id=mid,
                        text=text,
                        start_offset=0,
                        end_offset=len(text),
                        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    )
                )

    return conversations, nodes, messages, spans, edges


def build_exchanges(archive: dict, messages: list[NormalizedMessage]) -> list[ExchangeUnit]:
    by_node = {m.node_id: m for m in messages}
    exchanges: list[ExchangeUnit] = []

    for conv in archive["conversations"]:
        path = conv["selected_path"]
        i = 0
        while i < len(path):
            node_id = path[i]
            msg = by_node.get(node_id)

            if not msg or msg.role != "user":
                i += 1
                continue

            assistant = None
            source_path = [node_id]

            if i + 1 < len(path):
                next_node = path[i + 1]
                next_msg = by_node.get(next_node)
                if next_msg and next_msg.role == "assistant":
                    assistant = next_msg
                    source_path.append(next_node)
                    i += 1

            exchanges.append(
                ExchangeUnit(
                    exchange_id=f"{conv['conversation_id']}-ex-{len(exchanges)+1:03d}",
                    conversation_id=conv["conversation_id"],
                    user_message_id=msg.message_id,
                    assistant_message_id=assistant.message_id if assistant else None,
                    user_text=msg.text,
                    assistant_text=assistant.text if assistant else None,
                    source_node_path=source_path,
                )
            )
            i += 1

    return exchanges


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2
    }


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def label_boundaries(exchanges: list[ExchangeUnit]) -> list[SemanticBoundary]:
    """
    Illustrative public-demo heuristic only.
    This is not the private production segmentation policy.
    """
    results: list[SemanticBoundary] = []

    for prev, cur in zip(exchanges, exchanges[1:]):
        text = cur.user_text.lower()

        if "anyway, back to" in text or "back to viridian" in text:
            label = "RESUME"
            reason = "explicit return language"
        elif "random aside" in text or text.startswith("aside"):
            label = "ASIDE"
            reason = "explicit aside language"
        elif "switching topics" in text:
            label = "SHIFT"
            reason = "explicit activity-shift language"
        else:
            overlap = _jaccard(prev.user_text, cur.user_text)
            label = "SAME" if overlap >= 0.05 else "SAME"
            reason = f"illustrative continuity default; lexical overlap={overlap:.3f}"

        results.append(
            SemanticBoundary(
                boundary_id=f"b-{len(results)+1:03d}",
                previous_exchange_id=prev.exchange_id,
                current_exchange_id=cur.exchange_id,
                label=label,
                reason=reason,
            )
        )

    return results


def write_jsonl(path: Path, rows: Iterable[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(asdict(row), ensure_ascii=False, sort_keys=True) + "\n")


def run_demo(data_path: Path, out_dir: Path) -> dict:
    archive = load_archive(data_path)
    conversations, nodes, messages, spans, edges = normalize_archive(archive)
    exchanges = build_exchanges(archive, messages)
    boundaries = label_boundaries(exchanges)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "normalized_conversations.jsonl", conversations)
    write_jsonl(out_dir / "normalized_nodes.jsonl", nodes)
    write_jsonl(out_dir / "normalized_messages.jsonl", messages)
    write_jsonl(out_dir / "text_spans.jsonl", spans)
    write_jsonl(out_dir / "graph_edges.jsonl", edges)
    write_jsonl(out_dir / "exchange_units.jsonl", exchanges)
    write_jsonl(out_dir / "semantic_boundaries.jsonl", boundaries)

    summary = {
        "conversations": len(conversations),
        "nodes": len(nodes),
        "messages": len(messages),
        "text_spans": len(spans),
        "graph_edges": len(edges),
        "exchange_units": len(exchanges),
        "semantic_boundaries": len(boundaries),
        "labels": {label: sum(1 for b in boundaries if b.label == label)
                   for label in ["SAME", "SHIFT", "ASIDE", "RESUME"]},
    }

    report = [
        "# NeuralMap Public Demo Report",
        "",
        "Synthetic data only.",
        "",
        "## Counts",
        "",
    ]
    for key, value in summary.items():
        if key != "labels":
            report.append(f"- **{key}:** {value}")
    report += ["", "## Boundary labels", ""]
    for key, value in summary["labels"].items():
        report.append(f"- **{key}:** {value}")
    report += [
        "",
        "## Design note",
        "",
        "The segmentation logic in this repository is intentionally simple and deterministic.",
        "It demonstrates architecture and provenance, not the private production policy.",
        "",
    ]
    (out_dir / "demo-report.md").write_text("\n".join(report), encoding="utf-8")

    return summary
