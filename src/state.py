import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def _path(root, name):
    p = Path(root) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_json(root, name, default):
    p = _path(root, name)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(root, name, value):
    _path(root, name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(root, name, value):
    p = _path(root, name)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")


def today():
    return datetime.now(KST).strftime("%Y-%m-%d")


def load_today_plan(root):
    plan = load_json(root, "current_plan.json", {})
    return plan if plan.get("date") == today() else {}
