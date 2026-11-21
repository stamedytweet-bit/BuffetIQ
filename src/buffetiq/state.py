"""Shared state for all pages, guarded by one lock.

Every page reads the same service (one breakfast morning) through this module,
so the kitchen board, the runner phone, the guest page and Ask BuffetIQ always
show the same numbers. Phase 3 adds the service date, the service clock, guest
plans from the guest page and the live forecast they feed. Later phases add
arrivals, tray levels, batches and alerts.

Privacy: room numbers stay on this laptop. They are kept only to let a guest
change their own plan, are written only to data/guest_checkins.csv (ignored by
git), are never logged or sent to any external service, and are deleted when
the service date moves on (the simulated checkout) or on reset.
"""

from __future__ import annotations

import csv
import math
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.yaml"
CHECKINS_PATH = ROOT / "data" / "guest_checkins.csv"
DEFAULT_SERVICE_DATE = "2026-11-24"      # the demo morning on the design screens
DEFAULT_CLOCK = "06:15"                  # before service, when the showcase demo starts

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


# ---------------------------------------------------------------------------
# Times and labels
# ---------------------------------------------------------------------------

def minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def hhmm(total_minutes: int) -> str:
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def service_slots() -> list[str]:
    """Start times of the sixteen 15-minute slots, '06:30' to '10:15'."""
    s = load_config()["service"]
    step = s["slot_minutes"]
    return [hhmm(t) for t in range(minutes(s["start"]), minutes(s["end"]), step)]


def half_hours() -> list[str]:
    """Start times of the half hours a guest can choose, '06:30' to '10:00'."""
    s = load_config()["service"]
    step = s["guest_slot_minutes"]
    return [hhmm(t) for t in range(minutes(s["start"]), minutes(s["end"]), step)]


def long_date(date: str) -> str:
    """'2026-11-24' to 'Tuesday 24 November'."""
    d = datetime.strptime(date, "%Y-%m-%d")
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B')}"


def crowd_word(value: float, busiest: float) -> str:
    """Quiet below 40% of the busiest half hour, Moderate from 40% to 75%, Busy above 75%."""
    if busiest <= 0:
        return "Quiet"
    share = value / busiest
    if share < 0.40:
        return "Quiet"
    if share <= 0.75:
        return "Moderate"
    return "Busy"


# ---------------------------------------------------------------------------
# Guest plans
# ---------------------------------------------------------------------------

@dataclass
class GuestPlan:
    service_date: str
    room: str
    attending: bool
    party: int
    halal: int = 0
    vegetarian: int = 0
    slot: str | None = None          # half hour such as "09:30"; None when not attending
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


def valid_room(room: str) -> bool:
    """Room numbers are 3 to 5 digits, such as 1204."""
    room = (room or "").strip()
    return room.isdigit() and 3 <= len(room) <= 5


def clean_plan(plan: GuestPlan) -> GuestPlan:
    """Clamp counts: party 1 to 8, meal counts 0 to the party size."""
    party = max(1, min(8, int(plan.party)))
    plan.party = party
    plan.halal = max(0, min(party, int(plan.halal)))
    plan.vegetarian = max(0, min(party, int(plan.vegetarian)))
    if not plan.attending:
        plan.slot = None
    elif plan.slot not in half_hours():
        raise ValueError(f"Unknown half hour {plan.slot!r}")
    return plan


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------

