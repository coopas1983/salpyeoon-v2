from .ai import ask_text
from .persona import BASE_PERSONA, STAGE_PERSONAS
from .config import DISCLOSURE, MAX_THREAD_CHARS


def _learning_text(learning: dict) -> str:
    directives = learning.get("directives", []) if isinstance(learning, dict) else []
    return " / ".join(str(x) for x in directives[:8]) or "아직 데이터 없음"


def _base(stage, plan, learning):
    return f"""
{BASE_PERSONA}

현재 모드: {STAGE_PERSONAS[stage]}
오늘 메인 주제: {plan.get('topic')}
왜 지금: {plan.get('why_now')}
사람 입장 관심 이유: {plan.get('consumer_hook')}
확장 아이디어: {plan.get('content_angles')}
커뮤니티 방향: {plan.get('community_angle')}
최근 성과에서 배운 점: {_learning_text(learning)}

Threads 한 게시물이다. 350자 안팎을 목표로 하고, 짧으면 더 좋다.
한 줄씩 너무 반듯하게 정리하지 말고 실제 사람이 쓴 듯 자연스럽게 쓴다.
출력은 게시할 본문만. 제목/설명/따옴표/마크다운 금지.
"""


def write(stage: str, plan: dict, learning: dict, product=None) -> str:
    prompt = _base(stage, plan, learning)
    source = (plan.get("sources") or [{}])[0].get("url", "")

    if stage == "inform":
        prompt += f"""
출근길 정보글. 기사에서 알게 된 핵심을 한두 포인트만 자연스럽게 언급하고 '이거 봤어?' 느낌으로 쓴다.
기사 내용을 길게 요약하지 않는다. 사실을 과장하지 않는다.
이 기사 URL은 본문 마지막에 그대로 붙여야 한다: {source}
"""
    elif stage == "desire":
        prompt += """
점심 전 관심/욕구 글. 상품을 팔지 않는다. 링크도 넣지 않는다.
주제가 음식이면 먹고 싶은 장면, 뷰티면 사용 상황, 생활용품이면 불편한 순간처럼 카테고리에 맞는 욕구를 스스로 선택한다.
"""
    elif stage == "sell":
        p = product or {}
        prompt += f"""
오늘 하루 딱 한 번의 제휴상품 글이다. 오전부터 이어진 주제 흐름을 기억하는 사람처럼 쓴다.
제품명: {p.get('productName')}
현재 표시 가격: {p.get('productPrice')}
로켓배송 여부: {p.get('isRocket')}
무료배송 여부: {p.get('isFreeShipping')}
상품 URL: {p.get('productUrl')}
확인 가능한 정보만 말하고, 리뷰/할인율/최저가를 지어내지 않는다.
상품 URL과 제휴 고지는 코드가 뒤에 붙이므로 본문에는 URL/고지문을 쓰지 않는다.
"""
    elif stage == "talk":
        prompt += """
퇴근 전 대화글. 맛집이 자연스러운 주제면 맛집/지역 질문을, 뷰티면 취향/사용법, 생활용품이면 생활 습관처럼 주제에 맞게 변형한다.
실제로 가본 곳/써본 물건인 척하지 않는다. 댓글을 구걸하지 말고 사람들이 자기 경험을 말하고 싶게 만든다.
"""
    else:
        raise ValueError(stage)

    text, _ = ask_text(prompt, use_search=False)
    text = text.strip()
    if stage == "inform" and source and source not in text:
        text = text.rstrip() + "\n\n" + source
    if stage == "sell":
        url = (product or {}).get("productUrl", "")
        suffix = f"\n\n{url}\n\n{DISCLOSURE}" if url else f"\n\n{DISCLOSURE}"
        room = max(80, MAX_THREAD_CHARS - len(suffix))
        text = text[:room].rstrip() + suffix
    return text[:MAX_THREAD_CHARS]


def write_social(learning: dict) -> tuple[str, list[dict]]:
    prompt = f"""
{BASE_PERSONA}
현재 모드: {STAGE_PERSONAS['social']}
오늘 한국에서 사람들이 가볍게 이야기할 만한 생활/문화/직장/날씨/소비/웃긴 일상 화제를 Google 검색으로 찾아라.
정치, 범죄, 사망, 재난, 전쟁, 선정적 사건은 제외한다.
쿠팡/상품/판매 이야기는 절대 하지 않는다. 사실을 지어내지 않는다.
뉴스봇처럼 요약하지 말고, 살펴온 운영자가 보고 한마디 던지는 짧은 Threads 글로 써라.
최근 성과 피드백: {_learning_text(learning)}
출력은 게시 본문만. 300자 이하. 마크다운/제목 금지.
"""
    return ask_text(prompt, use_search=True)
