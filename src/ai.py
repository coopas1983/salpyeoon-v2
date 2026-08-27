import json
import os
import re
from typing import Any

from google import genai
from google.genai import types

from .config import GEMINI_MODEL


_CLIENT = None


def client():
    """Return one long-lived Gemini client per process.

    Keeping the client alive avoids the transient-client lifecycle issue that can
    close the underlying httpx client before an API request is sent.
    """
    global _CLIENT
    if _CLIENT is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT


def _extract_json(text: str) -> Any:
    text = (text or "").strip()
    # ```json ... ``` 또는 앞뒤 설명이 섞여도 첫 JSON 객체를 찾아 복구한다.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


def _citations(response) -> list[dict]:
    """Extract unique web sources from Gemini grounding metadata.

    This is intentionally defensive because the SDK may expose metadata as
    typed objects whose optional fields vary slightly by version/model.
    """
    out: list[dict] = []
    seen: set[str] = set()

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        grounding = getattr(candidate, "grounding_metadata", None)
        if not grounding:
            continue

        chunks = getattr(grounding, "grounding_chunks", None) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if not web:
                continue
            url = getattr(web, "uri", None) or getattr(web, "url", None)
            title = getattr(web, "title", None) or ""
            if url and url not in seen:
                seen.add(url)
                out.append({"title": title, "url": url})

    return out


def _generate(prompt: str, use_search: bool = False):
    """Use the stable generate_content API instead of experimental Interactions."""
    config = None
    if use_search:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )

    return client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=config,
    )


def ask_json(prompt: str, use_search: bool = False) -> tuple[dict, list[dict]]:
    response = _generate(prompt, use_search=use_search)
    return _extract_json(response.text or ""), _citations(response)


def ask_text(prompt: str, use_search: bool = False) -> tuple[str, list[dict]]:
    response = _generate(prompt, use_search=use_search)
    return (response.text or "").strip(), _citations(response)
