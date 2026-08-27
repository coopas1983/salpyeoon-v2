from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .ai import ask_json
from . import buffer

KST = ZoneInfo("Asia/Seoul")


def _recent_posts(days: int, limit: int = 100):
    posts = buffer.sent_posts_with_metrics(limit)
    cutoff = datetime.now(KST) - timedelta(days=days)
    recent = []
    for p in posts:
        due = p.get("dueAt") or p.get("sentAt") or ""
        measured_at = datetime.now(KST).isoformat()
        age_hours = None
        try:
            dt = datetime.fromisoformat(due.replace("Z", "+00:00")).astimezone(KST)
            if dt < cutoff:
                continue
            age_hours = round((datetime.now(KST) - dt).total_seconds() / 3600, 1)
        except Exception:
            pass
        q = dict(p)
        q["_measurement"] = {"measured_at": measured_at, "post_age_hours": age_hours}
        recent.append(q)
    return recent


def _prompt(existing, recent, horizon, baseline):
    return f"""
너는 살펴온 계정의 내부 성과 분석가다. 밖으로 글을 쓰지 않는다.
핵심 불변 규칙: '게시 성공'은 성공이 아니다. 노출→반응→클릭→구매를 분리해서 측정하고 다음 행동을 결정해야 한 사이클이 끝난다.

분석 기간: {horizon}
기준선(Baseline): {baseline}
기존 학습값: {existing}
최근 실제 데이터: {recent}

[데이터 신선도]
- 각 게시물의 _measurement.measured_at과 post_age_hours를 반드시 고려한다.
- 게시 직후라 집계가 덜 된 데이터와 충분히 지난 데이터를 같은 조건으로 비교하지 않는다.
- 값이 존재한다는 이유만으로 최신/완전한 데이터라고 가정하지 않는다.
- 없는 조회/클릭/구매 수치는 절대 만들어내지 않는다.

[실패 원인 레인 — 반드시 분리]
1. EXPOSURE: 노출/조회가 낮다 → 주제, 후킹, 시간대, 계정 활동을 의심.
2. ENGAGEMENT: 노출은 있는데 반응/댓글이 약하다 → 글 형식, 페르소나, 대화 유도를 의심.
3. CLICK: 반응은 있는데 제휴 클릭이 약하다 → 상품 연결 타이밍/문구/관련성을 의심.
4. CONVERSION: 클릭은 있는데 구매가 약하다 → 상품, 가격, 구매매력, 랜딩을 의심.
5. WIN: 구매까지 발생 → 주제×시간×페르소나×흐름 조합을 승리 패턴 후보로 기록.
클릭/구매 데이터가 없으면 CLICK/CONVERSION은 unknown으로 둔다.

[과잉학습 금지]
- 표본이 작으면 confidence를 낮춘다.
- 하루 한 게시물이 튄 것만으로 전체 전략을 뒤집지 않는다.
- 무엇이 성공했고 무엇이 실패했는지를 한 점수로 뭉개지 않는다.

JSON 객체 하나만 출력:
{{
  "horizon": "{horizon}",
  "summary": "짧은 분석",
  "lanes": {{
    "exposure": {{"status":"win|weak|unknown", "evidence":""}},
    "engagement": {{"status":"win|weak|unknown", "evidence":""}},
    "click": {{"status":"win|weak|unknown", "evidence":""}},
    "conversion": {{"status":"win|weak|unknown", "evidence":""}}
  }},
  "directives": ["다음 행동 규칙"],
  "avoid": ["줄일 패턴"],
  "promote": ["늘릴 패턴"],
  "winning_patterns": [],
  "confidence": "low|medium|high",
  "sample_size": {len(recent)},
  "data_freshness_note": "",
  "updated_at": "{datetime.now(KST).isoformat()}"
}}
"""


def review(existing: dict | None = None, baseline: dict | None = None, days: int = 1, horizon: str = "daily") -> dict:
    existing = existing or {}
    baseline = baseline or {}
    recent = _recent_posts(days)
    learned, _ = ask_json(_prompt(existing, recent, horizon, baseline), use_search=False)
    return learned


def learn(existing: dict | None = None, baseline: dict | None = None) -> dict:
    return review(existing, baseline, days=1, horizon="daily")
