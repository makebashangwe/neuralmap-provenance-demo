import json
import tempfile
import unittest
from pathlib import Path

from neuralmap_demo.pipeline import (
    build_exchanges,
    label_boundaries,
    load_archive,
    normalize_archive,
    run_demo,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "data" / "synthetic_archive.json"


class NeuralMapDemoTests(unittest.TestCase):
    def test_branch_edges_are_preserved(self):
        archive = load_archive(DATA)
        _, _, _, _, edges = normalize_archive(archive)
        pairs = {(e.parent_node_id, e.child_node_id) for e in edges}
        self.assertIn(("n1", "n2a"), pairs)
        self.assertIn(("n1", "n2b"), pairs)

    def test_selected_path_uses_second_regenerated_answer(self):
        archive = load_archive(DATA)
        _, _, messages, _, _ = normalize_archive(archive)
        exchanges = build_exchanges(archive, messages)
        self.assertEqual(exchanges[0].assistant_message_id, "m2b")

    def test_text_span_preserves_exact_text(self):
        archive = load_archive(DATA)
        _, _, messages, spans, _ = normalize_archive(archive)
        by_message = {m.message_id: m for m in messages}
        span_by_message = {s.message_id: s for s in spans}
        self.assertEqual(
            span_by_message["m1"].text,
            by_message["m1"].text,
        )
        self.assertEqual(
            span_by_message["m1"].end_offset,
            len(by_message["m1"].text),
        )

    def test_expected_boundary_labels_exist(self):
        archive = load_archive(DATA)
        _, _, messages, _, _ = normalize_archive(archive)
        exchanges = build_exchanges(archive, messages)
        boundaries = label_boundaries(exchanges)
        labels = [b.label for b in boundaries]
        self.assertIn("ASIDE", labels)
        self.assertIn("RESUME", labels)
        self.assertIn("SHIFT", labels)

    def test_run_demo_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            run_demo(DATA, Path(d1))
            run_demo(DATA, Path(d2))
            for name in [
                "normalized_conversations.jsonl",
                "normalized_nodes.jsonl",
                "normalized_messages.jsonl",
                "text_spans.jsonl",
                "graph_edges.jsonl",
                "exchange_units.jsonl",
                "semantic_boundaries.jsonl",
                "demo-report.md",
            ]:
                self.assertEqual(
                    (Path(d1) / name).read_bytes(),
                    (Path(d2) / name).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
