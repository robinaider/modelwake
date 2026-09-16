# Modelwake ⏩

[![CI](https://github.com/robinaider/modelwake/actions/workflows/ci.yml/badge.svg)](https://github.com/robinaider/modelwake/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/robinaider/modelwake/badge)](https://scorecard.dev/viewer/?uri=github.com/robinaider/modelwake)

**Wake the right model — not the most expensive one.**

LiteLLM needs Postgres + Redis + Docker. OpenRouter takes 5.5% and your prompts leave your network. Modelwake is the small alternative: a stdlib-only, local-first router with tier chains, automatic fallback, and a one-file SQLite cost ledger.

```bash
pip install modelwake
modelwake tiers --config examples/modelwake.toml
modelwake route --config examples/modelwake.toml --tier auto --prompt "summarize this diff"
modelwake costs
```

- `SIMPLE → local-small → hosted-smart`, `COMPLEX → hosted-smart → local-small` — you own the chains
- First success wins; 429s / 5xx / timeouts fall through, full chain failure is an honest error
- Every call logged: model, tier, tokens, USD — `costs` shows cheapest-first spend
- Any OpenAI-compatible endpoint: Ollama, vLLM, OpenRouter, LiteLLM-behind — no SDKs, just urllib
- Stdlib only. No Postgres, no Redis, no markup.

Why not just LiteLLM/OpenRouter? Use those for breadth. Use modelwake when you want zero infra, data stays local except the winning call, and juniors can't accidentally spend $400 on opus for "hi".
