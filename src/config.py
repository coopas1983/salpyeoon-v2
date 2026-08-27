import os

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
THREADS_SERVICE = "threads"
MAX_THREAD_CHARS = int(os.getenv("MAX_THREAD_CHARS", "480"))
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."

# 상품화하면 안 되는 이슈. 조회수보다 계정 안전/신뢰를 우선한다.
BLOCKED_TOPIC_HINTS = [
    "정치", "대통령", "선거", "정당", "범죄", "살인", "사망", "참사", "재난",
    "전쟁", "테러", "성범죄", "아동학대", "자살", "실종", "주가", "코인 급등",
]
