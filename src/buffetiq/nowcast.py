"""Nowcast and refill engine (Phase 5): the heart of BuffetIQ.

A nowcast is a forecast revised with what has already happened this morning:

    N(t) = w(t) x A(t) / F(t) + (1 - w(t)) x N0,  with w(t) = F(t)

where A(t) is the diners logged so far, F(t) the forecast share of the morning's
arrivals by time t, and N0 the night-before forecast. Below F(t) = 0.05 the
night-before forecast is kept.

For each dish the remaining need is

    R_d(t) = max(0, (1 + b) x (N(t) - A(t)) x c_d - S_d(t) - P_d(t))

with c_d the expected amount per remaining diner, b the safety buffer, S_d the
stock on the buffet and P_d any batch already cooking. R_d says whether more
food is needed this morning at all; the timing rule below says whether to cook
it now (see docs/ASSUMPTIONS.md, Phase 5):

* if R_d is 0, hold: there is enough for the rest of service;
* if a batch could not be ready before the dish's last-cook time, let it run down;
* if stock plus cooking will not last until a new batch is ready plus one check
  interval, cook now, enough to cover demand until ready plus `cover_minutes`,
  at least one batch, never more than R_d, rounded up to whole batches;
* otherwise hold until the next check.

The `Engine` class keeps one morning's kitchen state (arrivals, stock estimates,
batches, pan timers, overrides and alerts). The live kitchen board and the
65-day replay both use it, so the replay tests exactly what the board does.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

SERVICE_START = 6 * 60 + 30
SLOT = 15
N_SLOTS = 16
SERVICE_END = SERVICE_START + SLOT * N_SLOTS
PAN_WARN, PAN_LIMIT = 210, 240


def hhmm(minute: float) -> str:
    m = int(round(minute))
    return f"{m // 60:02d}:{m % 60:02d}"


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def cumulative_share(shares, minute: float) -> float:
    """F(t): forecast share of the morning's arrivals by `minute`, linear within each slot."""
    shares = np.asarray(shares, float)
    shares = shares / shares.sum()
    x = (minute - SERVICE_START) / SLOT
    if x <= 0:
        return 0.0
    if x >= N_SLOTS:
        return 1.0
    i = int(x)
    return float(shares[:i].sum() + shares[i] * (x - i))


def nowcast(arrived: float, f: float, n0: float, min_share: float = 0.05) -> float:
    """N(t) = w x A/F + (1 - w) x N0 with w = F; keeps N0 while F < min_share. Never below A."""
    if f < min_share:
        return max(n0, arrived)
    w = f
    n = w * arrived / f + (1 - w) * n0
    return max(n, arrived)


def remaining_between(n: float, arrived: float, shares, t0: float, t1: float, now: float | None = None) -> float:
    """Expected arrivals between t0 and t1: the N - A guests still to come after `now` (t0 by default),
    spread along the rest of the forecast curve."""
    now = t0 if now is None else now
    f_now = cumulative_share(shares, now)
    f0, f1 = cumulative_share(shares, max(t0, now)), cumulative_share(shares, min(t1, SERVICE_END))
    if f_now >= 1:
        return 0.0
    return max(n - arrived, 0.0) * max(f1 - f0, 0.0) / (1 - f_now)


def round_up(x: float, step: float) -> float:
    if x <= 0:
        return 0.0
    return math.ceil(round(x / step, 9)) * step


def remaining_need(n, arrived, rate, stock, cooking, buffer, batch) -> float:
    """R_d(t), rounded up to whole batches."""
    raw = max(0.0, (1 + buffer) * max(n - arrived, 0.0) * rate - stock - cooking)
    return round_up(raw, batch)


@dataclass
class Call:
    action: str          # "cook", "hold", "run_down", "cook_to_order"
    amount: float = 0.0
    line: str = ""


def refill_call(*, now: float, n: float, arrived: float, shares, rate: float, stock: float, cooking: float,
                buffer: float, batch: float, lead: float, last_cook: float, check: float, cover: float) -> Call:
    """The cook or hold decision for one dish (see the module docstring)."""
    need = remaining_need(n, arrived, rate, stock, cooking, buffer, batch)
    if need <= 0:
        return Call("hold", 0.0, f"Next check {hhmm(now + check)}")
    if now + lead > last_cook:
        return Call("run_down", 0.0, f"Last cook was {hhmm(last_cook)}")
    soon = (1 + buffer) * rate * remaining_between(n, arrived, shares, now, now + lead + check)
    if stock + cooking > soon and stock > 0:
        return Call("hold", 0.0, f"Next check {hhmm(now + check)}")
    cover_need = (1 + buffer) * rate * remaining_between(n, arrived, shares, now, now + lead + cover)
    amount = round_up(max(cover_need - stock - cooking, batch), batch)
    return Call("cook", min(amount, need), "")


