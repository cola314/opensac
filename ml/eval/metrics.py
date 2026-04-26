import re
import unicodedata
from difflib import SequenceMatcher

CATALOG_PATTERN = re.compile(r"\b(op\.?\s*\d+[a-z]?|bwv\s*\d+[a-z]?|k\.?\s*\d+[a-z]?|rv\s*\d+[a-z]?|s\.?\s*\d+[a-z]?|d\.?\s*\d+[a-z]?|hob\.?\s*[ivx]+:?\d*)\b", re.IGNORECASE)
ROMAN_MOVEMENT_SUFFIX = re.compile(r"\b(?:i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv)\.\s+[^,;]+$", re.IGNORECASE)

KOREAN_COMPOSER_ALIASES = {
    "모차르트": "wolfgang amadeus mozart",
    "베토벤": "ludwig van beethoven",
    "말러": "gustav mahler",
    "브람스": "johannes brahms",
    "프로코피예프": "sergei prokofiev",
    "드뷔시": "claude debussy",
    "뒤뷔시": "claude debussy",
    "생상스": "camille saint saens",
    "생상": "camille saint saens",
    "사티": "erik satie",
    "라벨": "maurice ravel",
    "슈만": "robert schumann",
    "바그너": "richard wagner",
    "리스트": "franz liszt",
    "글린카": "mikhail glinka",
    "로시니": "gioachino rossini",
    "구노": "charles gounod",
}

KOREAN_PIECE_ALIASES = {
    "후궁으로부터의 유괴": "die entfuhrung from the seraglio",
    "마적": "the magic flute",
    "거인": "titan",
    "에그몬트": "egmont",
}

KOREAN_PIECE_TOKEN_MAP = {
    "교향곡": "symphony",
    "협주곡": "concerto",
    "서곡": "overture",
    "소나타": "sonata",
    "모음곡": "suite",
    "환상곡": "fantasy",
    "왈츠": "waltz",
    "전주곡": "prelude",
    "피아노": "piano",
    "바이올린": "violin",
    "첼로": "cello",
    "플루트": "flute",
}


def normalize(s: str) -> str:
    """작곡가/곡명 정규화 — 소문자, 공백 정리"""
    return " ".join(s.lower().strip().split())


