import argparse
import datetime as dt
import json
import os

from .ai import ask_text
from .buffer import create_text_post, list_channels

TARGET_HANDLE = os.getenv("HEAF_THREADS_HANDLE", "agewellkoreanstyle").strip().lower()

THEMES = [
    "a tiny everyday habit you notice in Korea",
    "a Korean phrase whose emotional meaning is different from its literal translation",
    "a small social rule or piece of nunchi in Korean daily life",
    "a Korean food habit explained through ordinary life, not nutrition claims",
    "a home or apartment habit that feels distinctly Korean",
    "a café, convenience-store, or neighborhood observation from Korea",
    "a generational difference in Korean everyday life after age 40",
    "a Korean expression used between friends, couples, or family",
    "a seasonal habit or small tradition people actually experience in Korea",
    "a funny but respectful culture-gap moment a foreign visitor could notice",
    "a Korean word that textbooks translate correctly but fail to explain emotionally",
    "an ordinary Korean routine that can spark a simple question or conversation",
]


def threads_channel_exact():
    matches = []
    for c in list_channels():
        if c.get("service") != "threads":
            continue
        if c.get("isDisconnected") or c.get("isLocked"):
            continue
        names = {
            str(c.get("name") or "").strip().lower(),
            str(c.get("displayName") or "").strip().lower(),
        }
        if TARGET_HANDLE in names:
            matches.append(c)
    if len(matches) != 1:
        available = [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "displayName": c.get("displayName"),
                "service": c.get("service"),
                "isDisconnected": c.get("isDisconnected"),
                "isLocked": c.get("isLocked"),
            }
            for c in list_channels()
            if c.get("service") == "threads"
        ]
        raise RuntimeError(
            f"Expected exactly one usable Threads channel named {TARGET_HANDLE!r}; "
            f"found {len(matches)}. Available Threads channels: {available}"
        )
    return matches[0]


def should_soft_promote(day: dt.date, slot: int) -> bool:
    # About 1 in 20 posts (~5%) if running 3 posts/day.
    ordinal = day.toordinal() * 3 + slot
    return ordinal % 20 == 0


def build_prompt(day: dt.date, slot: int) -> tuple[str, str]:
    theme = THEMES[(day.toordinal() + slot * 3) % len(THEMES)]
    ebook_url = os.getenv("HEAF_EBOOK_URL", "").strip()
    promo = should_soft_promote(day, slot) and bool(ebook_url)

    if promo:
        objective = f"""
This is a rare soft-promotion post for a Korean-language ebook called “You already know the words.”
Do not sound like an ad. Start with a genuinely useful Korean-language or culture insight, then naturally say that this is the kind of nuance collected in the ebook. End with this URL on its own final line:
{ebook_url}
"""
    else:
        objective = """
This is an audience-growth post, not a sales post. Do not mention any product, ebook, website, or link.
End with either a short observation that lands well or one easy question that invites replies.
"""

    prompt = f"""
You write the Threads account @agewellkoreanstyle for English-speaking adults who are curious about real everyday Korea.

Write ONE standalone Threads post in natural English.
Date: {day.isoformat()}
Slot: {slot}
Topic direction: {theme}

Style rules:
- Sound like a real person noticing something interesting, not a brand, lecturer, travel brochure, or AI.
- Strong first sentence. Keep the whole post compact and highly readable on a phone.
- Aim for 180-380 characters; hard maximum 480 characters including line breaks and any URL.
- Use short paragraphs and natural line breaks.
- No headline label such as “Did you know”.
- No hashtags unless one is truly necessary; default to none.
- No emojis by default. At most one if it genuinely improves the post.
- Avoid sweeping claims like “Koreans always…” or “all Koreans…”. Prefer “in Korea,” “you’ll often notice,” or a specific everyday context.
- No medical, financial, political, or unverifiable claims.
- Do not invent statistics or personal experiences.
- Korean words may be included in Hangul when they help the idea, followed by enough English context to understand them.
- Do not repeat the account name.
{objective}

Return only the finished post. No quotation marks, notes, or explanation.
""".strip()
    return prompt, theme


def normalize_post(text: str) -> str:
    text = (text or "").strip()
    if len(text) > 500:
        raise RuntimeError(f"Generated Threads post is too long: {len(text)} chars")
    if not text:
        raise RuntimeError("Generated empty Threads post")
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", type=int, choices=[0, 1, 2], default=0)
    parser.add_argument("--date", default="", help="YYYY-MM-DD; defaults to current KST date")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()

    if args.date:
        day = dt.date.fromisoformat(args.date)
    else:
        kst = dt.timezone(dt.timedelta(hours=9))
        day = dt.datetime.now(kst).date()

    prompt, theme = build_prompt(day, args.slot)
    post, _ = ask_text(prompt, use_search=False)
    post = normalize_post(post)

    result = {
        "date": day.isoformat(),
        "slot": args.slot,
        "theme": theme,
        "target": TARGET_HANDLE,
        "publish": args.publish,
        "draft": args.draft,
        "text": post,
    }

    if args.publish:
        ch = threads_channel_exact()
        mode = "addToQueue" if args.draft else "shareNow"
        # Buffer's draft flag is separate from scheduling mode. For a true draft,
        # keep shareNow mode but save_to_draft=True, matching the existing client helper.
        mode = "shareNow"
        sent = create_text_post(
            ch["id"],
            post,
            mode=mode,
            save_to_draft=args.draft,
        )
        result["buffer"] = sent
        result["channel"] = {
            "id": ch.get("id"),
            "name": ch.get("name"),
            "displayName": ch.get("displayName"),
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
