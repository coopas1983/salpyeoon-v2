살펴온 v2 안정화 수정본

수정 파일:
- src/writer.py
- src/run_stage.py
- src/persona.py
- .github/workflows/salpyeoon-v2.yml

핵심 변경:
1) 90분 이상 늦은 GitHub 예약 실행 폐기
2) workflow concurrency로 state 동시 수정 방지
3) 같은 KST 날짜/같은 stage의 실제 게시 중복 차단
4) salpyeoon-images push 전에 rebase + 최대 3회 retry
5) SOCIAL을 당일 메인 주제 안의 비판매 공감글로 고정
6) SOCIAL topic=null 로그 버그 수정
7) SOCIAL도 ensure_plan/history 사용

적용 후 첫 검증은 workflow_dispatch에서 dry_run=true로 inform/social을 실행하고,
정상 확인 후 실제 스케줄을 그대로 두면 됩니다.
