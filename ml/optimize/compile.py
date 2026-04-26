import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent.parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

import dspy

from parser.modules import ConcertProgramParser
from eval.metrics import program_f1, program_f1_v2

DEFAULT_TRAINSET_PATH = ML_DIR / "data" / "dataset.train30.json"
DEFAULT_OUTPUT_PATH = ML_DIR / "optimize" / "compiled_program.json"
WORK_IDENTIFIER_PATTERN = re.compile(
    r"\b(op\.?\s*\d+|no\.?\s*\d+|bwv\s*\d+|k\.?\s*\d+|rv\s*\d+|s\.?\s*\d+|d\.?\s*\d+)\b",
    re.IGNORECASE,
)
PROGRAM_CUE_PATTERN = re.compile(
    r"\b(symphony|concerto|sonata|suite|quartet|trio|overture|etude|fantasia|교향곡|협주곡|소나타|모음곡|환상곡)\b",
    re.IGNORECASE,
)
PROGRAM_SECTION_MARKER = re.compile(r"\[(?:program|프로그램)\]", re.IGNORECASE)


def setup_lm() -> None:
    import os

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    lm = dspy.LM(
        "openrouter/google/gemini-2.5-flash",
        api_key=api_key,
    )
    dspy.configure(lm=lm)


def preprocess_detail_text(raw_text: str) -> str:
    text = raw_text or ""
    marker = PROGRAM_SECTION_MARKER.search(text)
    if marker:
        text = text[marker.end():]

    if "※" in text:
        text = text.split("※", 1)[0]

    text = " ".join(text.split())
    return text.strip()


def has_work_identifier(text: str) -> bool:
    return bool(WORK_IDENTIFIER_PATTERN.search(text or ""))


def has_program_cue(text: str) -> bool:
    return bool(PROGRAM_CUE_PATTERN.search(text or ""))


def validate_preprocessed_text(raw_text: str, preprocessed_text: str, min_retention: float, max_retention: float) -> tuple[bool, str]:
    if not preprocessed_text.strip():
        return False, "empty_after_preprocess"

    raw_len = max(1, len(raw_text))
    retention = len(preprocessed_text) / raw_len
    if retention < min_retention or retention > max_retention:
        return False, f"retention_ratio_out_of_range:{retention:.2f}"

    if has_work_identifier(raw_text) and not has_work_identifier(preprocessed_text):
        return False, "lost_work_identifier"

    if has_program_cue(raw_text) and not has_program_cue(preprocessed_text):
        return False, "lost_program_cue"

    return True, "ok"


def apply_preprocessing(
    raw_text: str,
    mode: str,
    min_retention: float,
    max_retention: float,
) -> tuple[str, bool, str]:
    if mode == "off":
        return raw_text, False, "mode_off"

    candidate = preprocess_detail_text(raw_text)
    valid, reason = validate_preprocessed_text(raw_text, candidate, min_retention, max_retention)

    if mode == "shadow":
        if valid:
            return raw_text, False, "shadow_pass"
        return raw_text, False, f"shadow_fallback:{reason}"

    if valid:
        return candidate, True, "applied"

    return raw_text, False, reason


def print_preprocess_summary(mode: str, counters: Counter, reasons: Counter) -> None:
    if mode == "off":
        return

    print("=== Preprocess summary (compile trainset) ===")
    print(f"mode: {mode}")
    print(f"attempted: {counters.get('attempted', 0)}")
    print(f"applied: {counters.get('applied', 0)}")
    print(f"fallback: {counters.get('fallback', 0)}")
    if reasons:
        print("top_reasons:")
        for reason, count in reasons.most_common(5):
            print(f"  {reason}: {count}")