def pan_status(out_at: float | None, now: float) -> tuple[str, str]:
    """('ok' | 'warn' | 'limit', footer text) for the 4-hour hot-holding rule."""
    if out_at is None:
        return "ok", "Next batch starts the timer"
    held = now - out_at
    swap = hhmm(out_at + PAN_LIMIT)
    if held >= PAN_LIMIT:
        return "limit", f"Out since {hhmm(out_at)} · Swap now"
    if held >= PAN_WARN:
        return "warn", f"Out since {hhmm(out_at)} · swap by {swap}"
    return "ok", f"Out since {hhmm(out_at)} · swap by {swap}"


def per_slot_rate(n, arrived, shares, now) -> list[tuple[float, float]]:
    """(slot start, expected arrivals) for each remaining 15-minute slot."""
    out = []
    t = max(now, SERVICE_START)
    start = SERVICE_START + SLOT * math.floor((t - SERVICE_START) / SLOT) if t < SERVICE_END else SERVICE_END
    while start < SERVICE_END:
        out.append((start, remaining_between(n, arrived, shares, start, start + SLOT, now=now)))
        start += SLOT
    return out


def cook_to_order_from(n, arrived, shares, now, threshold) -> float | None:
    """The first slot from which fewer than `threshold` guests per 15 minutes are expected for the rest of service."""
    slots = per_slot_rate(n, arrived, shares, now)
    for i, (start, _) in enumerate(slots):
        if all(v < threshold for _, v in slots[i:]) and start >= SERVICE_START + 60:
            return start
    return None


# ---------------------------------------------------------------------------
# The kitchen engine
# ---------------------------------------------------------------------------

@dataclass
class Batch:
    dish: str
    amount: float
    start: float
    ready: float
    source: str = "call"   # "call" (a followed BuffetIQ call), "override" or "reactive"


@dataclass
class Override:
    action: str
    reason: str
    at: float
    until: float


@dataclass
class EngineAlert:
    kind: str      # "stop", "info" or "suggest"
    title: str
    line: str
    at: float
    key: str = ""  # stops the same alert repeating


