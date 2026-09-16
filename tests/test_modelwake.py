"""Hermetic tests. No network — transport is always faked."""

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
import sys

sys.path.insert(0, str(SRC))

from modelwake import ledger as ledger_mod
from modelwake.config import load as load_config
from modelwake.router import auto_tier, cost_usd, pick_chain, route

CFG_TOML = """
[model.cheap]
base_url = "http://local/v1"
api_key_env = "MW_TEST_KEY"
model = "tiny"
price_in_per_1k = 0.1
price_out_per_1k = 0.2

[model.strong]
base_url = "http://local/v1"
api_key_env = "MW_TEST_KEY"
model = "big"
price_in_per_1k = 1.0
price_out_per_1k = 2.0

[tier.SIMPLE]
chain = ["cheap", "strong"]

[tier.COMPLEX]
chain = ["strong", "cheap"]
"""


def write_cfg(tmp: str) -> str:
    p = Path(tmp) / "mw.toml"
    p.write_text(CFG_TOML, encoding="utf-8")
    return str(p)


class TestConfig(unittest.TestCase):
    def test_load_and_chains(self):
        with tempfile.TemporaryDirectory() as t:
            cfg = load_config(write_cfg(t))
            self.assertEqual(pick_chain(cfg, "simple"), ["cheap", "strong"])
            self.assertEqual(pick_chain(cfg, "COMPLEX"), ["strong", "cheap"])

    def test_bad_reference_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "bad.toml"
            p.write_text('[model.a]\nbase_url="http://x"\nmodel="m"\n[tier.SIMPLE]\nchain=["nope"]\n')
            with self.assertRaises(ValueError):
                load_config(str(p))


class TestTiers(unittest.TestCase):
    def test_auto_tier_escalates(self):
        self.assertEqual(auto_tier("hi"), "SIMPLE")
        self.assertEqual(auto_tier("x" * 900), "MEDIUM")
        self.assertEqual(auto_tier("def f():\nimport os\n```\nTraceback error: x" * 40), "COMPLEX")


class TestRouter(unittest.TestCase):
    def test_first_success_wins(self):
        with tempfile.TemporaryDirectory() as t:
            cfg = load_config(write_cfg(t))

            def ok(base, key, model, prompt, timeout):
                return ("hello", 100, 50)

            res = route(cfg, "SIMPLE", "hi", ok)
            self.assertEqual(res.model_key, "cheap")
            self.assertAlmostEqual(res.cost_usd, 100 / 1000 * 0.1 + 50 / 1000 * 0.2)

    def test_fallback_on_failure(self):
        with tempfile.TemporaryDirectory() as t:
            cfg = load_config(write_cfg(t))
            calls = []

            def flaky(base, key, model, prompt, timeout):
                calls.append(model)
                if model == "tiny":
                    raise RuntimeError("429 rate limited")
                return ("recovered", 10, 5)

            res = route(cfg, "SIMPLE", "hi", flaky)
            self.assertEqual(res.model_key, "strong")
            self.assertEqual(calls, ["tiny", "big"])
            self.assertEqual(res.attempted, ["cheap", "strong"])

    def test_all_fail_raises(self):
        with tempfile.TemporaryDirectory() as t:
            cfg = load_config(write_cfg(t))

            def dead(*a):
                raise RuntimeError("down")

            with self.assertRaises(RuntimeError):
                route(cfg, "SIMPLE", "hi", dead)

    def test_cost_math(self):
        with tempfile.TemporaryDirectory() as t:
            cfg = load_config(write_cfg(t))
            self.assertAlmostEqual(cost_usd(cfg, "cheap", 1000, 1000), 0.3)


