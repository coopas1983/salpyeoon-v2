import json
import os
import re
from typing import Any
from google import genai
from .config import GEMINI_MODEL


def client():
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    # ```json ... ``` 또는 앞뒤 설명이 섞여도 첫 JSON 객체를 찾아 복구한다.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end+1]
    return json.loads(text)


def _citations(interaction) -> list[dict]:
    out = []
    seen = set()
    for step in getattr(interaction, "steps", []) or []:
        if getattr(step, "type", None) != "model_output":
            continue
        for block in getattr(step, "content", []) or []:
            for ann in getattr(block, "annotations", []) or []:
                if getattr(ann, "type", None) != "url_citation":
                    continue
                url = getattr(ann, "url", None)
                title = getattr(ann, "title", None) or ""
                if url and url not in seen:
                    seen.add(url)
                    out.append({"title": title, "url": url})
    return out


def ask_json(prompt: str, use_search: bool = False) -> tuple[dict, list[dict]]:
    kwargs = {"model": GEMINI_MODEL, "input": prompt}
    if use_search:
        kwargs["tools"] = [{"type": "google_search"}]
    interaction = client().interactions.create(**kwargs)
    return _extract_json(interaction.output_text), _citations(interaction)


def ask_text(prompt: str, use_search: bool = False) -> tuple[str, list[dict]]:
    kwargs = {"model": GEMINI_MODEL, "input": prompt}
    if use_search:
        kwargs["tools"] = [{"type": "google_search"}]
    interaction = client().interactions.create(**kwargs)
    return (interaction.output_text or "").strip(), _citations(interaction)
