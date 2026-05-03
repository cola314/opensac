"""수동 라벨링 vs Gemini Flash 결과 비교 (v1 프롬프트 시절 분석용 — legacy)."""

import pandas as pd
import re
import unicodedata
from pathlib import Path

DATA = Path(__file__).parent / "data"


def norm(s: str) -> str:
    """비교용 정규화: NFKC, lowercase, 공백·특수문자 제거."""
    s = unicodedata.normalize("NFKC", str(s))
    s = s.lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[\.,'’`\"“”\-‐\(\)\[\]:;!?·•/]", "", s)
    return s


manual = pd.read_csv(DATA / "작곡가_곡_수동추출_샘플.csv")
gemini = pd.read_csv(DATA / "작곡가_곡_gemini_flash_v2_샘플.csv")

print(f"수동: {len(manual)}행, Gemini: {len(gemini)}행\n")
print("=== 공연별 행 수 ===")
for name in manual["공연명"].unique():
    m = (manual["공연명"] == name).sum()
    g = (gemini["공연명"] == name).sum()
    flag = "" if m == g else "  ← 차이"
    print(f"  - {name}: 수동={m}, Gemini={g}{flag}")

# Gemini 중복 제거: 정규화한 (composer_norm, title_norm) 기준 dedup
gemini["norm_key"] = gemini["곡명"].apply(norm)
gemini_dedup = gemini.drop_duplicates(subset=["공연명", "norm_key"]).copy()
print(f"\nGemini 한·영 중복 제거 후: {len(gemini_dedup)}행")

# 매칭 (공연명 + 곡명 정규화 기준)
manual["norm_key"] = manual["곡명"].apply(norm)

m_keys = set(zip(manual["공연명"], manual["norm_key"]))
g_keys = set(zip(gemini_dedup["공연명"], gemini_dedup["norm_key"]))

# 부분 일치도 보기 위해 더 느슨하게: 곡명 정규화 문자열에서 공통 토큰이 있는가
print("\n=== 정확 일치 / 차이 ===")
exact = m_keys & g_keys
only_m = m_keys - g_keys
only_g = g_keys - m_keys
print(f"  정확 일치: {len(exact)}")
print(f"  수동에만:  {len(only_m)}")
print(f"  Gemini에만: {len(only_g)}")

if only_m:
    print("\n[수동에만 있는 항목]")
    for c, k in sorted(only_m):
        orig = manual[(manual["공연명"] == c) & (manual["norm_key"] == k)]["곡명"].iloc[0]
        print(f"  - [{c}] {orig}")

if only_g:
    print("\n[Gemini에만 있는 항목]")
    for c, k in sorted(only_g):
        orig = gemini_dedup[(gemini_dedup["공연명"] == c) & (gemini_dedup["norm_key"] == k)]["곡명"].iloc[0]
        print(f"  - [{c}] {orig}")

# 공연별 작곡가 set 비교
print("\n=== 공연별 작곡가 셋 (참고용) ===")
for name in manual["공연명"].unique():
    m_comp = sorted(set(manual[manual["공연명"] == name]["작곡가"].apply(lambda s: norm(s))))
    g_comp = sorted(set(gemini_dedup[gemini_dedup["공연명"] == name]["작곡가"].apply(lambda s: norm(s))))
    print(f"\n  {name}")
    print(f"    수동: {len(m_comp)}명")
    print(f"    Gemini: {len(g_comp)}명")