class TestLedger(unittest.TestCase):
    def test_log_and_summary(self):
        with tempfile.TemporaryDirectory() as t:
            db = str(Path(t) / "u.db")
            ledger_mod.log(db, model="cheap", tier="SIMPLE", prompt_chars=10,
                           in_tokens=100, out_tokens=50, cost_usd=0.02)
            ledger_mod.log(db, model="cheap", tier="SIMPLE", prompt_chars=10,
                           in_tokens=100, out_tokens=50, cost_usd=0.02)
            ledger_mod.log(db, model="strong", tier="COMPLEX", prompt_chars=10,
                           in_tokens=10, out_tokens=5, cost_usd=0.02)
            rows = {r["model"]: r for r in ledger_mod.summary(db)}
            self.assertEqual(rows["cheap"]["calls"], 2)
            self.assertEqual(rows["strong"]["calls"], 1)

    def test_missing_db_empty(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(ledger_mod.summary(str(Path(t) / "no.db")), [])
            self.assertEqual(ledger_mod.cooling_down(str(Path(t) / "no.db")), [])


class TestCooldown(unittest.TestCase):
    def test_set_and_list(self):
        with tempfile.TemporaryDirectory() as t:
            db = str(Path(t) / "u.db")
            ledger_mod.set_cooldown(db, "cheap", 3600)
            cooling = ledger_mod.cooling_down(db)
            self.assertEqual([c["model"] for c in cooling], ["cheap"])
            self.assertGreater(cooling[0]["retry_in"], 3500)

    def test_expired_gone(self):
        with tempfile.TemporaryDirectory() as t:
            db = str(Path(t) / "u.db")
            ledger_mod.set_cooldown(db, "cheap", 3600)
            ledger_mod.set_cooldown(db, "cheap", -1)
            self.assertEqual(ledger_mod.cooling_down(db), [])

    def test_rate_limit_parks_model(self):
        with tempfile.TemporaryDirectory() as t:
            db = str(Path(t) / "u.db")
            cfg = load_config(write_cfg(t))

            def limited(*a):
                raise RuntimeError("HTTP 429: too many requests")

            with self.assertRaises(RuntimeError):
                route(cfg, "SIMPLE", "hi", limited, db=db)
            self.assertEqual(
                {c["model"] for c in ledger_mod.cooling_down(db)},
                {"cheap", "strong"},
            )

    def test_cooled_models_go_last(self):
        with tempfile.TemporaryDirectory() as t:
            db = str(Path(t) / "u.db")
            cfg = load_config(write_cfg(t))
            ledger_mod.set_cooldown(db, "cheap", 3600)
            calls = []

            def ok(base, key, model, prompt, timeout):
                calls.append(model)
                return ("hi", 1, 1)

            res = route(cfg, "SIMPLE", "hi", ok, db=db)
            self.assertEqual(res.model_key, "strong")
            self.assertEqual(res.attempted, ["strong"])
            self.assertEqual(calls, ["big"])

    def test_all_cooling_says_retry(self):
        with tempfile.TemporaryDirectory() as t:
            db = str(Path(t) / "u.db")
            cfg = load_config(write_cfg(t))
            ledger_mod.set_cooldown(db, "cheap", 3600)
            ledger_mod.set_cooldown(db, "strong", 3600)

            def dead(*a):
                raise RuntimeError("down")

            with self.assertRaisesRegex(RuntimeError, "cooling down"):
                route(cfg, "SIMPLE", "hi", dead, db=db)


FREE_TOML = """
[model.local-small]
base_url = "http://localhost:9/v1"
api_key_env = ""
model = "tiny"
price_in_per_1k = 0.0
price_out_per_1k = 0.0

[model.or-free]
base_url = "https://openrouter.ai/api/v1"
api_key_env = "MW_TEST_FREE_KEY_MISSING"
model = "x:free"
price_in_per_1k = 0.0
price_out_per_1k = 0.0

[tier.FREE]
chain = ["local-small", "or-free"]
"""


class TestFreeCommand(unittest.TestCase):
    def test_reports_status_without_keys(self):
        import io
        from contextlib import redirect_stdout

        from modelwake.cli import main
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "free.toml"
            p.write_text(FREE_TOML, encoding="utf-8")
            db = str(Path(t) / "u.db")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(["free", "--config", str(p), "--db", db])
            out = buf.getvalue()
            self.assertEqual(rc, 1)  # nothing usable: port 9 refused, key missing
            self.assertIn("local-small", out)
            self.assertIn("or-free", out)
            self.assertIn("MW_TEST_FREE_KEY_MISSING", out)


if __name__ == "__main__":
    unittest.main()
