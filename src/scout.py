import json
from datetime import datetime
from zoneinfo import ZoneInfo

from .ai import ask_json
from .config import BLOCKED_TOPIC_HINTS
from .radar import collect_all

KST = ZoneInfo("Asia/Seoul")

SCHEMA = r'''
반드시 JSON 객체 하나만 출력:
{
  "topic": "오늘의 핵심 주제",
  "category": "food|beauty|home|digital|fashion|pet|seasonal|lifestyle|other",
  "why_now": "왜 오늘 이야기할 가치가 있는지 1~2문장",
  "consumer_hook": "사람 입장에서 지금 관심 가질 이유",
  "product_search_terms": ["쿠팡 검색어1", "검색어2", "검색어3"],
  "content_angles": ["정보/관심 확장 아이디어1", "아이디어2", "아이디어3"],
  "community_angle": "댓글이 붙을 만한 질문 방향",
  "evidence": [{"radar":"trend|news|season", "title":"근거", "url":"있으면 URL"}],
  "scores": {"timeliness":0,"conversation":0,"product_fit":0,"buy_reason":0,"expandability":0,"total":0},
  "no_topic": false,
  "reason_if_no_topic": ""
}
'''


def _compact(data: dict) -> dict:
    return {
        "trend": [x for x in data.get("trend", []) if "error" not in x][:25],
        "news": data.get("news", [])[:45],
        "season": data.get("season", [])[:12],
    }


def discover_topic(learning: dict | None = None) -> dict:
    now = datetime.now(KST)
    learning = learning or {}
    radar = collect_all()
    evidence_pack = _compact(radar)
    prompt = f"""
오늘은 {now:%Y-%m-%d} 한국시간이다.
너는 '살펴온'의 편집장이다. 인터넷 검색 도구를 사용하지 마라.
아래 수집기가 가져온 NEWS + TREND + SEASON 데이터만 근거로 오늘의 소비/생활 주제 1개를 고른다.

중요: 식품에 편향되지 마라. food/beauty/home/digital/fashion/pet/seasonal/lifestyle를 동등하게 경쟁시켜라.
정치/범죄/사망/재난/전쟁/투자·코인은 판매 주제에서 제외한다.
유명인 이름이 검색량이 높다는 이유만으로 고르지 마라.
근거가 약하거나 상품 연결이 억지라면 no_topic=true가 정답이다.
뉴스 1건만 있는 주장보다 trend+news, news+season처럼 서로 다른 레이더가 겹치는 후보를 우대한다.

평가: 시의성25 + Threads 대화20 + 쿠팡 상품 자연스러운 연결20 + 지금 살 이유20 + 콘텐츠 확장15 = 100.
콘텐츠 확장은 요리/맛집으로 고정하지 않는다. 카테고리에 맞춰 사용팁, 비교, 공감, 생활상황, 장소, 취향질문 등으로 설계한다.
과거 운영 피드백: {json.dumps(learning, ensure_ascii=False)[:6000]}

수집 데이터:
{json.dumps(evidence_pack, ensure_ascii=False)[:24000]}

{SCHEMA}
"""
    # B plan: Gemini is editor/decision-maker only. No Google Search grounding.
    plan, _ = ask_json(prompt, use_search=False)
    plan["date"] = now.strftime("%Y-%m-%d")
    plan["discovered_at"] = now.isoformat()
    plan["radar_collected_at"] = radar.get("collected_at")
    plan["radar_counts"] = {k: len(radar.get(k, [])) for k in ("trend", "news", "season")}
    plan["radar_preview"] = evidence_pack
    plan["sources"] = [e for e in plan.get("evidence", []) if e.get("url")][:8]

    blob = f"{plan.get('topic','')} {plan.get('why_now','')}"
    if any(x in blob for x in BLOCKED_TOPIC_HINTS):
        plan["no_topic"] = True
        plan["reason_if_no_topic"] = "안전 제외 주제 감지"
    return plan
