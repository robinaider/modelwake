"""Routing: tier -> fallback chain, first success wins. Pure logic, transport injected."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .config import Config

Transport = Callable[[str, str, str, str, int], tuple[str, int, int]]
# (base_url, api_key, model, prompt, timeout) -> (text, in_tokens, out_tokens)


@dataclass
class RouteResult:
    model_key: str
    text: str
    in_tokens: int
    out_tokens: int
    cost_usd: float
    attempted: list[str]


def auto_tier(prompt: str) -> str:
    """Sub-millisecond heuristic. No LLM call. Long/code prompts escalate."""
    p = prompt.lower()
    code_markers = ("def ", "class ", "import ", "```", "traceback", "error:", "sql", "regex")
    if len(prompt) > 3000 or sum(p.count(m) for m in code_markers) >= 3:
        return "COMPLEX"
    if len(prompt) > 800 or any(m in p for m in code_markers):
        return "MEDIUM"
    return "SIMPLE"


def pick_chain(cfg: Config, tier: str) -> list[str]:
    t = tier.upper()
    if t in cfg.tiers:
        return list(cfg.tiers[t])
    # Unknown tier: cheapest-first union, deduped, preserves config order.
    seen: list[str] = []
    for chain in cfg.tiers.values():
        for key in chain:
            if key not in seen:
                seen.append(key)
    return seen


def cost_usd(cfg: Config, model_key: str, in_tok: int, out_tok: int) -> float:
    m = cfg.models[model_key]
    return in_tok / 1000.0 * m.price_in_per_1k + out_tok / 1000.0 * m.price_out_per_1k


def is_rate_limit_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return ("429" in s or "rate limit" in s or "rate-limit" in s
            or "too many requests" in s or "quota" in s)


def route(cfg: Config, tier: str, prompt: str, transport: Transport,
          timeout: int = 60, db: str | None = None,
          cooldown_secs: int = 60) -> RouteResult:
    from . import ledger as ledger_mod
    from .config import api_key_for

    chain = pick_chain(cfg, tier)
    # Free-tier rotation: cooled-down models go last so one's 429 is
    # another's turn. If everything is cooling, we still try in order —
    # a cooldown may have expired mid-flight — but say so on failure.
    cooled: set[str] = set()
    if db:
        cooled = {c["model"] for c in ledger_mod.cooling_down(db)}
    order = [k for k in chain if k not in cooled]
    order += [k for k in chain if k in cooled]
    attempted: list[str] = []
    errors: list[str] = []
    for key in order:
        m = cfg.models[key]
        attempted.append(key)
        try:
            text, itok, otok = transport(m.base_url, api_key_for(m), m.model,
                                         prompt, timeout)
        except Exception as e:  # fallback is the feature, not a crash
            errors.append(f"{key}: {e}")
            if db and is_rate_limit_error(e):
                ledger_mod.set_cooldown(db, key, cooldown_secs)
            continue
        return RouteResult(model_key=key, text=text, in_tokens=itok,
                           out_tokens=otok,
                           cost_usd=cost_usd(cfg, key, itok, otok),
                           attempted=list(attempted))
    hint = ""
    if cooled and set(chain) <= cooled:
        waits = {c["model"]: c["retry_in"] for c in ledger_mod.cooling_down(db)}  # type: ignore[arg-type]
        soonest = min(waits.values()) if waits else cooldown_secs
        hint = f" (all {len(chain)} cooling down — retry in ~{soonest}s)"
    raise RuntimeError("all models failed" + hint + ": " + " | ".join(errors))
