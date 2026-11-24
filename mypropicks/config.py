"""Settings: the three portfolios, defaults, and config.yaml overrides."""
from __future__ import annotations

import copy
import os
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DISCLAIMER = (
    "Rules-based ranking for personal research. Not investment advice. "
    "No returns are guaranteed."
)

PORTFOLIOS: dict[str, dict] = {
    "nifty20": {
        "n": 20,
        "label": "Nifty 20",
        "index_file": "ind_nifty100list",
        "index_name": "Nifty 100",
    },
    "midcap30": {
        "n": 30,
        "label": "Nifty Midcap 30",
        "index_file": "ind_niftymidcap150list",
        "index_name": "Nifty Midcap 150",
    },
    "smallcap50": {
        "n": 50,
        "label": "Nifty Smallcap 50",
        "index_file": "ind_niftysmallcap250list",
        "index_name": "Nifty Smallcap 250",
    },
}

# Yahoo Finance tickers for each portfolio's comparison index (checked during the build).
BENCHMARKS: dict[str, str] = {
    "nifty20": "^CNX100",
    "midcap30": "NIFTYMIDCAP150.NS",
    "smallcap50": "NIFTYSMLCAP250.NS",
}

DEFAULTS: dict = {
    # Starting money per portfolio, in rupees. Set your own in config.yaml.
    "capital": {"nifty20": 0, "midcap30": 0, "smallcap50": 0},
    "weights": {
        "profitability": 0.20,
        "growth": 0.20,
        "cash_flow": 0.15,
        "relative_value": 0.20,
        "momentum": 0.25,
    },
    # Minimum median daily traded value over 3 months, in crore rupees.
    "liquidity_cr": {"nifty20": 50, "midcap30": 10, "smallcap50": 2},
    "eligibility": {"min_history_days": 250, "traded_days_window": 126},
    "fair_value": {
        "band": 0.10,
        "dcf_years": 5,
        "dcf_discount": 0.12,
        "dcf_terminal": 0.05,
        "dcf_growth_min": 0.0,
        "dcf_growth_max": 0.25,
        "outlier_ratio": 3.0,
    },
    "low_data_threshold": 0.60,
}


def data_dir() -> Path:
    env = os.environ.get("MYPROPICKS_DATA_DIR")
    return Path(env) if env else PROJECT_ROOT / "data"


def config_path() -> Path:
    env = os.environ.get("MYPROPICKS_CONFIG")
    return Path(env) if env else PROJECT_ROOT / "config.yaml"


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | Path | None = None) -> dict:
    p = Path(path) if path else config_path()
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return _merge(DEFAULTS, yaml.safe_load(f) or {})
    return copy.deepcopy(DEFAULTS)


def save_capital(capital: dict[str, float], path: str | Path | None = None) -> None:
    """Update only the capital section of config.yaml, keeping everything else."""
    p = Path(path) if path else config_path()
    current = {}
    if p.exists():
        with open(p, encoding="utf-8") as f:
            current = yaml.safe_load(f) or {}
    current.setdefault("capital", {}).update({k: float(v) for k, v in capital.items()})
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(current, f, sort_keys=False)
    from . import remote  # late import: remote imports this module
    if remote.enabled():
        remote.push(p, "settings: update capital")
