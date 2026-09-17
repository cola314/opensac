"""program_gate 회귀 테스트. 네트워크·API 키 불필요.

  python ml/test_program_gate.py

픽스처는 실제 SAC "작품소개" 탭 텍스트에서 가져왔다.
crawl.fetch_detail이 get_text(strip=True)로 뽑기 때문에 줄바꿈이 없는
한 덩어리 문자열이라는 점까지 그대로 재현했다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from program_gate import gate_reason, has_program_text, strip_boilerplate

HEAD = "공연·전시 상세 정보"

# ── 차단되어야 하는 입력 ──────────────────────────────────────────────
# 실제로 환각 12건을 만들어낸 입력들이 이 모양이었다.
MUST_BLOCK = [
    ("None", None),
    ("빈 문자열", ""),
    ("머리말만 (SN 77631 홍종화&김정수 듀오, SN 74673 조수미 CONTINUUM)", HEAD),
    ("머리말 + 공백", HEAD + "   "),
    ("준비중 안내", HEAD + "상세정보 준비중입니다."),
    ("프로그램 추후 공지", HEAD + "프로그램은 추후 공지 예정입니다."),
    (
        "짧은 홍보문구, 곡 정보 신호 없음",
        HEAD + "올가을, 가장 따뜻한 무대로 여러분을 초대합니다. 온 가족이 함께 즐기는 특별한 시간. 예매 문의는 공연기획사로 연락 주시기 바랍니다.",
    ),
]

# ── 반드시 통과해야 하는 입력 ────────────────────────────────────────
# 오탐(정상 프로그램 차단)이 미탐보다 비싸다. 여기가 깨지면 게이트를 되돌려야 한다.
MUST_PASS = [
    (
        "영어 프로그램 섹션 (SN 80134 안수민 바로크 플루트)",
        HEAD
        + "[프로그램]François Couperin(1668-1733) -Premier Concert No. 1 in G Major aus Concerts Royaux (1722)PréludeAllemandeSarabandeGavotteGigueMenuet",
    ),
    (
        "작품번호만 있는 짧은 프로그램",
        HEAD + "J. S. Bach : Goldberg Variations BWV 988",
    ),
    (
        "한국 가곡 — 장르어 없이 곡명만, 섹션 헤더로 통과",
        HEAD + "[프로그램]그리운 금강산 / 목련화 / 산노을 / 향수 / 첫사랑 / 강 건너 봄이 오듯",
    ),
    (
        "국악·민요 — 제N번 표기",
        HEAD + "1부 한오백년, 뱃노래, 새야 새야 2부 아리랑 환상곡 제3번",
    ),
    (
        "연주자 프로필만 긴 페이지 (SN 77498 김운성 트롬본)",
        HEAD
        + "PROFILE TROMBONE 김운성 작품에 대한 섬세한 이해와 뛰어난 연주력을 바탕으로 폭넓은 음악 활동을 선보이고 있는 트롬보니스트 김운성은 연세대학교 음악대학을 졸업하고 도독하여 쾰른 국립음대에서 최고연주자과정을 마쳤다. "
        + "이후 국내외 여러 오케스트라와 협연하였으며 현재 다수의 대학에 출강하며 후학을 양성하고 있다. 그는 언제나 무대에서 관객과 호흡하는 연주를 지향한다. " * 3,
    ),
    (
        "산문 속에 곡명이 섞인 소개글 (SN 81352 더 바흐 #7 골드베르크)",
        HEAD
        + "피아니스트 강효지가 바흐의 불멸의 걸작 <골드베르크 변주곡>과 자작곡 <만화경>의 세계 초연을 선보이는 특별한 리사이틀이다. 시대를 초월한 바흐의 음악과 동시대 창작이 한 무대에서 만나, 전통과 현대가 교차하는 순간을 그린다.",
    ),
]


def main() -> int:
    failures = []

    print("── 차단되어야 하는 입력 ──")
    for label, text in MUST_BLOCK:
        reason = gate_reason(text)
        ok = reason is not None
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        if ok:
            print(f"        └ 사유: {reason}")
        else:
            failures.append(f"차단 실패: {label} (본문 {len(strip_boilerplate(text))}자)")

    print("\n── 통과해야 하는 입력 ──")
    for label, text in MUST_PASS:
        ok = has_program_text(text)
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        if not ok:
            failures.append(f"오탐(정상 프로그램 차단): {label} → {gate_reason(text)}")

    print()
    if failures:
        print(f"실패 {len(failures)}건")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"전체 통과 ({len(MUST_BLOCK)} 차단 + {len(MUST_PASS)} 통과)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
