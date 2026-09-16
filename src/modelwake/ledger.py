"""SQLite cost ledger. One file, no server. Stdlib sqlite3 only."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

SCHEMA = """CREATE TABLE IF NOT EXISTS usage(
  ts REAL, model TEXT, tier TEXT, prompt_chars INTEGER,
  in_tokens INTEGER, out_tokens INTEGER, cost_usd REAL, ok INTEGER, error TEXT
)"""

COOLDOWN_SCHEMA = """CREATE TABLE IF NOT EXISTS cooldowns(
  model TEXT PRIMARY KEY, until_ts REAL
)"""


def _connect(db: str | Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db))
    con.execute(SCHEMA)
    con.execute(COOLDOWN_SCHEMA)
    return con


def log(db: str | Path, *, model: str, tier: str, prompt_chars: int,
        in_tokens: int, out_tokens: int, cost_usd: float,
        ok: bool = True, error: str = "") -> None:
    con = _connect(db)
    try:
        con.execute(
            "INSERT INTO usage VALUES(?,?,?,?,?,?,?,?,?)",
            (time.time(), model, tier, prompt_chars, in_tokens,
             out_tokens, cost_usd, 1 if ok else 0, error),
        )
        con.commit()
    finally:
        con.close()


def summary(db: str | Path) -> list[dict]:
    p = Path(str(db))
    if not p.exists():
        return []
    con = sqlite3.connect(str(db))
    try:
        rows = con.execute(
            "SELECT model, COUNT(*), SUM(in_tokens), SUM(out_tokens),"
            " SUM(cost_usd), SUM(ok) FROM usage GROUP BY model ORDER BY 5"
        ).fetchall()
    finally:
        con.close()
    return [
        {"model": m, "calls": n, "in_tokens": it or 0, "out_tokens": ot or 0,
         "cost_usd": c or 0.0, "ok": o or 0}
        for m, n, it, ot, c, o in rows
    ]


def set_cooldown(db: str | Path, model: str, seconds: float) -> None:
    """Park a rate-limited model until now+seconds. Negative seconds clears it."""
    con = _connect(db)
    try:
        con.execute("DELETE FROM cooldowns WHERE until_ts <= ?", (time.time(),))
        if seconds > 0:
            con.execute(
                "INSERT OR REPLACE INTO cooldowns VALUES(?,?)",
                (model, time.time() + seconds),
            )
        else:
            con.execute("DELETE FROM cooldowns WHERE model = ?", (model,))
        con.commit()
    finally:
        con.close()


def cooling_down(db: str | Path) -> list[dict]:
    """Models still parked, with seconds remaining. Missing db -> []."""
    p = Path(str(db))
    if not p.exists():
        return []
    now = time.time()
    con = sqlite3.connect(str(db))
    try:
        con.execute(COOLDOWN_SCHEMA)
        rows = con.execute(
            "SELECT model, until_ts FROM cooldowns WHERE until_ts > ?"
            " ORDER BY until_ts",
            (now,),
        ).fetchall()
    finally:
        con.close()
    return [{"model": m, "retry_in": max(0, int(u - now))} for m, u in rows]
