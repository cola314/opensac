"""
검증 스크립트: dataset.json 의 composer를 Open Opus 작곡가 목록과 fuzzy match.

Usage:
    cd ml && python label/validate.py
    cd ml && python label/validate.py --threshold 0.7
"""

import argparse
import json
from difflib import SequenceMatcher
from pathlib import Path

ML_DIR = Path(__file__).parent.parent
DATA_DIR = ML_DIR / "data"
DATASET_PATH = DATA_DIR / "dataset.json"
OPENOPUS_PATH = DATA_DIR / "openopus_dump.json"


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def best_match(composer: str, opus_names: list[str]) -> tuple[str, float]:
    best_name = ""
    best_score = 0.0
    for name in opus_names:
        score = similarity(composer, name)
        if score > best_score:
            best_score = score
            best_name = name
    return best_name, best_score


def load_opus_composers(path: Path) -> list[str]:
    with open(path, encoding="utf-8") as f:
        dump = json.load(f)

    composers: set[str] = set()

    # Open Opus dump structure: {"composers": [...], ...} or a list of works
    # Try common shapes
    if isinstance(dump, dict):
        if "composers" in dump:
            for c in dump["composers"]:
                if isinstance(c, dict):
                    for key in ("name", "complete_name", "full_name"):
                        if key in c:
                            composers.add(c[key])
                elif isinstance(c, str):
                    composers.add(c)
        elif "works" in dump:
            for w in dump["works"]:
                if isinstance(w, dict) and "composer" in w:
                    c = w["composer"]
                    if isinstance(c, dict):
                        for key in ("name", "complete_name"):
                            if key in c:
                                composers.add(c[key])
                    elif isinstance(c, str):
                        composers.add(c)
    elif isinstance(dump, list):
        for item in dump:
            if isinstance(item, dict):
                # could be a work with nested composer, or a composer directly
                if "composer" in item:
                    c = item["composer"]
                    if isinstance(c, dict):
                        for key in ("name", "complete_name"):
                            if key in c:
                                composers.add(c[key])
                    elif isinstance(c, str):
                        composers.add(c)
                for key in ("name", "complete_name"):
                    if key in item:
                        composers.add(item[key])

    return sorted(composers)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate composers against Open Opus")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Fuzzy match threshold (0-1, default 0.6)",
    )
    args = parser.parse_args()

    if not DATASET_PATH.exists():
        print(f"dataset.json not found at {DATASET_PATH}. Run merge.py first.")
        return

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    opus_names = load_opus_composers(OPENOPUS_PATH)
    if not opus_names:
        print("Warning: could not extract any composer names from openopus_dump.json")
        return

    print(f"Open Opus composers loaded: {len(opus_names)}")

    # Collect all unique composers from dataset
    composer_set: set[str] = set()
    for record in dataset:
        for prog in record.get("programs", []):
            composer = prog.get("composer", "").strip()
            if composer:
                composer_set.add(composer)

    composers_list = sorted(composer_set)
    print(f"Unique composers in dataset: {len(composers_list)}")
    print(f"Fuzzy match threshold: {args.threshold}\n")

    matched = []
    unmatched = []

    for composer in composers_list:
        best_name, best_score = best_match(composer, opus_names)
        if best_score >= args.threshold:
            matched.append((composer, best_name, best_score))
        else:
            unmatched.append((composer, best_name, best_score))

    total = len(composers_list)
    match_count = len(matched)
    print(f"Results: {match_count}/{total} matched ({match_count/total*100:.1f}%)")
    print(f"Unmatched: {len(unmatched)}/{total} ({len(unmatched)/total*100:.1f}%)\n")

    if unmatched:
        print("=== Unmatched composers ===")
        for composer, best_name, best_score in sorted(unmatched, key=lambda x: x[2], reverse=True):
            print(f"  {composer!r:40s} best={best_name!r} score={best_score:.2f}")

    if matched:
        print("\n=== Matched composers (sample, top 20) ===")
        for composer, best_name, best_score in sorted(matched, key=lambda x: x[2], reverse=True)[:20]:
            print(f"  {composer!r:40s} -> {best_name!r} score={best_score:.2f}")


if __name__ == "__main__":
    main()
