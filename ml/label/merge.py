"""
병합 스크립트: data/labeled/*.json 개별 파일을 data/dataset.json 으로 합침.

Usage:
    cd ml && python label/merge.py
    cd ml && python label/merge.py --output data/dataset.json
"""

import argparse
import json
from pathlib import Path

ML_DIR = Path(__file__).parent.parent
DATA_DIR = ML_DIR / "data"
LABELED_DIR = DATA_DIR / "labeled"
DEFAULT_OUTPUT_PATH = DATA_DIR / "dataset.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge labeled JSON files into a gold dataset")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output dataset path")
    args = parser.parse_args()

    output_path = Path(args.output)

    label_files = sorted(LABELED_DIR.glob("*.json"))
    if not label_files:
        print(f"No labeled files found in {LABELED_DIR}")
        return

    dataset = []
    for path in label_files:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        dataset.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Merged {len(dataset)} records -> {output_path}")


if __name__ == "__main__":
    main()
