"""Eval harness: does the cheap model actually pass YOUR checks?

A suite is JSONL, one case per line:
  {"name": "capitals", "prompt": "...", "tier": "FREE", "contains": "Paris"}
  {"name": "json-only", "prompt": "...", "tier": "SIMPLE", "regex": "^\\\\{"}

Grading is substring/regex on the routed text — no judge model, no vibes.
Only models that pass your evals should join your chains; this file is how
you prove the free tier is good enough (and notice the day it isn't).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Case:
    name: str
    prompt: str
    tier: str = "FREE"
    contains: str = ""
    regex: str = ""

    def check_desc(self) -> str:
        if self.contains:
            return f"contains {self.contains!r}"
        return f"matches /{self.regex}/"


@dataclass
class Verdict:
    name: str
    passed: bool
    detail: str
    model_key: str = ""
    cost_usd: float = 0.0
    tier: str = ""


@dataclass
class Report:
    verdicts: list[Verdict] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for v in self.verdicts if v.passed)

    @property
    def total(self) -> int:
        return len(self.verdicts)

    @property
    def cost(self) -> float:
        return sum(v.cost_usd for v in self.verdicts)


def load_suite(path: str | Path) -> list[Case]:
    cases: list[Case] = []
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"suite {path}:{i}: bad JSON: {e}") from e
        name = str(d.get("name", f"case-{i}"))
        prompt = d.get("prompt", "")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"suite {path}:{i} ({name}): prompt required")
        contains = str(d.get("contains", ""))
        regex = str(d.get("regex", ""))
        if not contains and not regex:
            raise ValueError(f"suite {path}:{i} ({name}): need contains or regex")
        if regex:
            try:
                re.compile(regex)
            except re.error as e:
                raise ValueError(f"suite {path}:{i} ({name}): bad regex: {e}") from e
        cases.append(Case(name=name, prompt=prompt,
                          tier=str(d.get("tier", "FREE")), contains=contains,
                          regex=regex))
    if not cases:
        raise ValueError(f"suite {path}: no cases")
    return cases


def grade(case: Case, output: str) -> tuple[bool, str]:
    if case.contains:
        ok = case.contains.lower() in output.lower()
        return ok, ("found" if ok else "missing") + f" {case.contains!r}"
    m = re.search(case.regex, output, re.DOTALL)
    return (m is not None,
            ("matched" if m else "no match") + f" /{case.regex}/")
