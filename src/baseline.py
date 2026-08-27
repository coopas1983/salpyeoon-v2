from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from . import buffer

KST = ZoneInfo("Asia/Seoul")


def capture(days: int = 7) -> dict:
    posts = buffer.sent_posts_with_metrics(100)
    cutoff = datetime.now(KST) - timedelta(days=days)
    kept = []
    for p in posts:
        due = p.get("dueAt") or p.get("sentAt") or ""
        try:
            dt = datetime.fromisoformat(due.replace("Z", "+00:00")).astimezone(KST)
            if dt < cutoff:
                continue
        except Exception:
            pass
        kept.append(p)
    return {
        "captured_at": datetime.now(KST).isoformat(),
        "window_days": days,
        "purpose": "V2 시작 전 비교 기준. 존재하지 않는 metric은 추정하지 않는다.",
        "post_count": len(kept),
        "posts": kept,
        "manual_context": {
            "legacy_structure": "하루 상품 중심 자동게시(과일/뷰티/생활 카테고리 슬롯)",
            "known_issue": "Threads 노출이 매우 낮아 클릭/자연구매 검증 단계까지 도달하지 못함"
        }
    }
