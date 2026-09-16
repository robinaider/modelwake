"""`modelwake` CLI. Stdlib only. Exit codes: 0 ok, 1 route failed, 2 usage."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from . import ledger as ledger_mod
from .config import load as load_config
from .router import auto_tier, route
from .transport import openai_chat


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="modelwake",
                                 description="Wake the right model — route, fallback, ledger.")
    ap.add_argument("--version", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    r = sub.add_parser("route", help="route one prompt through the tier chain")
    r.add_argument("--config", required=True)
    r.add_argument("--prompt", required=True)
    r.add_argument("--tier", default="auto", help="SIMPLE|MEDIUM|COMPLEX|auto")
    r.add_argument("--timeout", type=int, default=60)
    r.add_argument("--db", default="modelwake.db")
    r.add_argument("--no-ledger", action="store_true")

    c = sub.add_parser("costs", help="show spend per model from the ledger")
    c.add_argument("--db", default="modelwake.db")

    e = sub.add_parser("tiers", help="show tier chains from config")
    e.add_argument("--config", required=True)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if getattr(args, "version", False):
        print(f"modelwake {__version__}")
        return 0
    if args.cmd == "tiers":
        try:
            cfg = load_config(args.config)
        except Exception as ex:
            print(f"modelwake: {ex}", file=sys.stderr)
            return 2
        for tier, chain in sorted(cfg.tiers.items()):
            print(f"{tier}: {' -> '.join(chain)}")
        return 0
    if args.cmd == "costs":
        rows = ledger_mod.summary(args.db)
        if not rows:
            print("no usage logged yet")
            return 0
        total = sum(r["cost_usd"] for r in rows)
        for r in rows:
            print(f'{r["model"]}: {r["calls"]} calls, '
                  f'{r["in_tokens"]} in / {r["out_tokens"]} out, '
                  f'${r["cost_usd"]:.4f}, ok {r["ok"]}/{r["calls"]}')
        print(f"total: ${total:.4f}")
        return 0
    if args.cmd == "route":
        try:
            cfg = load_config(args.config)
        except Exception as ex:
            print(f"modelwake: {ex}", file=sys.stderr)
            return 2
        tier = auto_tier(args.prompt) if args.tier == "auto" else args.tier.upper()
        try:
            res = route(cfg, tier, args.prompt, openai_chat, timeout=args.timeout)
        except Exception as ex:
            if not args.no_ledger:
                ledger_mod.log(args.db, model="(none)", tier=tier,
                               prompt_chars=len(args.prompt),
                               in_tokens=0, out_tokens=0, cost_usd=0.0,
                               ok=False, error=str(ex)[:300])
            print(f"modelwake: {ex}", file=sys.stderr)
            return 1
        if not args.no_ledger:
            ledger_mod.log(args.db, model=res.model_key, tier=tier,
                           prompt_chars=len(args.prompt),
                           in_tokens=res.in_tokens, out_tokens=res.out_tokens,
                           cost_usd=res.cost_usd, ok=True)
        print(f"[{res.model_key} ${res.cost_usd:.4f}] {res.text}")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
