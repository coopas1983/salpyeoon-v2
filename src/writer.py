import json
import re
from .ai import ask_text, ask_json
from .persona import BASE_PERSONA, STAGE_PERSONAS
from .config import DISCLOSURE, MAX_THREAD_CHARS
from .radar import collect_all


def _learning_text(learning: dict) -> str:
    directives = learning.get("directives", []) if isinstance(learning, dict) else []
    return " / ".join(str(x) for x in directives[:8]) or "아직 데이터 없음"


def _history_text(history: list[dict] | None) -> str:
    if not history:
        return "오늘 앞서 작성된 글 없음"
    rows = []
    for x in history[-5:]:
        text = re.sub(r"https?://\S+", "[링크]", str(x.get("text", "")))
        rows.append(f"- {x.get('stage')}: {text[:500]}")
    return "\n".join(rows)


def _base(stage, plan, learning, history=None):
    return f"""
{BASE_PERSONA}

현재 모드: {STAGE_PERSONAS[stage]}
오늘 메인 주제: {plan.get('topic')}
왜 지금: {plan.get('why_now')}
사람 입장 관심 이유: {plan.get('consumer_hook')}
확장 아이디어: {plan.get('content_angles')}
커뮤니티 방향: {plan.get('community_angle')}
최근 성과에서 배운 점: {_learning_text(learning)}

[오늘 이미 쓴 글]
{_history_text(history)}

중요: 위 글들과 같은 예시, 같은 질문, 같은 결론, 같은 첫 문장 패턴을 반복하지 마라.
같은 하루를 운영하는 한 사람이지만 각 글은 새로운 각도여야 한다.
매 글 끝에 질문을 붙이지 마라. 질문은 정말 자연스러운 단계에서만 사용한다.
'잘 쓴 카피'보다 실제 사람이 휴대폰으로 툭 쓴 글처럼 자연스럽게 쓴다.
Threads 한 게시물이다. 350자 안팎을 목표로 하고, 짧으면 더 좋다.
출력은 게시할 본문만. 제목/설명/따옴표/마크다운 금지.
"""


def write(stage: str, plan: dict, learning: dict, product=None, history=None) -> str:
    prompt = _base(stage, plan, learning, history)
    source = (plan.get("sources") or [{}])[0].get("url", "")

    if stage == "inform":
        prompt += f"""
출근길 정보글이다. 기사에서 알게 된 핵심 한두 포인트만 친구에게 툭 말하듯 쓴다.
기사 요약문/보도자료처럼 쓰지 않는다. 과장하지 않는다.
끝맺음은 정보 공유, 짧은 감상, 가벼운 질문 중 하나를 자연스럽게 고른다.
기사 URL은 코드가 마지막에 보장한다: {source}
"""
    elif stage == "desire":
        prompt += """
점심 전 관심/욕구 글. 상품을 팔지 않고 링크도 넣지 않는다.
주제가 음식이면 먹고 싶은 순간, 뷰티면 준비/사용 장면, 생활이면 불편함이나 계절 변화처럼 카테고리에 맞는 장면을 택한다.
INFORM에서 이미 쓴 물건 목록이나 선택지를 다시 나열하지 않는다.
질문으로 끝내기보다 개인적인 생각, 망설임, 공감 한마디 등으로 끝내는 것을 우선한다.
"""
    elif stage == "sell":
        p = product or {}
        prompt += f"""
오늘 하루 딱 한 번의 제휴상품 글이다. 앞선 흐름에서 자연스럽게 하나 발견한 것처럼 연결하되 실제 구매·사용·비교 경험을 꾸며내지 않는다.
제품명: {p.get('productName')}
현재 표시 가격: {p.get('productPrice')}
로켓배송 여부: {p.get('isRocket')}
무료배송 여부: {p.get('isFreeShipping')}
상품 URL: {p.get('productUrl')}
확인 가능한 정보만 말한다. 리뷰, 품질, 촉감, 효과, 최저가, 할인율을 데이터 없이 단정하지 않는다.
'이것저것 따져봤다', '써봤다', '사봤다', '내가 고른다'처럼 실제 행동을 한 척하지 않는다.
광고 카피처럼 추천을 밀어붙이지 말고 '찾아보니 이런 조건의 제품이 있더라' 정도로 툭 연결한다.
상품 URL과 제휴 고지는 코드가 뒤에 붙이므로 본문에는 URL/고지문을 쓰지 않는다.
굳이 질문으로 끝내지 않는다.
"""
    elif stage == "talk":
        prompt += """
퇴근 전 대화글. 오늘 주제 안에서 앞선 글과 다른 생활 장면/고민/팁거리 하나를 골라 대화판을 연다.
앞에서 침구/커튼/조명처럼 이미 사용한 선택지를 그대로 반복하지 않는다.
맛집이 자연스러우면 지역/메뉴, 뷰티면 취향/루틴, 생활이면 보관/정리/사용습관 등 새로운 하위주제로 이동한다.
실제로 가본 곳/써본 물건인 척하지 않는다. 댓글을 구걸하지 않는다.
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


def write_social(learning: dict, main_topic: str = "") -> tuple[str, list[dict]]:
    """B-plan SOCIAL: external RSS radars collect; Gemini only selects/writes."""
    radar = collect_all()
    candidates = []
    for x in radar.get("trend", [])[:20]:
        if "error" not in x:
            candidates.append(x)
    for x in radar.get("news", [])[:30]:
        if "error" not in x:
            candidates.append(x)

    prompt = f"""
{BASE_PERSONA}
현재 모드: {STAGE_PERSONAS['social']}
인터넷 검색 도구를 사용하지 마라. 아래 외부 수집기가 가져온 후보만 사용한다.
오늘 메인 판매 주제 '{main_topic}'와는 일부러 다른 가벼운 화제를 하나 고른다.
정치, 범죄, 사망, 재난, 전쟁, 투자, 선정적 사건, 확인하기 어려운 루머는 제외한다.
쿠팡/상품/판매 이야기는 절대 하지 않는다.
뉴스봇처럼 요약하지 말고 평범한 사람이 보고 한마디 툭 던지는 Threads 글로 쓴다.
실제로 겪은 일인 척하지 않는다. 사실을 지어내지 않는다.
질문은 꼭 필요할 때만. 250자 안팎, 짧아도 된다.
최근 성과 피드백: {_learning_text(learning)}

후보 데이터:
{json.dumps(candidates, ensure_ascii=False)[:18000]}

JSON 객체 하나만 출력:
{{"text":"게시 본문", "source_title":"선택한 후보의 정확한 title", "source_url":"선택한 후보의 정확한 url"}}
"""
    obj, _ = ask_json(prompt, use_search=False)
    text = str(obj.get("text", "")).strip()[:MAX_THREAD_CHARS]
    source = {"title": obj.get("source_title", ""), "url": obj.get("source_url", ""), "source": "external radar"}
    sources = [source] if source["url"] else []
    return text, sources
