import re
from dataclasses import dataclass
from . import coupang

BAD = ["해외직구", "리퍼", "중고", "렌탈", "정기구독"]

@dataclass
class ProductPick:
    product: dict
    keyword: str
    score: float


def _tokens(text: str):
    return [t for t in re.findall(r"[0-9A-Za-z가-힣]+", (text or "").lower()) if len(t) >= 2]


def score(p: dict, keyword: str, rank: int) -> float:
    name = (p.get("productName") or "").lower()
    if any(x in name for x in BAD):
        return -999
    toks = _tokens(keyword)
    hits = sum(1 for t in toks if t in name)
    if toks and hits == 0:
        return -100
    s = hits * 12
    if p.get("isRocket"):
        s += 16
    if p.get("isFreeShipping"):
        s += 8
    s += max(0, 20 - rank * 2)
    price = int(p.get("productPrice") or 0)
    if 5000 <= price <= 50000:
        s += 14
    elif 50000 < price <= 150000:
        s += 8
    elif 0 < price < 5000:
        s += 4
    return s


def _clean_keyword(keyword: str) -> str:
    kw = re.sub(r"\s+", " ", (keyword or "").strip())
    # Known high-risk Korean shopping typo seen in dry-run; harmless normalization.
    kw = kw.replace("차엽", "차렵")
    return kw


def choose(search_terms: list[str]) -> ProductPick | None:
    candidates = []
    cleaned = []
    for raw in (search_terms or [])[:4]:
        kw = _clean_keyword(raw)
        if kw and kw not in cleaned:
            cleaned.append(kw)
    for kw in cleaned:
        try:
            for rank, p in enumerate(coupang.search(kw, 10), 1):
                s = score(p, kw, rank)
                if s > -90:
                    candidates.append(ProductPick(p, kw, s))
        except Exception as e:
            print(f"WARN coupang search failed [{kw}]: {e}")
    if not candidates:
        return None
    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates[0] if candidates[0].score >= 20 else None
