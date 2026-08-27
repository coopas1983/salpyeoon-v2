from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import requests

KST = ZoneInfo("Asia/Seoul")
UA = {"User-Agent": "Mozilla/5.0 SalpyeoonV2/2.0"}

# Broad consumer lenses. These are not final topics; they only make the news radar
# look across food, beauty, home, fashion, pet, digital and seasonal consumption.
NEWS_LENSES = [
    "가격 인하 할인 소비", "제철 출하 가격", "신제품 출시 생활용품",
    "뷰티 화장품 신제품", "가전 생활 신제품", "패션 신제품 유행",
    "반려동물 용품 트렌드", "날씨 폭염 장마 생활용품", "먹거리 유통 신제품",
]


def _text(node, name: str) -> str:
    child = node.find(name)
    return (child.text or "").strip() if child is not None else ""


def _clean(s: str) -> str:
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def _fetch_rss(url: str, limit: int = 20) -> list[dict]:
    try:
        r = requests.get(url, headers=UA, timeout=15)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        out = []
        for item in root.findall(".//item")[:limit]:
            out.append({
                "title": _clean(_text(item, "title")),
                "url": _text(item, "link"),
                "published": _text(item, "pubDate"),
                "summary": _clean(_text(item, "description"))[:500],
            })
        return out
    except Exception as e:
        return [{"error": str(e), "url": url}]


def collect_trends(limit: int = 30) -> list[dict]:
    # Google officially exposes RSS export from Trending Now. RSS is deliberately
    # treated as a signal, not as ground truth or the sole topic source.
    url = "https://trends.google.com/trending/rss?geo=KR"
    rows = _fetch_rss(url, limit=limit)
    for x in rows:
        x["radar"] = "trend"
        x["source"] = "Google Trends Trending Now RSS"
    return rows


def collect_news(per_lens: int = 8) -> list[dict]:
    out = []
    seen = set()
    for lens in NEWS_LENSES:
        url = f"https://news.google.com/rss/search?q={quote_plus(lens + ' when:3d')}&hl=ko&gl=KR&ceid=KR:ko"
        for row in _fetch_rss(url, limit=per_lens):
            key = (row.get("title") or "").lower()
            if not key or key in seen or "error" in row:
                continue
            seen.add(key)
            row.update({"radar": "news", "lens": lens, "source": "Google News RSS"})
            out.append(row)
    return out[:60]


def collect_season(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(KST)
    m, d = now.month, now.day
    signals = []
    # Korean consumer-season cues. They are prompts for verification against the
    # live trend/news radars, not claims that a product is currently trending.
    monthly = {
        1: ["한파/난방", "보습", "설 명절 준비"],
        2: ["신학기 준비", "환절기", "봄맞이 청소"],
        3: ["신학기", "미세먼지", "봄 나들이"],
        4: ["봄 나들이", "자외선", "캠핑"],
        5: ["가정의달", "자외선", "초여름 준비"],
        6: ["장마 대비", "제습/빨래", "여름휴가 준비"],
        7: ["폭염", "냉방", "휴가/물놀이"],
        8: ["늦더위", "휴가 복귀", "가을 제철 시작", "추석 사전 준비"],
        9: ["추석", "가을 제철", "환절기", "캠핑"],
        10: ["가을 나들이", "보습", "겨울 준비"],
        11: ["김장", "난방 준비", "보습", "연말 준비"],
        12: ["한파", "연말/선물", "난방", "홈파티"],
    }
    for label in monthly.get(m, []):
        signals.append({"radar": "season", "signal": label, "date": now.strftime("%Y-%m-%d")})
    return signals


def collect_all() -> dict:
    now = datetime.now(KST)
    return {
        "collected_at": now.isoformat(),
        "trend": collect_trends(),
        "news": collect_news(),
        "season": collect_season(now),
    }
