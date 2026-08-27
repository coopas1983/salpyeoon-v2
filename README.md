# 살펴온 V2 — AI 운영자형 Threads 자동화

V1의 `아침 과일 / 점심 뷰티 / 저녁 생활용품` 고정 상품 자동게시를 버리고,
**오늘의 소비 이슈를 먼저 찾고 하루 동안 관심을 만든 뒤 상품은 1번만 제안**하는 구조로 다시 설계한 버전입니다.

## 하루 흐름

1. **DISCOVER** — Gemini + Google Search로 NEWS / SEASON / CONSUMER TREND를 동시에 조사해 오늘 주제 선정
2. **INFORM** — 출근길: 이슈/기사 기반 짧은 정보글
3. **DESIRE** — 점심 전: 먹고 싶다/써보고 싶다/필요하다를 만드는 관심 글 (링크 없음)
4. **SELL** — 점심 후: 주제에 맞는 쿠팡 상품 1개만 검색/선정해 제휴 링크 게시
5. **TALK** — 퇴근 전: 맛집/취향/생활습관 등 카테고리에 맞는 참여형 글
6. **SOCIAL** — 저녁: 메인 주제와 무관한 가벼운 생활/문화 화제 글
7. **LEARN** — Buffer의 실제 Threads post metrics를 읽어 다음 글의 규칙으로 저장

## 페르소나

7명이 글을 쓰는 구조가 아니라 **'살펴온' 한 명의 운영자**가 상황에 따라 말투만 바뀝니다.
공통 규칙과 단계별 목소리는 `src/persona.py`에 있습니다.

- 확인되지 않은 사용/방문 경험을 1인칭으로 만들지 않음
- AI/블로그 상투어 금지
- 링크 판매글은 하루 1회
- 정치/범죄/사망/재난 등 민감 이슈 상품화 금지
- 좋은 소비 이슈가 없으면 `no_topic=true`로 판매 흐름 자체를 건너뜀

## 새로 필요한 GitHub Secret

기존 Secret은 그대로 사용합니다.

- `COUPANG_ACCESS_KEY`
- `COUPANG_SECRET_KEY`
- `COUPANG_SUB_ID`
- `BUFFER_API_KEY`
- `SALPYEOON_IMAGES_TOKEN` (V2에서는 이미지가 아니라 상태 JSON 저장소 쓰기에도 사용)
- **`GEMINI_API_KEY`** (새로 필요)

`GEMINI_MODEL`은 Repository Variable이며 기본값은 `gemini-3.7-flash`입니다.

## 안전하게 테스트하는 순서

새 workflow는 스케줄이 들어 있지만, Repository variable `SALPYEOON_V2_ENABLED=true`가 없으면 예약 job은 실행되지 않습니다.

처음에는 Actions → `salpyeoon-v2-agent` → Run workflow에서:

1. `stage=discover`, `dry_run=true`
2. 결과의 주제/근거/검색어 확인
3. `inform → desire → sell → talk → social`을 각각 `dry_run=true`로 확인
4. 문체와 상품 연결이 괜찮으면 `dry_run=false`, `draft=true`로 Buffer draft 테스트
5. 마지막으로 실제 게시 테스트
6. 검증 후 Repository variable `SALPYEOON_V2_ENABLED=true` 설정

## 상태 저장

기존 `salpyeoon-images` 저장소의 아래 경로를 사용합니다.

- `data/v2/current_plan.json` — 오늘의 주제
- `data/v2/history/YYYY-MM-DD-plan.json` — 날짜별 주제 기록
- `data/v2/post_log.jsonl` — 발행 로그/Buffer post id
- `data/v2/learning.json` — 최근 성과에서 배운 운영 규칙

## V1에서 재사용한 것

- 쿠팡 HMAC 인증/API 호출 구조
- Buffer GraphQL 연결 구조
- GitHub Actions + `salpyeoon-images` 저장소/token 구조

V1의 월별 과일/뷰티/생활용품 고정 리스트, 상품 카드 이미지, 3회 상품 게시 구조는 제거했습니다.

## V2.1 측정/학습 보강

공개 에이전트 설계에서 참고한 원칙을 살펴온 목적에 맞게 재구성했습니다.

- **BASELINE**: V2 시작 전 최근 7일 데이터를 `baseline.json`에 저장합니다. 첫 실전 가동 전에 workflow_dispatch에서 `baseline`을 1회 실행하세요.
- **데이터 신선도**: LEARN은 metric 값뿐 아니라 측정시각과 게시 후 경과시간을 함께 봅니다.
- **4개 성과 레인 분리**: Exposure(노출) / Engagement(반응) / Click(클릭) / Conversion(구매)을 한 점수로 뭉개지 않습니다.
- **Daily LEARN**: 매일 전날 데이터를 보고 작은 조정을 합니다.
- **Weekly Review**: 일요일 밤 최근 7일 패턴을 재평가하고 다음 주 생성 규칙에 반영합니다.
- **Monthly Strategy**: 매월 1일 최근 30일을 보고 큰 전략을 재평가합니다. 월간 결과는 자동으로 당일 전략을 뒤집지 않고 별도 리뷰로 보존합니다.
- **불변 규칙**: 게시 성공은 완료가 아닙니다. 측정하고 다음 행동이 정해져야 한 사이클이 완료됩니다.

클릭/구매 metric이 Buffer에서 제공되지 않는 경우 시스템은 해당 레인을 `unknown`으로 처리합니다. 쿠팡 성과 데이터를 자동으로 읽는 연결은 별도 단계로 추가할 수 있습니다.
