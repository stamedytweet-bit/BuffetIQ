"""Replay the 65 test mornings under three kitchen policies (Phase 5).

Each morning is replayed in 5-minute steps from 06:30 to 10:30. Guests arrive
as they did in the synthetic data and eat each dish in proportion to their
arrivals, up to the day's true demand. Every policy opens with one full pan of
each dish, cooked before service.

1. Baseline chef rule: the chef cooks the day's planned amount from the data
   (same-weekday average plus 15%) through the morning, following the usual
   arrival curve for that day type, and cooks one more batch whenever a tray is
   empty with nothing cooking.
2. Forecast only: as the chef, but the planned amount is the night-before
   forecast plus the 10% buffer, spread by the forecast arrival curve.
3. Full BuffetIQ: the nowcast and refill engine in nowcast.py, which sees only
   logged arrivals and camera tray readings every 15 minutes (four levels, 85%
   right, otherwise one level off), with cook-to-order and Treatsure flags.
   It is also run without the cook-to-order switch, and with 0% to 30% of guests
   in Busy half hours accepting a quieter one (a sensitivity test).

Food left on the buffet, held or still cooking at 10:30 counts as surplus.
Stock-out minutes count the time a dish's tray was empty while guests wanted it.
Every result is simulated on fictional data.

Run from the src folder:  python -m buffetiq.simulate
"""

from __future__ import annotations

import copy
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from buffetiq import data_gen, forecast
from buffetiq.camera import estimate
from buffetiq.nowcast import SERVICE_END, SERVICE_START, SLOT, Engine, round_up
from buffetiq.state import ROOT, load_config

RESULTS_PATH = ROOT / "docs" / "phase5_results.json"
CHARTS = ROOT / "docs" / "charts"
LEVEL_ORDER = ["empty", "low", "half", "full"]


def minutes(text: str) -> float:
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def kg(dish: dict, amount: float) -> float:
    return amount * float(dish.get("piece_kg", 1.0)) if dish["unit"] == "pieces" else amount


def true_level(stock: float, capacity: float) -> str:
    frac = min(stock, capacity) / capacity
    if frac <= 0.02:
        return "empty"
    if frac < 0.25:
        return "low"
    if frac <= 0.75:
        return "half"
    return "full"


def camera_reading(level: str, accuracy: float, rng: random.Random) -> str:
    """Right with probability `accuracy`, otherwise one level up or down."""
    if rng.random() < accuracy:
        return level
    i = LEVEL_ORDER.index(level)
    options = [j for j in (i - 1, i + 1) if 0 <= j < 4]
    return LEVEL_ORDER[rng.choice(options)]


def shift_arrivals(arrivals: np.ndarray, forecast_slots: np.ndarray, accept: float) -> np.ndarray:
    """Move `accept` of the guests in each Busy half hour to the nearest Quiet one (later wins a tie)."""
    if accept <= 0:
        return arrivals.astype(float)
    a = arrivals.astype(float).copy()
    halves = forecast_slots.reshape(8, 2).sum(axis=1)
    top = halves.max()
    word = ["Busy" if h > 0.75 * top else "Quiet" if h < 0.40 * top else "Moderate" for h in halves]
    quiet = [j for j, w in enumerate(word) if w == "Quiet"]
    if not quiet:
        return a
    for i, w in enumerate(word):
        if w != "Busy":
            continue
        j = min(quiet, key=lambda q: (abs(q - i), -q))
        for k in (2 * i, 2 * i + 1):
            moved = a[k] * accept
            a[k] -= moved
            a[2 * j] += moved / 2
            a[2 * j + 1] += moved / 2
    return a


@dataclass
class DayResult:
    prepared: dict = field(default_factory=dict)
    served: dict = field(default_factory=dict)
    left: dict = field(default_factory=dict)
    empty_minutes: dict = field(default_factory=dict)
    unmet: dict = field(default_factory=dict)
    to_order: dict = field(default_factory=dict)
    treatsure_kg: float = 0.0
    empty_spells: list = field(default_factory=list)   # [dish id, start minute, end minute]


