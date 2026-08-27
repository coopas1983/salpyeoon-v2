from datetime import datetime
from zoneinfo import ZoneInfo
from .ai import ask_json
from .config import BLOCKED_TOPIC_HINTS

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
  "scores": {
    "timeliness": 0,
    "conversation": 0,
    "product_fit": 0,
    "buy_reason": 0,
    "expandability": 0,
    "total": 0
  },
  "no_topic": false,
  "reason_if_no_topic": ""
}
'''


def discover_topic(learning: dict | None = None) -> dict:
    now = datetime.now(KST)
    learning = learning or {}
    prompt = f"""
오늘은 {now:%Y-%m-%d} 한국시간이다.
Google 검색을 직접 사용해서 최근 24~72시간 한국의 생활/소비 이슈를 넓게 조사하라.
고정 카테고리에 갇히지 말고 NEWS + SEASON + CONSUMER TREND 세 레이더를 동시에 본다.
후보 예시는 제철 먹거리, 가격 변화, 날씨/계절로 갑자기 필요한 생활용품, 뷰티/패션 신제품이나 소비 트렌드,
디지털/가전 생활 이슈, 반려생활, 휴가/개학/명절/이사 등이다.

목표는 '핫한 뉴스' 자체가 아니라 아래 다섯 조건이 동시에 높은 오늘의 주제 1개다.
- 시의성 25
- Threads에서 대화가 생길 가능성 20
- 쿠팡 상품과 자연스러운 연결 20
- 지금 살 이유 20
- 하루 동안 정보→욕구→상품→대화 콘텐츠로 확장 가능성 15
총점 100.

정치/범죄/사망/재난/전쟁/투자·코인 이슈는 상품화 후보에서 제외한다.
기사 하나만 보고 고르지 말고 가능하면 서로 다른 출처에서 같은 흐름이 확인되는지 검증한다.
식품에 편향되지 말고 모든 소비 카테고리를 동등하게 경쟁시킨다.
좋은 후보가 없으면 no_topic=true로 답해도 된다.
과거 운영 피드백: {learning}

{SCHEMA}
"""
    plan, citations = ask_json(prompt, use_search=True)
    plan["date"] = now.strftime("%Y-%m-%d")
    plan["discovered_at"] = now.isoformat()
    plan["sources"] = citations[:8]

    blob = f"{plan.get('topic','')} {plan.get('why_now','')}"
    if any(x in blob for x in BLOCKED_TOPIC_HINTS):
        plan["no_topic"] = True
        plan["reason_if_no_topic"] = "안전 제외 주제 감지"
    return plan
