"""detail_text에 실제 프로그램(곡 목록) 정보가 있는지 판별하는 게이트.

왜 필요한가
-----------
SAC 상세 페이지의 "작품소개" 탭은 비어 있거나 연주자 프로필만 있는 경우가 흔하다.
공연 확정 직후에는 프로그램이 아직 안 올라오기 때문이다. crawl.py의 필터는
탭 자체가 없을 때만 None을 내므로, 머리말("공연·전시 상세 정보")만 11자 있는
페이지도 그대로 통과해 LLM까지 흘러간다.

그 텍스트를 받은 모델은 "없다"고 답할 길이 없어서 그럴듯한 곡 목록을 지어낸다.
temperature=0이라 같은 빈 입력에는 같은 환각이 나오므로 결과가 무작위가 아니라
'도배'로 나타난다 — 2026-09 데이터에서 공연 12건이 완전히 동일한 바흐 첼로
모음곡(기타 편곡) 4곡 블록을 달고 있었고, 그 12건 어느 원문에도 "BWV 1007"·
"Guitar" 문자열이 없었다.

설계 원칙
---------
이 게이트는 **명백히 프로그램이 없는** 입력만 LLM 호출 전에 걸러낸다.
프로필만 긴 페이지처럼 애매한 입력까지 잡으려 들지 않는다 — 그건 프롬프트의
"프로그램 섹션이 없으면 빈 배열" 규칙이 담당한다.
오탐(정상 프로그램을 막는 것)이 미탐보다 훨씬 비싸므로 통과 쪽으로 기울여 놨다.
"""

import re

# 본문 길이 임계치
MIN_BODY_CHARS = 12  # 곡 정보 신호가 있어도 이보다 짧으면 토막으로 보고 차단
SHORT_BODY_CHARS = 250  # 곡 정보 신호가 없을 때, 이보다 짧으면 안내문으로 보고 차단
#
# 길이만으로 자르지 않는 이유: 국악·가곡 프로그램은 "1부 한오백년, 뱃노래 2부
# 아리랑 환상곡 제3번"처럼 30~40자짜리 진짜 목록인 경우가 있다. 그래서 판정의
# 1차 기준은 길이가 아니라 곡 정보 신호이고, 길이는 신호가 없을 때만 쓴다.

# 크롤러가 항상 붙여오는 머리말 + "내용 없음"을 뜻하는 상투구
_BOILERPLATE_RE = re.compile(
    r"공연\s*[·ㆍ・.]?\s*전시\s*상세\s*정보"
    r"|상세\s*정보\s*(?:준비|등록)\s*중"
    r"|공연\s*내용\s*(?:준비|등록)\s*중"
    r"|프로그램\s*(?:준비|등록)\s*중"
    r"|준비\s*중\s*입니다"
    r"|추후\s*(?:공지|안내)",
    re.IGNORECASE,
)

# 곡 정보가 있다고 볼 신호들. 하나라도 걸리면 통과시킨다.
_SIGNAL_RE = re.compile(
    # 작품번호 체계
    r"Op\.?\s*\d"
    r"|BWV\s*\.?\s*\d"
    r"|BuxWV|Hob\.|WoO\s*\d|RV\s*\d|HWV\s*\d|TrV\s*\d|Sz\.?\s*\d"
    r"|\bKV?\.?\s*\d{2,}"
    r"|\bD\.\s*\d{2,}"
    r"|\bS\.\s*\d{2,}"
    r"|작품\s*번?호?\s*\d"
    r"|No\.\s*\d"
    r"|제\s*\d+\s*번"
    # 프로그램 섹션 헤더
    r"|\[\s*프로그램\s*\]|\bPROGRAM\b|연주\s*곡\s*목|곡\s*목\s*[::]"
    # 장르어 (한국어)
    r"|교향곡|협주곡|소나타|변주곡|모음곡|서곡|전주곡|간주곡|야상곡|즉흥곡"
    r"|환상곡|광시곡|랩소디|이중주|삼중주|사중주|오중주|육중주|팔중주"
    r"|가곡|연가곡|아리아|미사곡|레퀴엠|칸타타|오라토리오|왈츠|왈쯔|녹턴"
    r"|마주르카|폴로네즈|스케르초|세레나데|카프리치오|토카타|푸가|무곡|행진곡"
    # 장르어 (영어/독일어/프랑스어)
    r"|\b(?:Symphon\w*|Concerto|Concerti|Sonat\w+|Variation\w*|Suite|Overture"
    r"|Prelude|Interlude|Intermezzo|Nocturne|Impromptu|Fantas\w+|Rhapsod\w+"
    r"|Ballade|Mazurka|Polonaise|Scherzo|Serenade|Caprice|Capriccio|Toccata"
    r"|Fugue|Partita|Etude|Étude|Waltz|Valse|Requiem|Cantata|Oratorio"
    r"|Mass|Aria|Lied|Lieder|Quartet|Quintet|Sextet|Septet|Octet|Trio|Duo"
    r"|Romance|Elegy|Adagio|Allegro|Andante)\b",
    re.IGNORECASE,
)


def strip_boilerplate(detail: str | None) -> str:
    """머리말·상투구를 제거한 실질 본문을 반환한다."""
    if not detail:
        return ""
    return _BOILERPLATE_RE.sub(" ", str(detail)).strip()


def gate_reason(detail: str | None) -> str | None:
    """차단 사유를 반환한다. 통과면 None.

    로그에 그대로 찍을 수 있는 한국어 문자열을 돌려준다.
    """
    body = strip_boilerplate(detail)

    if len(body) < MIN_BODY_CHARS:
        return f"작품소개 본문이 사실상 비어 있음 ({len(body)}자)"

    if _SIGNAL_RE.search(body):
        return None

    if len(body) < SHORT_BODY_CHARS:
        return f"짧은 안내문뿐이고 곡 정보 신호가 없음 ({len(body)}자)"

    # 본문이 충분히 길면 통과시킨다. 연주자 프로필만 있는 페이지가 여기로 오는데,
    # 그 판정은 프롬프트의 "프로그램 섹션이 없으면 빈 배열" 규칙에 맡긴다.
    return None


def has_program_text(detail: str | None) -> bool:
    """detail_text를 LLM에 넘길 가치가 있는지."""
    return gate_reason(detail) is None
