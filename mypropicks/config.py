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
        # How much each method counts in the (geometric) average. Checked against analysts'
        # targets on 500 NSE stocks: the stock's own past P/E and P/B were the most reliable,
        # sector multiples less so, and DCF on free data was far off, so it is left out.
        "weights": {"own_pe": 2, "own_pb": 2, "sector_pe": 1, "sector_pb": 1,
                    "sector_ev_ebitda": 1, "dcf": 0, "analyst_target": 2},
        # An analyst target counts fully only when at least this many analysts cover the stock.
        "analyst_min": 5,
    },
    "low_data_threshold": 0.60,
}


def data_dir() -> Path:
    env = os.environ.get("MYPROPICKS_DATA_DIR")
    return Path(env) if env else PROJECT_ROOT / "data"


def capital_path() -> Path:
    """Your capital is private, so it lives in its own file, kept out of the public repo."""
    return data_dir() / "capital.yaml"


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


def _read_yaml(p: Path) -> dict:
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(path: str | Path | None = None) -> dict:
    """Defaults, then config.yaml, then your private capital.yaml on top."""
    cfg = _merge(DEFAULTS, _read_yaml(Path(path) if path else config_path()))
    return _merge(cfg, {"capital": _read_yaml(capital_path())})


def save_capital(capital: dict[str, float]) -> None:
    """Save your capital to capital.yaml (and, in cloud mode, to the private data repo only)."""
    from . import remote  # late import: remote imports this module
    p = capital_path()
    repo = remote.data_repo() if remote.enabled() else None  # refuse before writing anything
    current = _read_yaml(p)
    current.update({k: float(v) for k, v in capital.items()})
    p.parent.mkdir(parents=True, exist_ok=True)
    before = p.read_bytes() if p.exists() else None
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(current, f, sort_keys=False)
    if repo:
        try:
            remote.push(p, "settings: update capital", repo=repo)
        except ValueError:
            if before is None:
                p.unlink()
            else:
                p.write_bytes(before)
            raise
