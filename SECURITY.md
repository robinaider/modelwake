# Security policy

Modelwake routes prompts to LLM providers you configure. Your prompts **do**
leave the machine for the winning provider call — that is the product — so:
never send secrets to `:free` rows or any endpoint whose data-use terms you
haven't read (see `docs/FREE_MODELS.md`). API keys stay in environment
variables and are never logged; the SQLite ledger records token counts and
costs, never prompt text beyond character counts.

## Reporting a vulnerability

**Please do not open a public issue for security reports.** Disclose privately via
https://github.com/robinaider/modelwake/security/advisories/new
so we can fix before details go public.

Please include a minimal repro and the version (`modelwake --version`).
We aim to acknowledge within 72 hours and share a fix plan within 14 days,
and will credit reporters in `CHANGELOG.md` unless you ask otherwise.
We follow coordinated vulnerability disclosure: please allow up to 90 days
before public disclosure of the vulnerability.

## Supported versions

| Version | Supported |
|---|---|
| Latest PyPI release (`pip install -U modelwake`) | ✅ |
| Older releases | ⚠️ best-effort — please upgrade, re-test, and re-report |

## Scope notes

- `modelwake` never writes outside the ledger db you point it at.
- `--no-ledger` disables all local recording.