def _strip_diacritics(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _compact(s: str) -> str:
    return re.sub(r"\s+", "", s)


def canonical_composer(s: str) -> str:
    raw = normalize(s)
    mapped = KOREAN_COMPOSER_ALIASES.get(_compact(raw))
    if mapped:
        return mapped

    s = _strip_diacritics(raw)
    s = s.replace("&", " and ")
    s = s.replace(".", " ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = " ".join(s.split())

    alias_map = {
        "s rachmaninoff": "sergei rachmaninoff",
        "p i tchaikovsky": "pyotr ilyich tchaikovsky",
        "c franck": "cesar franck",
        "f liszt": "franz liszt",
        "j s bach": "johann sebastian bach",
        "w a mozart": "wolfgang amadeus mozart",
        "l v beethoven": "ludwig van beethoven",
        "a arensky": "anton arensky",
        "g bizet": "georges bizet",
        "r wagner": "richard wagner",
        "m glinka": "mikhail glinka",
        "g rossini": "gioachino rossini",
        "c gounod": "charles gounod",
        "r schumann": "robert schumann",
        "j brahms": "johannes brahms",
        "c debussy": "claude debussy",
        "c dubussy": "claude debussy",
        "e satie": "erik satie",
        "m ravel": "maurice ravel",
        "j haydn": "joseph haydn",
    }
    return alias_map.get(s, s)


def _replace_korean_piece_tokens(s: str) -> str:
    out = s
    for ko, en in KOREAN_PIECE_ALIASES.items():
        out = out.replace(ko, en)
    out = re.sub(r"(\d+)\s*번", r"no \1", out)
    for ko, en in KOREAN_PIECE_TOKEN_MAP.items():
        out = out.replace(ko, f" {en} ")
    return out


def canonical_piece(s: str) -> str:
    s = normalize(s)
    s = _replace_korean_piece_tokens(s)
    s = _strip_diacritics(s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"\bopus\b", "op", s)
    s = re.sub(r"\bkoechel\b", "k", s)
    s = re.sub(r"\bkochel\b", "k", s)
    s = re.sub(r"\([^)]{0,120}\)", " ", s)
    s = re.sub(r"\[[^]]{0,120}\]", " ", s)
    s = ROMAN_MOVEMENT_SUFFIX.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_catalog_ids(s: str) -> set[str]:
    text = canonical_piece(s)
    ids = set()
    for m in CATALOG_PATTERN.finditer(text):
        token = re.sub(r"\s+", "", m.group(1).lower())
        token = token.replace(".", "")
        ids.add(token)
    return ids


def composer_match(pred: str, gold: str, threshold: float = 0.7) -> bool:
    """작곡가명 fuzzy match"""
    return SequenceMatcher(None, normalize(pred), normalize(gold)).ratio() >= threshold


def piece_match(pred: str, gold: str, threshold: float = 0.6) -> bool:
    """곡명 fuzzy match (더 유연하게)"""
    return SequenceMatcher(None, normalize(pred), normalize(gold)).ratio() >= threshold


def _split_name_parts(name: str) -> tuple[list[str], str] | None:
    tokens = [t for t in name.split() if t]
    if len(tokens) < 2:
        return None
    return tokens[:-1], tokens[-1]


def _is_initial_tokens(tokens: list[str]) -> bool:
    return bool(tokens) and all(len(t) == 1 for t in tokens)


def _initial_lastname_equivalent(a: str, b: str) -> bool:
    parsed_a = _split_name_parts(a)
    parsed_b = _split_name_parts(b)
    if parsed_a is None or parsed_b is None:
        return False

    given_a, family_a = parsed_a
    given_b, family_b = parsed_b

    if family_a != family_b:
        return False

    if _is_initial_tokens(given_a):
        initials_b = [g[0] for g in given_b if g]
        return given_a == initials_b[: len(given_a)]

    if _is_initial_tokens(given_b):
        initials_a = [g[0] for g in given_a if g]
        return given_b == initials_a[: len(given_b)]

    return False


def composer_match_v2(pred: str, gold: str, threshold: float = 0.75) -> bool:
    pred_norm = canonical_composer(pred)
    gold_norm = canonical_composer(gold)

    if pred_norm == gold_norm:
        return True

    if _initial_lastname_equivalent(pred_norm, gold_norm):
        return True

    return SequenceMatcher(None, pred_norm, gold_norm).ratio() >= threshold


def piece_match_v2(pred: str, gold: str, threshold: float = 0.62) -> bool:
    pred_norm = canonical_piece(pred)
    gold_norm = canonical_piece(gold)

    if pred_norm == gold_norm:
        return True

    pred_catalog = extract_catalog_ids(pred_norm)
    gold_catalog = extract_catalog_ids(gold_norm)

    if pred_catalog and gold_catalog:
        return pred_catalog == gold_catalog

    shorter, longer = (pred_norm, gold_norm) if len(pred_norm) <= len(gold_norm) else (gold_norm, pred_norm)
    if len(shorter) >= 12 and shorter in longer:
        return True

    return SequenceMatcher(None, pred_norm, gold_norm).ratio() >= threshold


def _program_f1_with_matchers(
    pred_programs: list[dict],
    gold_programs: list[dict],
    composer_matcher,
    piece_matcher,
) -> dict:
    if not gold_programs and not pred_programs:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not gold_programs:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}
    if not pred_programs:
        return {"precision": 1.0, "recall": 0.0, "f1": 0.0}

    matched_gold = set()
    true_positives = 0

    for pred in pred_programs:
        for i, gold in enumerate(gold_programs):
            if i in matched_gold:
                continue
            if (
                composer_matcher(pred.get("composer", ""), gold.get("composer", ""))
                and piece_matcher(pred.get("piece", ""), gold.get("piece", ""))
            ):
                true_positives += 1
                matched_gold.add(i)
                break

    precision = true_positives / len(pred_programs) if pred_programs else 0
    recall = true_positives / len(gold_programs) if gold_programs else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {"precision": precision, "recall": recall, "f1": f1}


def program_f1(pred_programs: list[dict], gold_programs: list[dict]) -> dict:
    """v1 프로그램 단위 F1 score 계산 (기존 동작 유지)"""
    return _program_f1_with_matchers(pred_programs, gold_programs, composer_match, piece_match)


def program_f1_v2(pred_programs: list[dict], gold_programs: list[dict]) -> dict:
    """v2 프로그램 단위 F1 score 계산 (정규화 + catalog-aware)"""
    return _program_f1_with_matchers(pred_programs, gold_programs, composer_match_v2, piece_match_v2)
