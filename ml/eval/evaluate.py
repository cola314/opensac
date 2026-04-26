import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent.parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from eval.metrics import program_f1, program_f1_v2

DEFAULT_PREDICTIONS_PATH = ML_DIR / "data" / "dspy_results.json"
DEFAULT_GOLD_PATH = ML_DIR / "data" / "dataset.dev20.json"
DEFAULT_RUN_LOG_PATH = ML_DIR / "data" / "runs" / "metrics_runs.jsonl"
DEFAULT_RUN_CSV_PATH = ML_DIR / "data" / "runs" / "metrics_runs.csv"


def select_metric(metric_version: str):
    if metric_version == "v2":
        return program_f1_v2
    return program_f1


def append_run_log(
    run_log_path: Path,
    *,
    run_tag: str,
    variant: str,
    metric_version: str,
    preprocess_mode: str,
    predictions_path: str,
    gold_path: str,
    n_items: int,
    precision: float,
    recall: float,
    f1: float,
    low_f1_count: int,
    est_cost_usd: float,
) -> None:
    run_log_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    run_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{run_tag or 'eval'}"

    record = {
        "run_id": run_id,
        "timestamp": timestamp,
        "stage": "evaluate",
        "variant": variant,
        "metric_version": metric_version,
        "preprocess_mode": preprocess_mode,
        "predictions_path": predictions_path,
        "gold_path": gold_path,
        "n_items": n_items,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "low_f1_count": low_f1_count,
        "est_cost_usd": est_cost_usd,
    }

    with open(run_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def export_run_log_csv(run_log_path: Path, csv_path: Path) -> int:
    if not run_log_path.exists():
        print(f"Run log not found: {run_log_path}")
        return 0

    rows = []
    with open(run_log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    if not rows:
        print("No run records to export")
        return 0

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp",
        "run_id",
        "variant",
        "metric_version",
        "preprocess_mode",
        "n_items",
        "precision",
        "recall",
        "f1",
        "low_f1_count",
        "est_cost_usd",
        "predictions_path",
        "gold_path",
    ]

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})

    return len(rows)


def print_recent_runs(run_log_path: Path, limit: int) -> int:
    if not run_log_path.exists():
        print(f"Run log not found: {run_log_path}")
        return 0

    rows = []
    with open(run_log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    if not rows:
        print("No run records found")
        return 0

    rows = rows[-limit:]
    print("=== Recent run trend ===")
    for row in rows:
        print(
            f"{row.get('timestamp')} "
            f"{row.get('variant')}/{row.get('metric_version')} "
            f"f1={row.get('f1', 0):.3f} "
            f"p={row.get('precision', 0):.3f} "
            f"r={row.get('recall', 0):.3f} "
            f"n={row.get('n_items', 0)} "
            f"cost~{row.get('est_cost_usd', 0):.4f}"
        )
    return len(rows)


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--predictions", default=str(DEFAULT_PREDICTIONS_PATH), help="DSPy 결과 JSON")
    argparser.add_argument("--gold", default=str(DEFAULT_GOLD_PATH), help="골드 데이터셋 JSON")
    argparser.add_argument("--metric-version", choices=["v1", "v2"], default="v1", help="평가 메트릭 버전")
    argparser.add_argument("--variant", default="baseline", help="실험 변형 라벨 (baseline/compiled)")
    argparser.add_argument("--preprocess-mode", choices=["off", "shadow", "on"], default="off", help="입력 전처리 모드 라벨")
    argparser.add_argument("--run-tag", default="", help="추적 로그 run 태그")
    argparser.add_argument("--run-log", default=str(DEFAULT_RUN_LOG_PATH), help="JSONL 추적 로그 경로")
    argparser.add_argument("--run-csv", default=str(DEFAULT_RUN_CSV_PATH), help="CSV 추출 경로")
    argparser.add_argument("--track-runs", action="store_true", help="평가 결과를 run log에 append")
    argparser.add_argument("--export-csv", action="store_true", help="run log를 CSV로 내보내기")
    argparser.add_argument("--report-trend", action="store_true", help="최근 run 요약 출력")
    argparser.add_argument("--trend-limit", type=int, default=20, help="최근 run 출력 개수")
    argparser.add_argument("--est-cost-usd", type=float, default=0.0, help="이번 실행 예상 비용(USD)")
    args = argparser.parse_args()

    run_log_path = Path(args.run_log)
    run_csv_path = Path(args.run_csv)

    if args.export_csv:
        count = export_run_log_csv(run_log_path, run_csv_path)
        print(f"Exported {count} run records -> {run_csv_path}")
        if not args.report_trend and not args.track_runs:
            return

    if args.report_trend:
        count = print_recent_runs(run_log_path, args.trend_limit)
        print(f"Displayed {count} run records")
        if not args.track_runs and args.predictions == str(DEFAULT_PREDICTIONS_PATH) and args.gold == str(DEFAULT_GOLD_PATH):
            return

    metric_fn = select_metric(args.metric_version)

    with open(args.predictions, encoding="utf-8") as f:
        preds = {str(item["sn"]): item for item in json.load(f)}

    with open(args.gold, encoding="utf-8") as f:
        golds = {str(item["sn"]): item for item in json.load(f)}

    common_sns = set(preds.keys()) & set(golds.keys())
    print(f"Evaluating {len(common_sns)} items")
    if not common_sns:
        print("No overlapping SNs between predictions and gold dataset.")
        return

    scores = []
    errors = []
    for sn in sorted(common_sns):
        pred_programs = preds[sn].get("programs", [])
        gold_programs = golds[sn].get("programs", [])
        score = metric_fn(pred_programs, gold_programs)
        scores.append(score)

        if score["f1"] < 0.8:
            errors.append({
                "sn": sn,
                "title": golds[sn].get("title", ""),
                "f1": score["f1"],
                "pred_count": len(pred_programs),
                "gold_count": len(gold_programs),
            })

    avg_precision = sum(s["precision"] for s in scores) / len(scores) if scores else 0
    avg_recall = sum(s["recall"] for s in scores) / len(scores) if scores else 0
    avg_f1 = sum(s["f1"] for s in scores) / len(scores) if scores else 0

    print(f"\n=== Results ({args.metric_version}) ===")
    print(f"Precision: {avg_precision:.3f}")
    print(f"Recall:    {avg_recall:.3f}")
    print(f"F1:        {avg_f1:.3f}")

    if errors:
        print(f"\n=== Low F1 items ({len(errors)}) ===")
        for e in errors[:10]:
            print(f"  SN {e['sn']} ({e['title']}): F1={e['f1']:.2f} (pred={e['pred_count']}, gold={e['gold_count']})")

    if args.track_runs:
        append_run_log(
            run_log_path,
            run_tag=args.run_tag,
            variant=args.variant,
            metric_version=args.metric_version,
            preprocess_mode=args.preprocess_mode,
            predictions_path=args.predictions,
            gold_path=args.gold,
            n_items=len(common_sns),
            precision=avg_precision,
            recall=avg_recall,
            f1=avg_f1,
            low_f1_count=len(errors),
            est_cost_usd=args.est_cost_usd,
        )
        print(f"Run log appended -> {run_log_path}")


if __name__ == "__main__":
    main()
