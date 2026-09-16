"""OpenAI-compatible chat transport. urllib only. Never logs keys."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def openai_chat(base_url: str, api_key: str, model: str,
                prompt: str, timeout: int = 60) -> tuple[str, int, int]:
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    if api_key:
        req.add_header("Authorization", "Bearer " + api_key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e
    except Exception as e:
        raise RuntimeError(f"transport: {e}") from e
    try:
        text = payload["choices"][0]["message"]["content"]
        usage = payload.get("usage", {})
        return (str(text), int(usage.get("prompt_tokens", 0)),
                int(usage.get("completion_tokens", 0)))
    except Exception as e:
        raise RuntimeError(f"bad response shape: {e}") from e
