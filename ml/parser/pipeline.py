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

DEFAULT_INPUT_PATH = ML_DIR / "data" / "dataset.json"
DEFAULT_OUTPUT_PATH = ML_DIR / "data" / "dspy_results.json"
WORK_IDENTIFIER_PATTERN = re.compile(
    r"\b(op\.?\s*\d+|no\.?\s*\d+|bwv\s*\d+|k\.?\s*\d+|rv\s*\d+|s\.?\s*\d+|d\.?\s*\d+)\b",
    re.IGNORECASE,
)
PROGRAM_CUE_PATTERN = re.compile(
    r"\b(symphony|concerto|sonata|suite|quartet|trio|overture|etude|fantasia|교향곡|협주곡|소나타|모음곡|환상곡)\b",
    re.IGNORECASE,
)
PROGRAM_SECTION_MARKER = re.compile(r"\[(?:program|프로그램)\]", re.IGNORECASE)


def setup_lm():
    import os

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    lm = dspy.LM(
        "openrouter/google/gemini-2.5-flash",
        api_key=api_key,
    )
    dspy.configure(lm=lm)


def estimate_usage(
    items: list[dict],
    input_chars_per_token: float,
    output_chars_per_token: float,
    output_token_ratio: float,
) -> dict:
    input_chars = 0
    output_chars = 0
    output_ref_count = 0

    for item in items:
        detail_text = item.get("input") or item.get("detail_text") or ""
        input_chars += len(detail_text)

        if "programs" in item and isinstance(item.get("programs"), list):
            output_chars += len(json.dumps(item.get("programs", []), ensure_ascii=False))
            output_ref_count += 1

    est_input_tokens = input_chars / input_chars_per_token if input_chars_per_token > 0 else 0

    if output_ref_count > 0:
        est_output_tokens = output_chars / output_chars_per_token if output_chars_per_token > 0 else 0
        output_estimation_mode = "gold_reference"
    else:
        est_output_tokens = est_input_tokens * output_token_ratio
        output_estimation_mode = "ratio"

    return {
        "items": len(items),
        "input_chars": input_chars,
        "output_chars": output_chars,
        "output_ref_count": output_ref_count,
        "est_input_tokens": est_input_tokens,
        "est_output_tokens": est_output_tokens,
        "output_estimation_mode": output_estimation_mode,
    }


def print_estimate(estimate: dict, price_in_per_m: float, price_out_per_m: float) -> None:
    est_input_tokens = estimate["est_input_tokens"]
    est_output_tokens = estimate["est_output_tokens"]

    print("=== Cost estimate ===")
    print(f"items: {estimate['items']}")
    print(f"input_chars: {estimate['input_chars']}")
    print(
        f"output_estimation_mode: {estimate['output_estimation_mode']}"
        f" (reference_items={estimate['output_ref_count']})"
    )
    print(f"est_input_tokens: {est_input_tokens:.0f}")
    print(f"est_output_tokens: {est_output_tokens:.0f}")

    if price_in_per_m > 0 or price_out_per_m > 0:
        est_cost = (est_input_tokens / 1_000_000) * price_in_per_m + (est_output_tokens / 1_000_000) * price_out_per_m
        print(f"est_cost_usd: {est_cost:.6f}")
    else:
        print("est_cost_usd: (set --price-in-per-m and --price-out-per-m to enable)")


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


def print_preprocess_summary(mode: str, counters: Counter, reason_counts: Counter) -> None:
    if mode == "off":
        return

    attempted = counters.get("attempted", 0)
    applied = counters.get("applied", 0)
    fallback = counters.get("fallback", 0)

    print("\n=== Preprocess summary ===")
    print(f"mode: {mode}")
    print(f"attempted: {attempted}")
    print(f"applied: {applied}")
    print(f"fallback: {fallback}")

    if reason_counts:
        print("top_reasons:")
        for reason, count in reason_counts.most_common(5):
            print(f"  {reason}: {count}")


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--input", default=str(DEFAULT_INPUT_PATH))
    argparser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    argparser.add_argument("--limit", type=int, default=None)
    argparser.add_argument("--estimate-only", action="store_true", help="Print usage/cost estimate and exit")
    argparser.add_argument("--price-in-per-m", type=float, default=0.0, help="Input token price per 1M tokens (USD)")
    argparser.add_argument("--price-out-per-m", type=float, default=0.0, help="Output token price per 1M tokens (USD)")
    argparser.add_argument("--input-chars-per-token", type=float, default=1.5, help="Input chars per token heuristic")
    argparser.add_argument("--output-chars-per-token", type=float, default=2.0, help="Output chars per token heuristic")
    argparser.add_argument("--output-token-ratio", type=float, default=0.25, help="Output/input token ratio when gold programs are unavailable")
    argparser.add_argument("--preprocess-mode", choices=["off", "shadow", "on"], default="off", help="입력 전처리 모드")
    argparser.add_argument("--preprocess-min-retention", type=float, default=0.7, help="전처리 후 최소 길이 비율")
    argparser.add_argument("--preprocess-max-retention", type=float, default=1.3, help="전처리 후 최대 길이 비율")
    argparser.add_argument("--compiled-program", default="", help="컴파일된 DSPy 프로그램 state 경로")
    args = argparser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        items = json.load(f)

    if args.limit:
        items = items[:args.limit]

    estimate = estimate_usage(
        items,
        input_chars_per_token=args.input_chars_per_token,
        output_chars_per_token=args.output_chars_per_token,
        output_token_ratio=args.output_token_ratio,
    )
    print_estimate(estimate, args.price_in_per_m, args.price_out_per_m)

    if args.estimate_only:
        return

    setup_lm()

    preprocess_counters = Counter()
    preprocess_reasons = Counter()

    results = []
    parser = ConcertProgramParser()
    if args.compiled_program:
        compiled_path = Path(args.compiled_program)
        if not compiled_path.exists():
            raise FileNotFoundError(f"Compiled program not found: {compiled_path}")
        parser.load(str(compiled_path))
        print(f"Loaded compiled program: {compiled_path}")

    for item in items:
        sn = item.get("sn")
        title = item.get("title", "")
        detail_text_raw = item.get("input") or item.get("detail_text") or ""

        detail_text, pre_applied, pre_reason = apply_preprocessing(
            detail_text_raw,
            mode=args.preprocess_mode,
            min_retention=args.preprocess_min_retention,
            max_retention=args.preprocess_max_retention,
        )

        if args.preprocess_mode != "off":
            preprocess_counters["attempted"] += 1
            if pre_applied:
                preprocess_counters["applied"] += 1
            elif pre_reason != "shadow_pass":
                preprocess_counters["fallback"] += 1
            preprocess_reasons[pre_reason] += 1

        try:
            result = parser(detail_text=detail_text)
            results.append({
                "sn": sn,
                "title": title,
                "programs": [p.model_dump() for p in result.programs],
            })
        except Exception as e:
            print(f"Error for {sn}: {e}")
            results.append({
                "sn": sn,
                "title": title,
                "programs": [],
                "error": str(e),
            })

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print_preprocess_summary(args.preprocess_mode, preprocess_counters, preprocess_reasons)
    print(f"Processed {len(results)} items → {args.output}")


if __name__ == "__main__":
    main()
