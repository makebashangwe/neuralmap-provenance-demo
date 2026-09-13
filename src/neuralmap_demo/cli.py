from pathlib import Path
from .pipeline import run_demo


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    data_path = project_root / "data" / "synthetic_archive.json"
    out_dir = project_root / "out"

    summary = run_demo(data_path, out_dir)

    print("NeuralMap public demo complete.")
    print(f"Conversations: {summary['conversations']}")
    print(f"Nodes: {summary['nodes']}")
    print(f"Messages: {summary['messages']}")
    print(f"Exchange units: {summary['exchange_units']}")
    print(f"Boundaries: {summary['semantic_boundaries']}")
    print(f"Outputs: {out_dir}")


if __name__ == "__main__":
    main()