class World:
    """The simulated real kitchen for one morning: true stock, true demand and pending batches."""

    def __init__(self, dishes, demand, arrivals, step, cook_to_order_waste):
        self.dishes = dishes
        self.demand = demand                    # true total demand per dish for the morning
        self.arrivals = arrivals                # diners per 15-minute slot
        self.total = max(arrivals.sum(), 1e-9)
        self.step = step
        self.w = cook_to_order_waste
        self.stock = {d["id"]: float(d["pan_capacity"]) for d in dishes}
        self.pending = []                       # (ready minute, dish id, amount)
        self.seen_log = 0                       # engine log entries already turned into cooking here
        self.until = SERVICE_START              # the simulated kitchen has been played up to here
        self.r = DayResult()
        for d in dishes:
            did = d["id"]
            self.r.prepared[did] = float(d["pan_capacity"])
            for k in ("served", "empty_minutes", "unmet", "to_order"):
                getattr(self.r, k)[did] = 0.0

    def arrivals_in(self, t: float) -> float:
        i = int((t - SERVICE_START) // SLOT)
        return self.arrivals[i] * self.step / SLOT if 0 <= i < len(self.arrivals) else 0.0

    def cook(self, dish_id: str, amount: float, ready: float) -> None:
        self.r.prepared[dish_id] += amount
        self.pending.append((ready, dish_id, amount))

    def bring_out(self, t: float) -> None:
        for p in [p for p in self.pending if p[0] <= t]:
            self.pending.remove(p)
            self.stock[p[1]] += p[2]

    def consume(self, t: float, to_order: set) -> None:
        share = self.arrivals_in(t) / self.total
        for d in self.dishes:
            did = d["id"]
            want = self.demand[did] * share
            if want <= 0:
                continue
            got = min(self.stock[did], want)
            self.stock[did] -= got
            short = want - got
            if short > 1e-9 and did in to_order:
                # cooked to order: served, with a small share wasted on pans and plates
                self.r.prepared[did] += short * (1 + self.w)
                self.r.to_order[did] += short
                got += short
                short = 0.0
            self.r.served[did] += got
            if short > 1e-9:
                self.r.unmet[did] += short
                gone = self.step * short / want
                self.r.empty_minutes[did] += gone
                self._spell(did, t + self.step - gone, t + self.step)

    def _spell(self, dish_id: str, start: float, end: float) -> None:
        """Join empty minutes that touch into one spell, so the report can say "08:36 to 08:42"."""
        for sp in reversed(self.r.empty_spells):
            if sp[0] == dish_id and sp[2] >= start - self.step - 1e-6:
                sp[2] = end
                return
        self.r.empty_spells.append([dish_id, start, end])

    def close(self) -> DayResult:
        for d in self.dishes:
            did = d["id"]
            pending = sum(p[2] for p in self.pending if p[1] == did)
            extra = self.r.to_order[did] * self.w
            self.r.left[did] = self.stock[did] + pending + extra
        return self.r


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------

def run_scheduled(day: dict, planned: dict, curve: np.ndarray, cfg: dict) -> DayResult:
    """Policies 1 and 2: cook the planned amount ahead of the expected curve, plus one batch when empty."""
    dishes, step = cfg["dishes"], cfg["replay"]["step_minutes"]
    world = World(dishes, day["demand"], day["arrivals"], step, cfg["rules"]["cook_to_order_waste"])
    cooked = {d["id"]: float(d["pan_capacity"]) for d in dishes}
    for t in range(SERVICE_START, SERVICE_END, step):
        world.bring_out(t)
        for d in dishes:
            did, lead, batch = d["id"], float(d["lead_minutes"]), float(d["batch"])
            if t + lead > minutes(d["last_cook"]):
                continue
            target = planned[did] * _cum(curve, t + lead + SLOT)
            while cooked[did] < min(planned[did], target) - 1e-9:
                world.cook(did, batch, t + lead)
                cooked[did] += batch
            busy = any(p[1] == did for p in world.pending)
            if world.stock[did] <= 1e-9 and not busy:
                world.cook(did, batch, t + lead)     # the chef cooks one more batch when a tray is empty
                cooked[did] += batch
        world.consume(t, set())
    return world.close()


def _cum(curve: np.ndarray, minute: float) -> float:
    from buffetiq.nowcast import cumulative_share

    return cumulative_share(curve, minute)


def run_buffetiq(day: dict, n0: float, shares: np.ndarray, rates: dict, cfg: dict, rng: random.Random,
                 cook_to_order: bool = True) -> DayResult:
    """Policy 3: the live engine, seeing only logged arrivals and noisy camera levels."""
    rules = dict(cfg["rules"])
    if not cook_to_order:
        rules["cook_to_order_threshold"] = 0
    world = World(cfg["dishes"], day["demand"], day["arrivals"], cfg["replay"]["step_minutes"],
                  rules["cook_to_order_waste"])
    eng = Engine(dishes=cfg["dishes"], rules=rules, n0=n0, shares=list(shares), rates=rates)
    treat = play(eng, world, SERVICE_START, SERVICE_END, cfg, rng)
    r = world.close()
    r.treatsure_kg = treat
    return r


def play(eng: Engine, world: World, start: float, end: float, cfg: dict, rng: random.Random) -> float:
    """Run the engine against the simulated kitchen from `start` to `end`; returns kg flagged for Treatsure.

    BuffetIQ sees only the logged arrivals and a camera reading of every tray each 15 minutes.
    """
    dishes, step = cfg["dishes"], cfg["replay"]["step_minutes"]
    acc = cfg["replay"]["camera_accuracy"]
    check = eng.rules["check_minutes"]
    seen = world.seen_log
    treat = 0.0
    for t in range(int(start), int(end), step):
        world.bring_out(t)
        if t > SERVICE_START and (t - SERVICE_START) % check == 0:
            for d in dishes:
                level = camera_reading(true_level(world.stock[d["id"]], float(d["pan_capacity"])), acc, rng)
                eng.tray_check(d["id"], estimate(level, d)["amount"], level, t)
        eng.step(t)
        for entry in eng.log[seen:]:
            if entry[1] == "cook":
                d = next(x for x in dishes if x["id"] == entry[2])
                world.cook(entry[2], entry[3], t + float(d["lead_minutes"]))
        seen = len(eng.log)
        for a in eng.alerts:
            if a.key.startswith("treat-") and a.at == t:
                d = next(x for x in dishes if x["id"] == a.key[6:])
                treat += eng.surplus(d, t)
        to_order = {d["id"] for d in dishes if eng.to_order and d.get("hot")}
        eng.log_arrivals(world.arrivals_in(t), t)
        world.consume(t, to_order)
        world.until = t + step
    world.seen_log = seen
    return treat


# ---------------------------------------------------------------------------
# The 65 test days
# ---------------------------------------------------------------------------

def day_inputs(row: pd.Series, cfg: dict) -> dict:
    demand = {}
    for d in cfg["dishes"]:
        demand[d["id"]] = float(row[data_gen.dish_columns(d)["demand"]])
    return {"date": row["date"], "demand": demand, "arrivals": row[data_gen.ARRIVAL_COLUMNS].to_numpy(float),
            "planned": {d["id"]: float(row[data_gen.dish_columns(d)["prepared"]]) for d in cfg["dishes"]}}


def summarise(results: list[DayResult], cfg: dict) -> dict:
    out = {"per_dish": {}, "days": len(results)}
    tot_left = tot_prep = tot_cost = tot_min = tot_unmet = 0.0
    for d in cfg["dishes"]:
        did = d["id"]
        left = np.array([kg(d, r.left[did]) for r in results])
        prep = np.array([kg(d, r.prepared[did]) for r in results])
        mins = np.array([r.empty_minutes[did] for r in results])
        unmet = np.array([kg(d, r.unmet[did]) for r in results])
        cost = left * d["cost_per_kg"]
        out["per_dish"][did] = {"name": d["name"], "left_kg": float(left.mean()), "prepared_kg": float(prep.mean()),
                                "empty_minutes": float(mins.mean()), "empty_minutes_total": float(mins.sum()),
                                "days_with_empty": int((mins > 0.5).sum()), "unmet_kg": float(unmet.mean()),
                                "cost": float(cost.mean())}
        tot_left += left.mean(); tot_prep += prep.mean(); tot_cost += cost.mean()
        tot_min += mins.mean(); tot_unmet += unmet.mean()
    out.update({"left_kg": tot_left, "prepared_kg": tot_prep, "cost": tot_cost, "empty_minutes": tot_min,
                "unmet_kg": tot_unmet, "treatsure_kg": float(np.mean([r.treatsure_kg for r in results]))})
    return out


def evaluate(write: bool = True) -> dict:
    cfg = load_config()
    full = forecast.load_history()
    train, test = forecast.split(full, cfg["forecast"]["train_days"])
    model = forecast.Forecaster(cfg).fit(train, tune=False)
    b = cfg["rules"]["safety_buffer"]
    seed = cfg["simulation"]["seed"]
    profile = model.curve_profile                       # the usual curve for weekdays and weekends

    runs: dict[str, list] = {"baseline": [], "forecast_only": [], "buffetiq": [], "buffetiq_no_cook_to_order": []}
    accept_runs = {a: [] for a in cfg["replay"]["acceptance_levels"]}
    for i in range(len(test)):
        row = test.iloc[i]
        day = day_inputs(row, cfg)
        X = test.iloc[[i]]
        n0 = float(model.predict_diners(X)[0])
        shares = model.predict_curve(X)[0]
        rates = {d["id"]: float(model.dish_rate(X, d["id"])[0]) for d in cfg["dishes"]}
        usual = profile[int(row["weekend_like"])]

        runs["baseline"].append(run_scheduled(day, day["planned"], usual, cfg))
        planned_fc = {d["id"]: round_up(rates[d["id"]] * n0 * (1 + b), float(d["batch"])) for d in cfg["dishes"]}
        runs["forecast_only"].append(run_scheduled(day, planned_fc, shares, cfg))
        runs["buffetiq"].append(run_buffetiq(day, n0, shares, rates, cfg, random.Random(seed + i)))
        runs["buffetiq_no_cook_to_order"].append(
            run_buffetiq(day, n0, shares, rates, cfg, random.Random(seed + i), cook_to_order=False))
        for a in accept_runs:
            shifted = dict(day, arrivals=shift_arrivals(day["arrivals"], shares * n0, a))
            accept_runs[a].append(run_buffetiq(shifted, n0, shares, rates, cfg, random.Random(seed + i)))

    results = {"test_days": [test["date"].iloc[0], test["date"].iloc[-1]],
               "policies": {k: summarise(v, cfg) for k, v in runs.items()},
               "acceptance": {str(a): summarise(v, cfg) for a, v in accept_runs.items()},
               "camera_accuracy": cfg["replay"]["camera_accuracy"]}
    base = results["policies"]["baseline"]
    for k, v in results["policies"].items():
        v["change_left_pct"] = 100 * (v["left_kg"] / base["left_kg"] - 1)
        v["change_cost_pct"] = 100 * (v["cost"] / base["cost"] - 1)
        v["change_empty_minutes"] = v["empty_minutes"] - base["empty_minutes"]
    if write:
        RESULTS_PATH.write_text(json.dumps(results, indent=2))
        plot_policies(results, CHARTS / "phase5_policies.png")
    return results


def plot_policies(results: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = {"baseline": "Baseline chef rule", "forecast_only": "Forecast only", "buffetiq": "Full BuffetIQ"}
    keys = list(names)
    left = [results["policies"][k]["left_kg"] for k in keys]
    mins = [results["policies"][k]["empty_minutes"] for k in keys]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150)
    fig.patch.set_facecolor("#FAF8F4")
    colours = ["#D9D3C7", "#9FC9C3", "#0F6E6E"]
    for ax, vals, label, fmt in ((axes[0], left, "Surplus at close (kg a day)", "{:.1f} kg"),
                                 (axes[1], mins, "Minutes a dish was empty (a day, all dishes)", "{:.0f} min")):
        ax.set_facecolor("#FFFFFF")
        ax.bar([names[k] for k in keys], vals, color=colours, width=0.6)
        for i, v in enumerate(vals):
            ax.text(i, v, fmt.format(v), ha="center", va="bottom", fontsize=10, fontweight="bold", color="#1F2328")
        ax.set_title(label, loc="left", fontsize=11, color="#1F2328")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors="#5F646B")
        ax.grid(axis="y", color="#EFEAE0")
        ax.set_axisbelow(True)
    b, f = left[0], left[2]
    fig.suptitle(f"Full BuffetIQ leaves {100 * (1 - f / b):.0f}% less food than the baseline chef rule",
                 x=0.02, ha="left", fontsize=13, fontweight="bold", color="#1F2328")
    fig.text(0.02, 0.01, "Average over 65 test days, 21 September to 24 November 2026. Simulated on fictional data.",
             fontsize=9, color="#5F646B")
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    r = evaluate()
    for k, v in r["policies"].items():
        print(f"{k:<26} left {v['left_kg']:6.1f} kg ({v['change_left_pct']:+.0f}%)  cost S${v['cost']:6.1f} "
              f"empty {v['empty_minutes']:6.1f} min ({v['change_empty_minutes']:+.1f})  prepared {v['prepared_kg']:.1f}"
              f"  unmet {v['unmet_kg']:.2f} kg  treatsure {v['treatsure_kg']:.1f}")
    for a, v in r["acceptance"].items():
        print(f"accept {a:<5} left {v['left_kg']:6.1f} kg  empty {v['empty_minutes']:6.1f} min")


if __name__ == "__main__":
    main()