def to_examples(
    dataset_items: list[dict],
    preprocess_mode: str,
    preprocess_min_retention: float,
    preprocess_max_retention: float,
) -> tuple[list[dspy.Example], Counter, Counter]:
    examples = []
    preprocess_counters: Counter = Counter()
    preprocess_reasons: Counter = Counter()

    for item in dataset_items:
        raw_text = item.get("input") or item.get("detail_text") or ""
        detail_text, applied, reason = apply_preprocessing(
            raw_text,
            mode=preprocess_mode,
            min_retention=preprocess_min_retention,
            max_retention=preprocess_max_retention,
        )

        if preprocess_mode != "off":
            preprocess_counters["attempted"] += 1
            if applied:
                preprocess_counters["applied"] += 1
            elif reason != "shadow_pass":
                preprocess_counters["fallback"] += 1
            preprocess_reasons[reason] += 1

        programs = item.get("programs", [])
        examples.append(
            dspy.Example(
                detail_text=detail_text,
                programs=programs,
                sn=str(item.get("sn", "")),
                title=item.get("title", ""),
            ).with_inputs("detail_text")
        )

    return examples, preprocess_counters, preprocess_reasons


def metric_v1(example, pred, trace=None) -> float:
    pred_programs = [p.model_dump() for p in getattr(pred, "programs", [])]
    gold_programs = example.programs
    scores = program_f1(pred_programs, gold_programs)
    return scores["f1"]


def metric_v2(example, pred, trace=None) -> float:
    pred_programs = [p.model_dump() for p in getattr(pred, "programs", [])]
    gold_programs = example.programs
    scores = program_f1_v2(pred_programs, gold_programs)
    return scores["f1"]


def select_metric(metric_version: str):
    if metric_version == "v2":
        return metric_v2
    return metric_v1


def main() -> None:
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--trainset", default=str(DEFAULT_TRAINSET_PATH), help="골드 데이터셋 JSON")
    argparser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="컴파일된 프로그램 출력 경로")
    argparser.add_argument("--optimizer", choices=["bootstrap", "mipro"], default="bootstrap")
    argparser.add_argument("--metric-version", choices=["v1", "v2"], default="v1", help="컴파일 목적 함수 메트릭 버전")
    argparser.add_argument("--max-bootstrapped-demos", type=int, default=4)
    argparser.add_argument("--max-labeled-demos", type=int, default=8)
    argparser.add_argument("--max-rounds", type=int, default=1)
    argparser.add_argument("--auto", choices=["light", "medium", "heavy"], default="light")
    argparser.add_argument("--preprocess-mode", choices=["off", "shadow", "on"], default="off", help="학습 입력 전처리 모드")
    argparser.add_argument("--preprocess-min-retention", type=float, default=0.7, help="전처리 후 최소 길이 비율")
    argparser.add_argument("--preprocess-max-retention", type=float, default=1.3, help="전처리 후 최대 길이 비율")
    args = argparser.parse_args()

    setup_lm()
    selected_metric = select_metric(args.metric_version)

    with open(args.trainset, encoding="utf-8") as f:
        dataset_items = json.load(f)

    trainset, preprocess_counters, preprocess_reasons = to_examples(
        dataset_items,
        preprocess_mode=args.preprocess_mode,
        preprocess_min_retention=args.preprocess_min_retention,
        preprocess_max_retention=args.preprocess_max_retention,
    )
    if not trainset:
        raise ValueError("Trainset is empty")

    print_preprocess_summary(args.preprocess_mode, preprocess_counters, preprocess_reasons)

    student = ConcertProgramParser()

    if args.optimizer == "bootstrap":
        optimizer = dspy.BootstrapFewShot(
            metric=selected_metric,
            max_bootstrapped_demos=args.max_bootstrapped_demos,
            max_labeled_demos=args.max_labeled_demos,
            max_rounds=args.max_rounds,
        )
        compiled = optimizer.compile(student=student, trainset=trainset)
    else:
        optimizer = dspy.MIPROv2(
            metric=selected_metric,
            auto=args.auto,
            max_bootstrapped_demos=args.max_bootstrapped_demos,
            max_labeled_demos=args.max_labeled_demos,
        )
        compiled = optimizer.compile(student, trainset=trainset)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    compiled.save(str(output_path))

    print(f"Compiled program saved to {output_path} (metric={args.metric_version})")


if __name__ == "__main__":
    main()
