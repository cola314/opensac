"""
라벨링 스크립트: claude -p 를 asyncio subprocess로 병렬 호출해 detail_text에서 프로그램 정보 추출.

Usage:
    cd ml && python label/generate.py
    cd ml && python label/generate.py --limit 10
    cd ml && python label/generate.py --concurrency 5
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

ML_DIR = Path(__file__).parent.parent
DATA_DIR = ML_DIR / "data"
LABELED_DIR = DATA_DIR / "labeled"

PROMPT_TEMPLATE = """다음 클래식 공연 작품소개 텍스트에서 연주 프로그램 정보를 추출해주세요.

각 곡에 대해 composer(작곡가 원어명/영문)와 piece(곡명 원어명/영문, 작품번호 포함)를 추출합니다.
한글/영문이 병기된 경우 원어(영문) 기준으로 하나만 추출합니다. 동일한 곡을 중복으로 넣지 마세요.
프로그램 정보가 없는 경우(출연자 프로필만 있는 등) 빈 배열을 반환하세요.

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

[
  {{"composer": "작곡가 원어명", "piece": "곡명 원어명, 작품번호"}},
  ...
]

텍스트:
{detail_text}"""


async def label_one(detail_text: str, semaphore: asyncio.Semaphore) -> list[dict]:
    prompt = PROMPT_TEMPLATE.format(detail_text=detail_text)

    async with semaphore:
        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", prompt, "--model", "haiku", "--output-format", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=90)

    if proc.returncode != 0:
        raise RuntimeError(
            f"claude exited with code {proc.returncode}: {stderr.decode().strip()}"
        )

    output = json.loads(stdout.decode())
    content = output.get("result", "[]")

    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        content = content.rsplit("```", 1)[0]

    return json.loads(content)


async def process_item(item: dict, semaphore: asyncio.Semaphore, pbar: tqdm) -> dict | None:
    sn = str(item["sn"])
    out_path = LABELED_DIR / f"{sn}.json"

    if out_path.exists():
        pbar.update(1)
        return {"status": "skipped"}

    try:
        programs = await label_one(item.get("detail_text", ""), semaphore)
    except Exception as e:
        logger.error(f"[{sn}] Failed: {e}")
        pbar.update(1)
        return {"status": "error"}

    record = {
        "sn": sn,
        "title": item.get("title", ""),
        "input": item.get("detail_text", ""),
        "programs": programs,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    pbar.update(1)
    return {"status": "success"}


async def run(items: list[dict], concurrency: int) -> None:
    semaphore = asyncio.Semaphore(concurrency)
    pbar = tqdm(total=len(items), unit="item")

    tasks = [process_item(item, semaphore, pbar) for item in items]
    results = await asyncio.gather(*tasks)

    pbar.close()

    success = sum(1 for r in results if r and r["status"] == "success")
    skipped = sum(1 for r in results if r and r["status"] == "skipped")
    errors = sum(1 for r in results if r and r["status"] == "error")
    logger.info(f"Done. success={success}, skipped={skipped}, errors={errors}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Label detail_texts with claude -p (parallel)")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N items")
    parser.add_argument("--start-from", type=int, default=0, dest="start_from", help="Skip first N items")
    parser.add_argument("--concurrency", type=int, default=10, help="Max parallel claude calls (default: 10)")
    args = parser.parse_args()

    LABELED_DIR.mkdir(parents=True, exist_ok=True)

    with open(DATA_DIR / "detail_texts.json", encoding="utf-8") as f:
        items = json.load(f)

    items = items[args.start_from:]
    if args.limit is not None:
        items = items[:args.limit]

    logger.info(f"Processing {len(items)} items (concurrency={args.concurrency})")

    asyncio.run(run(items, args.concurrency))


if __name__ == "__main__":
    main()