class Service:
    """One breakfast morning: its forecast, its clock and what guests have told us."""

    def __init__(self, service_date: str = DEFAULT_SERVICE_DATE, clock: str = DEFAULT_CLOCK,
                 checkins_path: Path = CHECKINS_PATH, model=None):
        from buffetiq import forecast

        self.config = load_config()
        self.service_date = service_date
        self.clock = datetime.strptime(f"{service_date} {clock}", "%Y-%m-%d %H:%M")
        self.checkins_path = Path(checkins_path)
        history = forecast.load_history()
        rows = history[history["date"] == service_date]
        if rows.empty:
            raise ValueError(f"No booking data for {service_date}")
        self.row = rows.copy()
        # trained only on days before the service, so the forecast never sees the morning itself
        self.model = model or forecast.Forecaster(self.config).fit(history[history["date"] < service_date], tune=False)
        self.base_check_ins = int(self.row["check_ins"].iloc[0])
        in_house = int(self.row["adults"].iloc[0] + self.row["children"].iloc[0])
        self.n0 = float(self.model.predict_diners(self.row)[0])
        self.profile = self.model.predict_curve(self.row)[0]
        self.p_dine = min(1.0, self.n0 / max(in_house, 1))   # chance an in-house guest eats breakfast
        self.plans: dict[str, GuestPlan] = {}
        self._load_plans()

    # ---- persistence (local file only) ----
    def _load_plans(self) -> None:
        if not self.checkins_path.exists():
            return
        kept = []
        with open(self.checkins_path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["service_date"] < self.service_date:
                    continue                      # guests have checked out: their rows are deleted
                kept.append(r)
                if r["service_date"] == self.service_date:
                    self.plans[r["room"]] = GuestPlan(
                        service_date=r["service_date"], room=r["room"], attending=r["attending"] == "True",
                        party=int(r["party"]), halal=int(r["halal"]), vegetarian=int(r["vegetarian"]),
                        slot=r["slot"] or None, updated_at=r["updated_at"])
        self._save()

    def _save(self) -> None:
        self.checkins_path.parent.mkdir(parents=True, exist_ok=True)
        names = list(GuestPlan.__dataclass_fields__)
        with open(self.checkins_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=names)
            w.writeheader()
            for p in self.plans.values():
                row = asdict(p)
                row["slot"] = row["slot"] or ""
                w.writerow(row)

    # ---- guest plans ----
    def save_plan(self, plan: GuestPlan) -> GuestPlan:
        if not valid_room(plan.room):
            raise ValueError("Room numbers are 3 to 5 digits")
        plan.room = plan.room.strip()
        plan.service_date = self.service_date
        plan = clean_plan(plan)
        with LOCK:
            self.plans[plan.room] = plan          # "Change my plans" replaces the room's earlier plan
            self._save()
        return plan

    def clear_plans(self) -> None:
        with LOCK:
            self.plans.clear()
            self._save()

    def confirmed_guests(self) -> int:
        return sum(p.party for p in self.plans.values() if p.attending)

    def declined_guests(self) -> int:
        return sum(p.party for p in self.plans.values() if not p.attending)

    def dietary_counts(self) -> dict:
        """Counts only, never names or rooms."""
        attending = [p for p in self.plans.values() if p.attending]
        return {"halal": sum(p.halal for p in attending), "vegetarian": sum(p.vegetarian for p in attending)}

    # ---- forecast ----
    def expected_diners(self) -> float:
        """Rerun the diner model with the new check-in count, then remove guests who said no.

        Live confirmations add to the check-ins the hotel already had for this
        morning. A decline removes the chance that guest would have eaten.
        """
        with LOCK:
            row = self.row.copy()
            row["check_ins"] = self.base_check_ins + self.confirmed_guests()
            n = float(self.model.predict_diners(row)[0])
            n -= self.declined_guests() * self.p_dine
            return max(n, float(self.confirmed_guests()))

    def expected_slots(self) -> np.ndarray:
        """Expected diners per 15-minute slot: confirmed guests in their chosen half hour,
        everyone else spread by the forecast arrival curve."""
        with LOCK:
            n = self.expected_diners()
            placed = np.zeros(len(service_slots()))
            slots = service_slots()
            for p in self.plans.values():
                if p.attending and p.slot:
                    i = slots.index(p.slot)
                    placed[i] += math.ceil(p.party / 2)
                    placed[i + 1] += p.party // 2
            free = max(n - placed.sum(), 0.0)
            return self.profile * free + placed

    def crowd_view(self) -> list[dict]:
        """One row per half hour for the guest page, with the word always beside the bar."""
        per_slot = self.expected_slots()
        totals = [per_slot[i] + per_slot[i + 1] for i in range(0, len(per_slot), 2)]
        busiest = max(totals)
        now = self.clock_minutes()
        same_day = self.is_service_day()
        view = []
        for start, value in zip(half_hours(), totals):
            view.append({
                "time": start,
                "expected": float(value),
                "word": crowd_word(value, busiest),
                "bar_pct": max(6, round(100 * value / busiest)) if busiest else 6,
                # on the morning itself, half hours that have already ended cannot be chosen
                "available": not same_day or minutes(start) + 30 > now,
            })
        return view

    # ---- clock ----
    def clock_minutes(self) -> int:
        return self.clock.hour * 60 + self.clock.minute

    def is_service_day(self) -> bool:
        return self.clock.strftime("%Y-%m-%d") == self.service_date

    def set_clock(self, when: datetime) -> None:
        with LOCK:
            self.clock = when

    def breakfast_heading(self) -> str:
        """'Breakfast tomorrow' the day before, 'Breakfast this morning' on the day."""
        if self.clock.date() < datetime.strptime(self.service_date, "%Y-%m-%d").date():
            return "Breakfast tomorrow"
        return "Breakfast this morning"

    def bookings_phrase(self) -> str:
        return "tomorrow's bookings" if self.breakfast_heading() == "Breakfast tomorrow" else "this morning's bookings"

    def current_slot_index(self) -> int | None:
        """Index of the 15-minute slot the clock is in, or None outside service hours."""
        s = self.config["service"]
        t = self.clock_minutes()
        if not self.is_service_day() or not (minutes(s["start"]) <= t < minutes(s["end"])):
            return None
        return (t - minutes(s["start"])) // s["slot_minutes"]

    def next_15(self) -> tuple[str, int]:
        """The word and expected count for the next 15 minutes (the first slot before service)."""
        per_slot = self.expected_slots()
        i = self.current_slot_index()
        if i is None:
            i = 0 if self.clock_minutes() < minutes(self.config["service"]["start"]) else len(per_slot) - 1
        value = per_slot[i]
        word = crowd_word(value, per_slot.max())
        return word, int(round(value))


_SERVICE: Service | None = None


def service() -> Service:
    """The one shared service, created on first use (training takes a few seconds)."""
    global _SERVICE
    with LOCK:
        if _SERVICE is None:
            _SERVICE = Service()
        return _SERVICE


def reset_service(**kwargs) -> Service:
    global _SERVICE
    with LOCK:
        _SERVICE = Service(**kwargs)
        return _SERVICE