@dataclass
class Engine:
    """One morning's kitchen: what BuffetIQ believes and what it calls for."""
    dishes: list
    rules: dict
    n0: float
    shares: list
    rates: dict                          # expected amount per diner, by dish id
    arrivals: np.ndarray = field(default_factory=lambda: np.zeros(N_SLOTS))
    stock: dict = field(default_factory=dict)          # estimated amount on the buffet, by dish id
    out_at: dict = field(default_factory=dict)         # when the food on the buffet went out
    empty_since: dict = field(default_factory=dict)
    batches: list = field(default_factory=list)        # cooking now
    served_out: list = field(default_factory=list)     # every batch that reached the buffet
    overrides: dict = field(default_factory=dict)
    to_order: bool = False
    to_order_from: float | None = None
    alerts: list = field(default_factory=list)
    calls: dict = field(default_factory=dict)
    last_announced: float | None = None
    now: float = SERVICE_START
    started: bool = False
    log: list = field(default_factory=list)            # (minute, action, dish, amount, note)

    # ---- set-up ----
    def open_service(self) -> None:
        """At 06:30 one full pan of each dish is out, cooked before service."""
        for d in self.dishes:
            self.stock[d["id"]] = float(d["pan_capacity"])
            self.out_at[d["id"]] = SERVICE_START
        self.started = True
        self.last_announced = self.n0

    # ---- what has happened ----
    def arrived(self) -> float:
        return float(self.arrivals.sum())

    def f(self, now: float | None = None) -> float:
        return cumulative_share(self.shares, self.now if now is None else now)

    def n(self) -> float:
        return nowcast(self.arrived(), self.f(), self.n0, self.rules["min_forecast_share"])

    def log_arrivals(self, count: int, now: float) -> None:
        """Host taps "Log arrivals": diners counted in the current slot, eating as they arrive."""
        i = min(max(int((now - SERVICE_START) // SLOT), 0), N_SLOTS - 1)
        self.arrivals[i] += count
        for d in self.dishes:
            if d["id"] in self.stock:
                self.stock[d["id"]] = max(0.0, self.stock[d["id"]] - count * self.rates[d["id"]])
                if self.stock[d["id"]] <= 0 and d["id"] not in self.empty_since:
                    self.empty_since[d["id"]] = now
        self.log.append((now, "arrivals", "", count, ""))

    def tray_check(self, dish_id: str, amount: float, level: str, now: float) -> None:
        """A camera or manual reading updates the pan on the buffet only.

        The camera cannot see food held hot in the kitchen, so the reserve BuffetIQ
        believes it has (anything above one pan) is kept and added to the reading.
        A Full reading also cannot tell how full above the pan's top it is.
        """
        dish = self._dish(dish_id)
        cap = float(dish["pan_capacity"])
        reserve = max(self.stock.get(dish_id, 0.0) - cap, 0.0)
        # An Empty pan means any reserve has run out or not been brought out, so the dish needs food now.
        # The camera is at most one level off, so a full pan is never read as Empty.
        est = 0.0 if level == "empty" else amount + reserve
        if level == "full":
            est = max(self.stock.get(dish_id, 0.0), est)
        self.stock[dish_id] = est
        if est <= 0:
            self.empty_since.setdefault(dish_id, now)
        else:
            self.empty_since.pop(dish_id, None)
        self.log.append((now, "tray_check", dish_id, amount, level))

    def override(self, dish_id: str, action: str, reason: str, now: float) -> None:
        """A chef's override stands for `override_minutes`. Discard empties the pan and logs it as waste."""
        self.overrides[dish_id] = Override(action, reason, now, now + self.rules["override_minutes"])
        self.log.append((now, "override", dish_id, 0.0, f"{action}: {reason}"))
        if action == "discard":
            wasted = self.stock.get(dish_id, 0.0)
            self.log.append((now, "discard", dish_id, wasted, reason))
            self.stock[dish_id] = 0.0
            self.out_at[dish_id] = None
            self.empty_since[dish_id] = now
            del self.overrides[dish_id]
        elif action == "cook":
            self._start(self._dish(dish_id), float(self._dish(dish_id)["batch"]), now, "override")

    # ---- moving time ----
    def step(self, now: float) -> None:
        """Bring batches out, refresh the nowcast and make every call for `now`."""
        self.now = now
        if not self.started and now >= SERVICE_START:
            self.open_service()
        if not self.started:
            return
        for b in [b for b in self.batches if b.ready <= now]:
            self.batches.remove(b)
            self.stock[b.dish] = self.stock.get(b.dish, 0.0) + b.amount
            self.out_at[b.dish] = b.ready
            self.empty_since.pop(b.dish, None)
            self.served_out.append(b)
            self.log.append((b.ready, "batch_out", b.dish, b.amount, b.source))
        for k in [k for k, o in self.overrides.items() if o.until <= now]:
            del self.overrides[k]
        self._forecast_alerts(now)
        for d in self.dishes:
            self.calls[d["id"]] = self._decide(d, now)
        self._stock_alerts(now)

    # ---- decisions ----
    def cooking(self, dish_id: str) -> float:
        return sum(b.amount for b in self.batches if b.dish == dish_id)

    def _decide(self, dish: dict, now: float) -> Call:
        did = dish["id"]
        o = self.overrides.get(did)
        if o is not None and o.action != "cook":
            return Call(o.action, 0.0, f"Chef override · {o.reason}")
        if self.to_order and dish.get("hot") and not self.batches_for(did):
            return Call("cook_to_order", 0.0, "Small portions as guests ask")
        if not self.batches_for(did):
            r = self.rules
            call = refill_call(now=now, n=self.n(), arrived=self.arrived(), shares=self.shares,
                               rate=self.rates[did], stock=self.stock.get(did, 0.0), cooking=0.0,
                               buffer=r["safety_buffer"], batch=float(dish["batch"]),
                               lead=float(dish["lead_minutes"]), last_cook=_minutes(dish["last_cook"]),
                               check=r["check_minutes"], cover=r["cover_minutes"])
            if call.action != "cook":
                return call
            self._start(dish, call.amount, now, "call")          # calls are assumed to be followed
        return self._cooking_call(dish, now)

    def batches_for(self, dish_id: str) -> list:
        return [b for b in self.batches if b.dish == dish_id]

    def _cooking_call(self, dish: dict, now: float) -> Call:
        """While a batch cooks, the card keeps the call with when it will be ready."""
        did = dish["id"]
        bs = self.batches_for(did)
        amount = sum(b.amount for b in bs)
        ready = min(b.ready for b in bs)
        if did in self.empty_since:
            line = f"Now · tray empty since {hhmm(self.empty_since[did])}"
        elif dish["unit"] == "pieces":
            line = f"Now · last bake {dish['last_cook']}"
        else:
            line = f"Now · ready in {max(1, math.ceil(ready - now))} min"
        if any(b.source == "override" for b in bs):
            line = "Chef override · " + line
        return Call("cook", amount, line)

    def _start(self, dish: dict, amount: float, now: float, source: str) -> None:
        b = Batch(dish["id"], amount, now, now + float(dish["lead_minutes"]), source)
        self.batches.append(b)
        self.log.append((now, "cook", dish["id"], amount, source))

    def _forecast_alerts(self, now: float) -> None:
        n = self.n()
        jump = self.rules["forecast_jump_alert"]
        if self.last_announced and abs(n - self.last_announced) >= jump * self.last_announced:
            word = "raised" if n > self.last_announced else "lowered"
            title = "More guests than forecast" if n > self.last_announced else "Fewer guests than forecast"
            self._alert("info", title, f"Expected diners {word} from {round(self.last_announced)} to {round(n)}.",
                        now, f"jump-{round(n)}")
            self.last_announced = n
        start = cook_to_order_from(n, self.arrived(), self.shares, now, self.rules["cook_to_order_threshold"])
        self.to_order_from = start
        if start is not None and now >= start:
            if not self.to_order:
                self.to_order = True
                self.log.append((now, "cook_to_order", "", 0.0, ""))
        elif start is not None and start - now <= 90:
            self._alert("suggest", f"Switch to cook-to-order from about {hhmm(start)}",
                        f"Under {self.rules['cook_to_order_threshold']} guests per 15 minutes expected, so use smaller pans.",
                        now, "to-order")

    def _stock_alerts(self, now: float) -> None:
        for d in self.dishes:
            did = d["id"]
            if did in self.empty_since and not self.to_order:
                at = self.empty_since[did]
                c = self.calls.get(did)
                todo = f"Cook {_amount(d, self.cooking(did) or float(d['batch']))} now." if c else ""
                self._alert("stop", f"{d['name']} ran out at {hhmm(at)}", todo, now, f"empty-{did}-{round(at)}")
            status, _ = pan_status(self.out_at.get(did), now)
            if status == "limit" and self.stock.get(did, 0) > 0:
                self._alert("stop", f"{d['name']} pan at 4 hours", "Swap now and log the old pan as discarded.",
                            now, f"pan-{did}-{self.out_at.get(did)}")
        if now >= SERVICE_END - 60:
            for d in self.dishes:
                surplus = self.surplus(d, now)
                if surplus > 1.0:
                    self._alert("suggest", f"Offer {d['name'].lower()} on Treatsure",
                                f"About {surplus:.1f} kg is likely to be left at close.", now, f"treat-{d['id']}")

    def surplus(self, dish: dict, now: float) -> float:
        """Predicted kilograms left at close: stock plus cooking minus expected remaining demand."""
        did = dish["id"]
        left = self.stock.get(did, 0.0) + self.cooking(did) - self.rates[did] * max(self.n() - self.arrived(), 0.0)
        kg = left * float(dish.get("piece_kg", 1.0)) if dish["unit"] == "pieces" else left
        return max(kg, 0.0)

    def _alert(self, kind, title, line, now, key) -> None:
        if any(a.key == key for a in self.alerts):
            return
        self.alerts.insert(0, EngineAlert(kind, title, line, now, key))

    def _dish(self, dish_id: str) -> dict:
        return next(d for d in self.dishes if d["id"] == dish_id)


def _minutes(hhmm_text: str) -> float:
    h, m = hhmm_text.split(":")
    return int(h) * 60 + int(m)


def _amount(dish: dict, amount: float) -> str:
    if dish["unit"] == "pieces":
        return f"{int(round(amount))}"
    return f"{amount:g} kg"


def action_text(dish: dict, call: Call) -> str:
    """'Cook 4 kg', 'Bake 24', 'Hold', 'Let it run down' or 'Cook to order'."""
    if call.action == "cook":
        verb = "Bake" if dish["unit"] == "pieces" else "Cook"
        return f"{verb} {_amount(dish, call.amount)}"
    return {"hold": "Hold", "run_down": "Let it run down", "cook_to_order": "Cook to order"}[call.action]
