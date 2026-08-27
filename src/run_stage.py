import argparse
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from . import buffer
from .scout import discover_topic
from .product import choose as choose_product
from .writer import write, write_social
from .learner import learn, review
from .baseline import capture as capture_baseline
from .state import load_json, save_json, append_jsonl, load_today_plan, load_today_posts, today

KST = ZoneInfo("Asia/Seoul")


def ensure_plan(state_dir: str, force=False):
    learning = load_json(state_dir, "learning.json", {})
    plan = {} if force else load_today_plan(state_dir)
    if not plan:
        plan = discover_topic(learning)
        save_json(state_dir, "current_plan.json", plan)
        save_json(state_dir, f"history/{today()}-plan.json", plan)
    return plan, learning


def publish_text(text: str, draft: bool):
    ch = buffer.threads_channel()
    return buffer.create_text_post(ch["id"], text, mode="addToQueue" if draft else "shareNow", save_to_draft=draft)


def log_post(state_dir, stage, plan, text, response, extra=None):
    row = {
        "at": datetime.now(KST).isoformat(),
        "date": today(),
        "stage": stage,
        "topic": plan.get("topic") if plan else None,
        "text": text,
        "buffer_post_id": (response or {}).get("id"),
    }
    if extra:
        row.update(extra)
    append_jsonl(state_dir, "post_log.jsonl", row)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["baseline", "discover", "inform", "desire", "sell", "talk", "social", "learn", "weekly", "monthly"], required=True)
    ap.add_argument("--state-dir", default="state")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--no-publish", action="store_true")
    args = ap.parse_args()
    Path(args.state_dir).mkdir(parents=True, exist_ok=True)

    if args.stage == "baseline":
        baseline = capture_baseline(7)
        save_json(args.state_dir, "baseline.json", baseline)
        print(json.dumps(baseline, ensure_ascii=False, indent=2))
        return

    if args.stage == "discover":
        plan, _ = ensure_plan(args.state_dir, force=True)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    if args.stage in ("learn", "weekly", "monthly"):
        existing = load_json(args.state_dir, "learning.json", {})
        baseline = load_json(args.state_dir, "baseline.json", {})
        if args.stage == "learn":
            learned = learn(existing, baseline)
            save_json(args.state_dir, "learning.json", learned)
        elif args.stage == "weekly":
            learned = review(existing, baseline, days=7, horizon="weekly")
            save_json(args.state_dir, "reviews/weekly-latest.json", learned)
            save_json(args.state_dir, f"reviews/{today()}-weekly.json", learned)
            # 주간 검토의 구체 지침은 다음날 생성에도 참고하도록 합친다.
            save_json(args.state_dir, "learning.json", learned)
        else:
            learned = review(existing, baseline, days=30, horizon="monthly-strategy")
            save_json(args.state_dir, "reviews/monthly-latest.json", learned)
            save_json(args.state_dir, f"reviews/{today()}-monthly.json", learned)
        print(json.dumps(learned, ensure_ascii=False, indent=2))
        return

    if args.stage == "social":
        learning = load_json(args.state_dir, "learning.json", {})
        plan = load_today_plan(args.state_dir)
        text, sources = write_social(learning, plan.get("topic", ""))
        # 검색 근거가 있는 글이면 첫 출처를 덧붙이되, 단순 공감문이면 모델이 링크 없이 끝내도 된다.
        response = None if args.no_publish else publish_text(text, args.draft)
        row = log_post(args.state_dir, "social", {}, text, response, {"sources": sources[:5]})
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return

    plan, learning = ensure_plan(args.state_dir)
    if plan.get("no_topic"):
        print(json.dumps({"skip": True, "stage": args.stage, "reason": plan.get("reason_if_no_topic", "no topic")}, ensure_ascii=False, indent=2))
        return

    product = None
    extra = {}
    if args.stage == "sell":
        pick = choose_product(plan.get("product_search_terms", []))
        if not pick:
            print(json.dumps({"skip": True, "stage": "sell", "reason": "no relevant Coupang product"}, ensure_ascii=False, indent=2))
            return
        product = pick.product
        extra = {"product": product, "product_keyword": pick.keyword, "product_score": pick.score}

    history = load_today_posts(args.state_dir)
    text = write(args.stage, plan, learning, product, history=history)
    response = None if args.no_publish else publish_text(text, args.draft)
    row = log_post(args.state_dir, args.stage, plan, text, response, extra)
    print(json.dumps(row, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
