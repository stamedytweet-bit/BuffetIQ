"""Shared state for all pages, guarded by one lock.

Phase 0 only loads the configuration. Live state (arrivals, tray levels, batches,
alerts, check-ins and the service clock) arrives in later phases, and every page
will read it through functions here so that the board, the runner phone and
Ask BuffetIQ always show the same numbers.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.yaml"

LOCK = threading.RLock()


@lru_cache(maxsize=1)
def load_config(path: str | None = None) -> dict:
    """Read config.yaml once; dishes keep the order they have in the file."""
    with open(path or CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def dish_names() -> list[str]:
    return [d["name"] for d in load_config()["dishes"]]


def hotel() -> dict:
    return load_config()["hotel"]
