# Free models — the honest menu

> Limits change quarterly. Treat numbers as "verify today", links as stable.
> `modelwake free --config examples/free.toml` checks what *you* can use right now.

## The free stack (cheapest first)

| Source | What you get | Limits (approx, verify) | Key | Data note |
|---|---|---|---|---|
| Ollama (local) | Any open-weight model your hardware fits | Infinite; speed = your GPU | None | Private — nothing leaves the machine |
| OpenRouter `:free` rows | Rotating frontier open-weight (DeepSeek, Llama, MiMo, GLM…) | ~20 req/min, daily caps per model | Free key, no card | Free-row prompts may train models — don't send secrets |
| Gemini free tier | Flash + Lite with big context | Generous RPM/RPD per key | Google account | Google API terms (free ≠ paid terms) |
| Groq free tier | Very fast small-model inference | Strict RPM/TPD caps | Free account | Provider terms apply |
| GitHub Models | Playground + API for GH users | Low rate limits, non-production | GitHub login | Don't send secrets; evaluation use |

## vs the ad-funded free (Freebuff and friends)

| | Ad-funded agent (Freebuff) | modelwake free chain |
|---|---|---|
| Who pays inference | Them (ads pay providers) | Nobody — your hardware + free tiers |
| Setup | Zero-config | One free key + optional Ollama |
| Ads | Text ads between turns; prompts may personalize them | None, ever |
| Session/region limits | Yes (peak pauses, 2 sessions/day caps, limited-mode countries) | None imposed by us; provider 429s rotate automatically |
| Model choice | Their catalog, their rules | Any OpenAI-compatible endpoint |
| Privacy | Gateway sees everything; training-use notices | Direct provider path; local stays local |
| Proof of $0 | Trust us | `modelwake costs` → `$0.0000` |

Neither is "better" universally: ad-funded wins on zero-config breadth today.
modelwake wins the moment you care who sees prompts, or a peak-hour pause
kills your flow. Different free — pick with eyes open.

## Rules of the free road

1. Free tiers rate-limit. That's what the 60s cooldown rotation is for.
2. Never send secrets to `:free` rows or any training-notice endpoint.
3. Local first for drafts, hosted-free for brains, paid only when evals say so.
4. When a free row dies (they rotate monthly), swap one line in `free.toml`.
