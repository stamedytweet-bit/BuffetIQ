"""The prepared showcase morning and the presenter's clock (Phase 8).

The showcase morning is a fictional Tuesday 24 November at 82% occupancy, built
from the demo morning in the synthetic data: in-house guests, breakfast rooms,
check-ins, arrivals and demand are scaled to 82% occupancy, and an unannounced
tour group of 24 arrives at 07:45. The tour group is not in the night-before
features (no group booking), so only the nowcast can catch it. The chef's plan
for the "usual day" comparison stays the same-weekday average from the data,
because a chef planning the night before would not know about the group either.

The presenter's clock moves the service forward at 1x to 10x speed; simulated
guests arrive and a simulated runner checks every tray every 15 minutes, while
real taps, photos and questions are added on top.
"""

from __future__ import annotations

import threading
import time

import numpy as np
import pandas as pd

from buffetiq import data_gen, forecast, state

OCCUPANCY = 0.82
TOUR_GROUP = 24
TOUR_SLOT = "07:45"
SPEEDS = {"Paused": 0, "1x": 1, "2x": 2, "5x": 5, "10x": 10}


def showcase_row(date: str = state.DEFAULT_SERVICE_DATE) -> pd.DataFrame:
    """The demo morning scaled to 82% occupancy, with a tour group of 24 at 07:45 that nobody booked."""
    cfg = state.load_config()
    hist = forecast.load_history()
    row = hist[hist["date"] == date].copy()
    r = row.iloc[0]
    scale = OCCUPANCY / float(r["occupancy_rate"])
    rooms = int(round(cfg["hotel"]["rooms"] * OCCUPANCY))
    row["occupancy_rate"] = OCCUPANCY
    row["rooms_occupied"] = rooms
    for col in ("adults", "children", "breakfast_inclusive_rooms", "check_ins"):
        row[col] = int(round(float(r[col]) * scale))
    row["group_booking"] = 0
    row["group_size"] = 0
    arrivals = np.round(r[data_gen.ARRIVAL_COLUMNS].to_numpy(float) * scale).astype(int)
    slot = data_gen.ARRIVAL_COLUMNS.index("arr_" + TOUR_SLOT.replace(":", ""))
    arrivals[slot] += TOUR_GROUP
    for col, v in zip(data_gen.ARRIVAL_COLUMNS, arrivals):
        row[col] = int(v)
    row["diners"] = int(arrivals.sum())
    rates = cfg["simulation"]["dish_rates"]
    for d in cfg["dishes"]:
        c = data_gen.dish_columns(d)
        row[c["demand"]] = round(float(r[c["demand"]]) * scale + TOUR_GROUP * rates[d["id"]]["per_diner"], 2)
    row["surprise"] = "tour_group_early"
    return forecast.add_features(row.reset_index(drop=True))


def tour_minute() -> int:
    return state.minutes(TOUR_SLOT)


# ---------------------------------------------------------------------------
# The presenter's clock
# ---------------------------------------------------------------------------

class Clock:
    """Moves the shared service forward in the background at the chosen speed."""

    def __init__(self):
        self.speed = 0
        self._thread = None
        self._stop = threading.Event()

    def set_speed(self, speed: float) -> None:
        self.speed = speed
        if speed and (self._thread is None or not self._thread.is_alive()):
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self) -> None:
        last = time.time()
        while not self._stop.is_set():
            time.sleep(1.0)
            now = time.time()
            if self.speed:
                svc = state.service()
                end = state.minutes(svc.config["service"]["end"])
                target = svc.clock_minutes_exact() + self.speed * (now - last) / 60.0
                if target >= end:
                    target, self.speed = end, 0
                svc.advance_to(target)
            last = now

    def stop(self) -> None:
        self.speed = 0
        self._stop.set()


CLOCK = Clock()


# ---------------------------------------------------------------------------
# Start and Restart on the kitchen board
# ---------------------------------------------------------------------------

LIVE_START = "08:00"   # "Start breakfast" brings a morning that has not reached this time up to it


def running() -> bool:
    return bool(CLOCK.speed)


def can_start() -> bool:
    """True when the board should offer "Start breakfast": the clock is stopped before the end of service."""
    svc = state.service()
    return not running() and svc.clock_minutes() < state.minutes(svc.config["service"]["end"])


def start_breakfast(at: str = LIVE_START) -> None:
    """Bring the morning up to `at` (simulated guests and tray rounds included), then run the clock in real time."""
    svc = state.service()
    if svc.clock_minutes() < state.minutes(at):
        svc.advance_to(state.minutes(at))
    CLOCK.set_speed(1)


def restart_morning() -> None:
    """Stop the clock and go back to 06:15 of the same morning, with no arrivals, checks or calls."""
    CLOCK.set_speed(0)
    state.reset()
