"""Config loading. TOML only (stdlib tomllib). No network, no defaults that spend money."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Model:
    key: str
    base_url: str
    api_key_env: str
    model: str
    price_in_per_1k: float = 0.0
    price_out_per_1k: float = 0.0


@dataclass
class Config:
    models: dict[str, Model] = field(default_factory=dict)
    tiers: dict[str, list[str]] = field(default_factory=dict)


def load(path: str | Path) -> Config:
    p = Path(path)
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    models: dict[str, Model] = {}
    for key, m in (data.get("model") or {}).items():
        models[key] = Model(
            key=key,
            base_url=str(m.get("base_url", "")).rstrip("/"),
            api_key_env=str(m.get("api_key_env", "")),
            model=str(m.get("model", "")),
            price_in_per_1k=float(m.get("price_in_per_1k", 0.0)),
            price_out_per_1k=float(m.get("price_out_per_1k", 0.0)),
        )
    tiers: dict[str, list[str]] = {}
    for tier, chain in (data.get("tier") or {}).items():
        if isinstance(chain, dict):
            chain = chain.get("chain", [])
        tiers[str(tier).upper()] = [str(x) for x in (chain or [])]
    cfg = Config(models=models, tiers=tiers)
    _validate(cfg)
    return cfg


def _validate(cfg: Config) -> None:
    if not cfg.models:
        raise ValueError("config: no [model.<name>] entries")
    if not cfg.tiers:
        raise ValueError("config: no [tier.<NAME>] chains")
    for tier, chain in cfg.tiers.items():
        if not chain:
            raise ValueError(f"config: tier {tier} has empty chain")
        for key in chain:
            if key not in cfg.models:
                raise ValueError(f"config: tier {tier} references unknown model {key!r}")
    for key, m in cfg.models.items():
        if not m.base_url or not m.model:
            raise ValueError(f"config: model {key!r} needs base_url + model")


def api_key_for(model: Model) -> str:
    if not model.api_key_env:
        return ""
    return os.environ.get(model.api_key_env, "")
