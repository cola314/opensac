import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ML_DIR = Path(__file__).resolve().parent.parent
COMPILE_SCRIPT = ML_DIR / "optimize" / "compile.py"
PIPELINE_SCRIPT = ML_DIR / "parser" / "pipeline.py"
EVAL_SCRIPT = ML_DIR / "eval" / "evaluate.py"
DEFAULT_TRAINSET = ML_DIR / "data" / "dataset.train30.json"
DEFAULT_DEVSET = ML_DIR / "data" / "dataset.dev20.json"
DEFAULT_SEARCH_LOG = ML_DIR / "data" / "runs" / "search_runs.jsonl"
DEFAULT_WORKSPACE = ML_DIR / "data" / "runs" / "search_artifacts"
DEFAULT_DOTENV_PATH = ML_DIR / ".env"


@dataclass
class Candidate:
    optimizer: str
    metric_version: str
    preprocess_mode: str
    max_bootstrapped_demos: int
    max_labeled_demos: int
    max_rounds: int
    auto: str


def parse_list(raw: str, cast):
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [cast(p) for p in parts]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_env_file(dotenv_path: Path) -> dict:
    env = os.environ.copy()
    if not dotenv_path.exists():
        return env

    with open(dotenv_path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in env:
                env[key] = value
    return env


def estimate_trial_cost(
    candidate: Candidate,
    train_input_chars: int,
    dev_input_chars: int,
    input_chars_per_token: float,
    output_token_ratio: float,
    price_in_per_m: float,
    price_out_per_m: float,
) -> tuple[float, float, float]:
    train_input_tokens = train_input_chars / input_chars_per_token
    dev_input_tokens = dev_input_chars / input_chars_per_token

    if candidate.optimizer == "bootstrap":
        compile_multiplier = (
            0.8
            + 0.25 * candidate.max_bootstrapped_demos
            + 0.05 * candidate.max_labeled_demos
            + 0.10 * candidate.max_rounds
        )
    else:
        compile_multiplier = (
            1.0
            + 0.35 * candidate.max_bootstrapped_demos
            + 0.08 * candidate.max_labeled_demos
        )
        if candidate.auto == "medium":
            compile_multiplier *= 1.2
        elif candidate.auto == "heavy":
            compile_multiplier *= 1.5

    compile_input_tokens = train_input_tokens * compile_multiplier
    compile_output_tokens = compile_input_tokens * 0.12

    infer_input_tokens = dev_input_tokens
    infer_output_tokens = dev_input_tokens * output_token_ratio

    total_input_tokens = compile_input_tokens + infer_input_tokens
    total_output_tokens = compile_output_tokens + infer_output_tokens

    est_cost = (
        (total_input_tokens / 1_000_000) * price_in_per_m
        + (total_output_tokens / 1_000_000) * price_out_per_m
    )

    return est_cost, total_input_tokens, total_output_tokens


def candidate_to_dict(candidate: Candidate) -> dict:
    return {
        "optimizer": candidate.optimizer,
        "metric_version": candidate.metric_version,
        "preprocess_mode": candidate.preprocess_mode,
        "max_bootstrapped_demos": candidate.max_bootstrapped_demos,
        "max_labeled_demos": candidate.max_labeled_demos,
        "max_rounds": candidate.max_rounds,
        "auto": candidate.auto,
    }


def run_command(name: str, cmd: list[str], env: dict) -> subprocess.CompletedProcess:
    print(f"\n[{name}] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ML_DIR), env=env, capture_output=True, text=True)

    if result.stdout.strip():
        lines = result.stdout.strip().splitlines()
        for line in lines[-12:]:
            print(line)

    if result.returncode != 0:
        print(f"[{name}] failed with code {result.returncode}")
        if result.stderr.strip():
            err_lines = result.stderr.strip().splitlines()
            for line in err_lines[-12:]:
                print(line)

    return result


def parse_eval_metrics(stdout: str) -> tuple[float | None, float | None, float | None]:
    p = re.search(r"Precision:\s+([0-9.]+)", stdout)
    r = re.search(r"Recall:\s+([0-9.]+)", stdout)
    f1 = re.search(r"F1:\s+([0-9.]+)", stdout)

    if not (p and r and f1):
        return None, None, None

    return float(p.group(1)), float(r.group(1)), float(f1.group(1))


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Budgeted DSPy search runner")
    parser.add_argument("--trainset", default=str(DEFAULT_TRAINSET))
    parser.add_argument("--devset", default=str(DEFAULT_DEVSET))
    parser.add_argument("--search-log", default=str(DEFAULT_SEARCH_LOG))
    parser.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--dotenv", default=str(DEFAULT_DOTENV_PATH))
    parser.add_argument("--max-trials", type=int, default=6)
    parser.add_argument("--budget-usd", type=float, default=0.08)
    parser.add_argument("--price-in-per-m", type=float, default=0.30)
    parser.add_argument("--price-out-per-m", type=float, default=1.20)
    parser.add_argument("--input-chars-per-token", type=float, default=1.5)
    parser.add_argument("--output-token-ratio", type=float, default=0.20)
    parser.add_argument("--optimizers", default="bootstrap,mipro")
    parser.add_argument("--metric-versions", default="v1,v2")
    parser.add_argument("--preprocess-modes", default="off,shadow")
    parser.add_argument("--bootstrapped-options", default="1,2")
    parser.add_argument("--labeled-options", default="2,4")
    parser.add_argument("--max-rounds-options", default="1")
    parser.add_argument("--auto-options", default="light")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    trainset = Path(args.trainset)
    devset = Path(args.devset)
    search_log = Path(args.search_log)
    workspace = Path(args.workspace)
    dotenv_path = Path(args.dotenv)

    train_items = load_json(trainset)
    dev_items = load_json(devset)
    train_input_chars = sum(len((x.get("input") or x.get("detail_text") or "")) for x in train_items)
    dev_input_chars = sum(len((x.get("input") or x.get("detail_text") or "")) for x in dev_items)

    optimizers = parse_list(args.optimizers, str)
    metric_versions = parse_list(args.metric_versions, str)
    preprocess_modes = parse_list(args.preprocess_modes, str)
    boot_opts = parse_list(args.bootstrapped_options, int)
    label_opts = parse_list(args.labeled_options, int)
    round_opts = parse_list(args.max_rounds_options, int)
    auto_opts = parse_list(args.auto_options, str)

    candidates: list[tuple[Candidate, float, float, float]] = []

    for optimizer in optimizers:
        for metric_version in metric_versions:
            for preprocess_mode in preprocess_modes:
                for max_boot in boot_opts:
                    for max_label in label_opts:
                        if optimizer == "bootstrap":
                            for max_rounds in round_opts:
                                candidate = Candidate(
                                    optimizer=optimizer,
                                    metric_version=metric_version,
                                    preprocess_mode=preprocess_mode,
                                    max_bootstrapped_demos=max_boot,
                                    max_labeled_demos=max_label,
                                    max_rounds=max_rounds,
                                    auto="light",
                                )
                                est_cost, est_in, est_out = estimate_trial_cost(
                                    candidate,
                                    train_input_chars,
                                    dev_input_chars,
                                    args.input_chars_per_token,
                                    args.output_token_ratio,
                                    args.price_in_per_m,
                                    args.price_out_per_m,
                                )
                                candidates.append((candidate, est_cost, est_in, est_out))
                        else:
                            for auto in auto_opts:
                                candidate = Candidate(
                                    optimizer=optimizer,
                                    metric_version=metric_version,
                                    preprocess_mode=preprocess_mode,
                                    max_bootstrapped_demos=max_boot,
                                    max_labeled_demos=max_label,
                                    max_rounds=1,
                                    auto=auto,
                                )
                                est_cost, est_in, est_out = estimate_trial_cost(
                                    candidate,
                                    train_input_chars,
                                    dev_input_chars,
                                    args.input_chars_per_token,
                                    args.output_token_ratio,
                                    args.price_in_per_m,
                                    args.price_out_per_m,
                                )
                                candidates.append((candidate, est_cost, est_in, est_out))

    candidates.sort(key=lambda x: x[1])

    selected: list[tuple[Candidate, float, float, float]] = []
    running_est_cost = 0.0
    for cand, est_cost, est_in, est_out in candidates:
        if len(selected) >= args.max_trials:
            break
        if running_est_cost + est_cost > args.budget_usd:
            continue
        selected.append((cand, est_cost, est_in, est_out))
        running_est_cost += est_cost

    print("=== Search plan ===")
    print(f"train_items={len(train_items)} dev_items={len(dev_items)}")
    print(f"candidate_pool={len(candidates)}")
    print(f"selected_trials={len(selected)}")
    print(f"budget_usd={args.budget_usd:.4f} est_total_usd={running_est_cost:.4f}")

    for i, (cand, est_cost, est_in, est_out) in enumerate(selected, start=1):
        print(
            f"  trial#{i} opt={cand.optimizer} metric={cand.metric_version} pre={cand.preprocess_mode} "
            f"boot={cand.max_bootstrapped_demos} labeled={cand.max_labeled_demos} rounds={cand.max_rounds} auto={cand.auto} "
            f"est=${est_cost:.4f} in~{est_in:.0f} out~{est_out:.0f}"
        )

    if not selected:
        print("No trials selected under budget. Increase --budget-usd or reduce search space.")
        return

    if args.dry_run:
        print("Dry-run mode: no model calls executed.")
        return

    env = load_env_file(dotenv_path)
    workspace.mkdir(parents=True, exist_ok=True)

    results = []
    best = None

    for idx, (cand, est_cost, est_in, est_out) in enumerate(selected, start=1):
        now = datetime.now(timezone.utc)
        run_stamp = now.strftime("%Y%m%d-%H%M%S")
        run_id = f"search-{run_stamp}-{idx:02d}-{cand.optimizer}-{cand.metric_version}-{cand.preprocess_mode}"

        compiled_path = workspace / f"compiled.{run_id}.json"
        pred_path = workspace / f"pred.{run_id}.json"

        compile_cmd = [
            sys.executable,
            str(COMPILE_SCRIPT),
            "--trainset",
            str(trainset),
            "--output",
            str(compiled_path),
            "--optimizer",
            cand.optimizer,
            "--metric-version",
            cand.metric_version,
            "--max-bootstrapped-demos",
            str(cand.max_bootstrapped_demos),
            "--max-labeled-demos",
            str(cand.max_labeled_demos),
            "--preprocess-mode",
            cand.preprocess_mode,
        ]

        if cand.optimizer == "bootstrap":
            compile_cmd.extend(["--max-rounds", str(cand.max_rounds)])
        else:
            compile_cmd.extend(["--auto", cand.auto])

        pipeline_cmd = [
            sys.executable,
            str(PIPELINE_SCRIPT),
            "--input",
            str(devset),
            "--output",
            str(pred_path),
            "--compiled-program",
            str(compiled_path),
            "--preprocess-mode",
            cand.preprocess_mode,
        ]

        eval_cmd = [
            sys.executable,
            str(EVAL_SCRIPT),
            "--predictions",
            str(pred_path),
            "--gold",
            str(devset),
            "--metric-version",
            cand.metric_version,
            "--variant",
            "search",
            "--preprocess-mode",
            cand.preprocess_mode,
            "--run-tag",
            run_id,
            "--track-runs",
            "--est-cost-usd",
            f"{est_cost:.6f}",
        ]

        record = {
            "run_id": run_id,
            "timestamp": now.isoformat(),
            "status": "started",
            "candidate": candidate_to_dict(cand),
            "est_cost_usd": est_cost,
            "est_input_tokens": est_in,
            "est_output_tokens": est_out,
            "compiled_path": str(compiled_path),
            "predictions_path": str(pred_path),
        }

        compile_res = run_command("compile", compile_cmd, env)
        if compile_res.returncode != 0:
            record["status"] = "compile_failed"
            record["compile_returncode"] = compile_res.returncode
            record["compile_stderr_tail"] = "\n".join(compile_res.stderr.strip().splitlines()[-8:])
            append_jsonl(search_log, record)
            results.append(record)
            continue

        pipeline_res = run_command("pipeline", pipeline_cmd, env)
        if pipeline_res.returncode != 0:
            record["status"] = "pipeline_failed"
            record["pipeline_returncode"] = pipeline_res.returncode
            record["pipeline_stderr_tail"] = "\n".join(pipeline_res.stderr.strip().splitlines()[-8:])
            append_jsonl(search_log, record)
            results.append(record)
            continue

        eval_res = run_command("evaluate", eval_cmd, env)
        if eval_res.returncode != 0:
            record["status"] = "eval_failed"
            record["eval_returncode"] = eval_res.returncode
            record["eval_stderr_tail"] = "\n".join(eval_res.stderr.strip().splitlines()[-8:])
            append_jsonl(search_log, record)
            results.append(record)
            continue

        precision, recall, f1 = parse_eval_metrics(eval_res.stdout)
        record["status"] = "success"
        record["precision"] = precision
        record["recall"] = recall
        record["f1"] = f1
        append_jsonl(search_log, record)
        results.append(record)

        if f1 is not None and (best is None or f1 > best["f1"]):
            best = record

    print("\n=== Search summary ===")
    success = [r for r in results if r.get("status") == "success"]
    print(f"completed={len(results)} success={len(success)}")
    print(f"search_log={search_log}")

    if best is None:
        print("No successful trial to report best config.")
        return

    print("Best trial:")
    print(f"  run_id={best['run_id']}")
    print(f"  f1={best.get('f1'):.3f} p={best.get('precision'):.3f} r={best.get('recall'):.3f}")
    print(f"  est_cost_usd={best.get('est_cost_usd'):.4f}")
    print(f"  candidate={json.dumps(best['candidate'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
