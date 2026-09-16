# Changelog

## [0.2.0] - 2026-09-16
- Free chain: `examples/free.toml` ($0 local -> OpenRouter :free -> Gemini free), `modelwake free` status command, `docs/FREE_MODELS.md`.
- 429-cooldown rotation: rate-limited models park for 60s and go last; honest "all cooling, retry in Ns" error.
- `route` now logs cooldowns via the ledger db (pass `--no-ledger` to opt out).
- Fix: `python -m modelwake` entry point (`__main__.py` was missing).
- Fix(ci): tests bootstrap `sys.path` like the depwake house pattern.

## [0.1.0] - 2026-09-16
- Initial release: tier chains, fallback routing, SQLite ledger, OpenAI-compatible urllib transport, stdlib only.
