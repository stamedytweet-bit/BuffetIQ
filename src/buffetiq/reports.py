"""Day-end report, history and retraining (Phase 7).

The report is built for the service in state.py:

* Today: the morning is finished on a copy of the kitchen engine and the
  simulated kitchen (demo), up to 10:30, so the live board is not changed. Any
  dish recorded with the runner's "Record leftovers" uses that figure instead,
  and discarded pans count as waste.
* A usual day: the same morning (same guests, same demand) replayed under the
  usual chef rule, so the comparison is like for like.
* What happened today: up to four notable events from the engine and the log.
* Forecast keeps improving: forecast error by week of use, starting from four
  weeks of history (simulated).

"Retrain tonight" adds today's service to the history and retrains the forecast,
and the NEA file lists every logged day's food waste by dish in kilograms.
Every figure is simulated on fictional data.
"""

from __future__ import annotations

import copy
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from buffetiq import data_gen, forecast, nowcast, simulate, state

LOGGED_DAYS_PATH = state.ROOT / "data" / "service_days.csv"
LEARNING_PATH = state.ROOT / "models" / "learning_curve.json"
NEA_PATH = state.ROOT / "data" / "nea_food_waste.csv"
RETRAIN_PATH = state.ROOT / "models" / "retrain_status.json"


def kg(dish: dict, amount: float) -> float:
    return simulate.kg(dish, amount)


# ---------------------------------------------------------------------------
# Today and a usual day
# ---------------------------------------------------------------------------

def finish_today(svc) -> dict:
    """Play the morning to 10:30 on copies of the engine and the simulated kitchen."""
    cfg = svc.config
    with state.LOCK:
        if svc.world is None:           # never replayed: simulate the whole morning from 06:30
            tmp = copy.copy(svc)
            tmp.engine = svc._new_engine()
            tmp.world = None
            state.Service.replay_to(tmp, cfg["service"]["end"])
            eng, world = tmp.engine, tmp.world
            start = nowcast.SERVICE_END
        else:
            eng, world = copy.deepcopy(svc.engine), copy.deepcopy(svc.world)
            start = max(svc.clock_minutes(), nowcast.SERVICE_START)
        rng = copy.deepcopy(svc.world_rng) if svc.world_rng is not None else random.Random(cfg["simulation"]["seed"])
    if start < nowcast.SERVICE_END:
        step = cfg["replay"]["step_minutes"]
        start = int(np.ceil(start / step) * step)
        simulate.play(eng, world, start, nowcast.SERVICE_END, cfg, rng)
    eng.step(nowcast.SERVICE_END)
    r = world.close()
    return {"result": r, "engine": eng}


def usual_day(svc) -> simulate.DayResult:
    """The same morning under the usual chef rule (same-weekday average plus 15%, usual arrival curve)."""
    row = svc.row.iloc[0]
    day = simulate.day_inputs(row, svc.config)
    curve = svc.model.curve_profile[int(row["weekend_like"])]
    return simulate.run_scheduled(day, day["planned"], curve, svc.config)


def logged_rows(svc) -> pd.DataFrame:
    if not svc.log_path.exists():
        return pd.DataFrame(columns=state.LOG_FIELDS)
    df = pd.read_csv(svc.log_path, dtype=str).fillna("")
    return df[df["service_date"] == svc.service_date]


def longest_spell(result: simulate.DayResult, dishes: list) -> tuple[str, float, float] | None:
    if not result.empty_spells:
        return None
    did, a, b = max(result.empty_spells, key=lambda s: s[2] - s[1])
    name = next(d["name"] for d in dishes if d["id"] == did)
    return name, a, b


def build(svc=None) -> dict:
    """Everything the day-end report shows, as numbers and text."""
    svc = svc or state.service()
    cfg = svc.config
    dishes = cfg["dishes"]
    done = finish_today(svc)
    today, eng = done["result"], done["engine"]
    usual = usual_day(svc)
    log = logged_rows(svc)

    # the runner's own leftover records win; discarded pans count as waste
    recorded = {}
    for _, row in log[log["action"] == "leftover"].iterrows():
        recorded[row["dish"]] = float(row["amount"])
    discarded = {}
    for _, row in log[log["action"] == "discard"].iterrows():
        discarded[row["dish"]] = discarded.get(row["dish"], 0.0) + float(row["amount"] or 0)

    rows = []
    for d in dishes:
        did = d["id"]
        prepared = kg(d, today.prepared[did])
        left = kg(d, recorded[did]) if did in recorded else kg(d, today.left[did])
        left = min(left + kg(d, discarded.get(did, 0.0)), prepared)
        eaten = max(prepared - left, 0.0)
        rows.append({"id": did, "name": d["name"], "prepared": prepared, "eaten": eaten, "left": left,
                     "usual_left": kg(d, usual.left[did]), "usual_prepared": kg(d, usual.prepared[did]),
                     "cost": left * d["cost_per_kg"], "usual_cost": kg(d, usual.left[did]) * d["cost_per_kg"],
                     "recorded": did in recorded})
    left_total = sum(r["left"] for r in rows)
    usual_total = sum(r["usual_left"] for r in rows)
    cost, usual_cost = sum(r["cost"] for r in rows), sum(r["usual_cost"] for r in rows)
    mins, usual_mins = sum(today.empty_minutes.values()), sum(usual.empty_minutes.values())
    diners = int(svc.row["diners"].iloc[0])
    jumps = [a for a in eng.alerts if a.key.startswith("jump-")]
    revised = (int(round(float(jumps[0].key[5:]))), nowcast.hhmm(jumps[0].at)) if jumps else None
    return {
        "date": svc.service_date, "rows": rows, "left_total": left_total, "usual_total": usual_total,
        "cost": cost, "usual_cost": usual_cost, "empty_minutes": mins, "usual_empty_minutes": usual_mins,
        "spell": longest_spell(today, dishes), "usual_spell": longest_spell(usual, dishes),
        "diners": diners, "forecast": int(round(svc.n0)), "revised": revised,
        "events": events(svc, eng, today, log), "learning": learning_curve(),
    }


def events(svc, eng, today, log) -> list[dict]:
    """Up to four notable things from the morning, most important first."""
    out = []
    jumps = [a for a in eng.alerts if a.key.startswith("jump-")]
    if jumps:
        a = jumps[0]
        out.append({"title": f"Forecast {('raised' if 'raised' in a.line else 'lowered')} during service",
                    "line": f"{a.line[:-1]} at {nowcast.hhmm(a.at)}."})
    spell = longest_spell(today, svc.config["dishes"])
    if spell and spell[2] - spell[1] >= 1:
        name, a, b = spell
        cooked = [x for x in eng.log if x[1] == "cook" and x[2] == _id(svc, name) and a - 30 <= x[0] <= b]
        extra = f" The kitchen cooked {nowcast._amount(_dish(svc, name), cooked[-1][3])}." if cooked else ""
        out.append({"title": f"{name} ran out for {round(b - a)} minutes",
                    "line": f"Empty from {nowcast.hhmm(a)} to {nowcast.hhmm(b)}.{extra}"})
    treats = [a for a in eng.alerts if a.key.startswith("treat-")]
    if treats:
        names = [_dish(svc, a.key[6:])["name"].lower() for a in treats]
        total = sum(float(a.line.split("About ")[1].split(" kg")[0]) for a in treats)
        which = _join(names) if len(names) <= 2 else f"{names[0]}, {names[1]} and {len(names) - 2} more"
        out.append({"title": f"{total:.1f} kg offered on Treatsure",
                    "line": f"{which[0].upper() + which[1:]}, flagged from {nowcast.hhmm(min(a.at for a in treats))}."})
    overrides = log[log["action"] == "override"]
    if len(overrides):
        reasons = overrides["note"].str.split(": ", n=1).str[-1].value_counts()
        parts = [f"{n} for {r[0].lower() + r[1:]}" for r, n in reasons.items()]
        out.append({"title": f"{len(overrides)} chef override{'s' if len(overrides) != 1 else ''}",
                    "line": _join(parts).capitalize() + "."})
    if svc.plans:
        guests = svc.confirmed_guests()
        out.append({"title": f"{guests} guests booked on the guest page",
                    "line": f"{len(svc.plans)} rooms replied, {svc.declined_guests()} guests said not this time."})
    start = [x for x in eng.log if x[1] == "cook_to_order"]
    if start and len(out) < 4:
        out.append({"title": f"Cook-to-order from {nowcast.hhmm(start[0][0])}",
                    "line": "Hot dishes were cooked in small portions for the last guests."})
    return out[:4]


def _dish(svc, name_or_id: str) -> dict:
    return next(d for d in svc.config["dishes"] if name_or_id in (d["name"], d["id"]))


def _id(svc, name: str) -> str:
    return _dish(svc, name)["id"]


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


# ---------------------------------------------------------------------------
# Forecast keeps improving
# ---------------------------------------------------------------------------

LEARNING_POINTS = [("1 month", 4), ("2 months", 8), ("3 months", 12), ("10 months", 42)]


def learning_curve(refresh: bool = False) -> list[tuple[str, float]]:
    """Average diner forecast error (MAPE) on the same 65 test days, trained on more and more history.

    Keeping the test days fixed separates what the model has learned from how hard
    each week happens to be; week-by-week errors on different weeks were too noisy
    to show learning (see docs/EVIDENCE.md, Phase 7).
    """
    if LEARNING_PATH.exists() and not refresh:
        return [tuple(x) for x in json.loads(LEARNING_PATH.read_text())]
    cfg = state.load_config()
    hist = forecast.load_history()
    test = hist.iloc[cfg["forecast"]["train_days"]:]
    out = []
    for label, weeks in LEARNING_POINTS:
        m = forecast.Forecaster(cfg).fit_core(hist.iloc[: 7 * weeks], tune=False)
        out.append((label, round(forecast.metrics(test["diners"], m.predict_diners(test))["mape"], 1)))
    LEARNING_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEARNING_PATH.write_text(json.dumps(out))
    return out


# ---------------------------------------------------------------------------
# History, retraining and the NEA file
# ---------------------------------------------------------------------------

def log_day(svc=None, report: dict | None = None) -> pd.DataFrame:
    """Save today's service as one history row (same columns as the synthetic data)."""
    svc = svc or state.service()
    report = report or build(svc)
    row = svc.row.iloc[0].to_dict()
    for d, r in zip(svc.config["dishes"], report["rows"]):
        c = data_gen.dish_columns(d)
        f = float(d.get("piece_kg", 1.0)) if d["unit"] == "pieces" else 1.0
        row[c["prepared"]] = round(r["prepared"] / f, 2)
        row[c["consumed"]] = round(r["eaten"] / f, 2)
        row[c["leftover"]] = round(r["left"] / f, 2)
    row["logged_at"] = datetime.now().isoformat(timespec="seconds")
    new = pd.DataFrame([row])
    if LOGGED_DAYS_PATH.exists():
        old = pd.read_csv(LOGGED_DAYS_PATH)
        old = old[old["date"] != svc.service_date]
        new = pd.concat([old, new], ignore_index=True)
    LOGGED_DAYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    new.to_csv(LOGGED_DAYS_PATH, index=False)
    return new


def history_with_logged() -> pd.DataFrame:
    """The synthetic history, with any logged service days replacing their synthetic rows."""
    hist = pd.read_csv(data_gen.OUT_PATH)
    if LOGGED_DAYS_PATH.exists():
        logged = pd.read_csv(LOGGED_DAYS_PATH)
        hist = hist[~hist["date"].isin(logged["date"])]
        hist = pd.concat([hist, logged[[c for c in hist.columns if c in logged.columns]]], ignore_index=True)
    return forecast.add_features(hist.sort_values("date").reset_index(drop=True))


def tomorrow_row(svc) -> pd.DataFrame:
    """Tomorrow's bookings (simulated with the same generator), without its outcomes."""
    cfg = copy.deepcopy(state.load_config())
    nxt = (datetime.strptime(svc.service_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    cfg["simulation"]["end"] = nxt
    month = nxt[:7]
    cfg["simulation"]["monthly_occupancy"].setdefault(month, cfg["simulation"]["monthly_occupancy"][svc.service_date[:7]])
    df = data_gen.generate(cfg)
    return forecast.add_features(df[df["date"] == nxt].reset_index(drop=True))


def retrain(svc=None) -> dict:
    """Add today's service to the history, retrain the forecast, and compare tomorrow's forecast."""
    svc = svc or state.service()
    log_day(svc)
    tomorrow = tomorrow_row(svc)
    before = float(svc.model.predict_diners(tomorrow)[0])       # last night's model, without today
    hist = history_with_logged()
    model = forecast.Forecaster(svc.config).fit(hist[hist["date"] <= svc.service_date], tune=False)
    after = float(model.predict_diners(tomorrow)[0])
    forecast.save(model)
    status = {"retrained_at": datetime.now().isoformat(timespec="seconds"), "days": int((hist["date"] <= svc.service_date).sum()),
              "tomorrow": tomorrow["date"].iloc[0], "before": round(before, 1), "after": round(after, 1),
              "dishes_after": {d["id"]: round(float(model.dish_rate(tomorrow, d["id"])[0] * after), 2)
                               for d in svc.config["dishes"]}}
    RETRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    RETRAIN_PATH.write_text(json.dumps(status, indent=2))
    svc.log_event("retrain", note=f"tomorrow {status['tomorrow']}: {before:.0f} -> {after:.0f} diners", source="manager")
    return status


def nea_csv(path: Path = NEA_PATH) -> str:
    """Every logged day's food waste by dish in kilograms (simulated history plus logged services)."""
    cfg = state.load_config()
    hist = pd.read_csv(data_gen.OUT_PATH)
    logged = pd.read_csv(LOGGED_DAYS_PATH) if LOGGED_DAYS_PATH.exists() else pd.DataFrame(columns=["date"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "dish", "food_waste_kg", "source"])
        for _, row in hist.iterrows():
            src = logged[logged["date"] == row["date"]]
            use, label = (src.iloc[0], "logged service (simulated on fictional data)") if len(src) else \
                (row, "simulated history (fictional data)")
            for d in cfg["dishes"]:
                left = float(use[data_gen.dish_columns(d)["leftover"]])
                w.writerow([row["date"], d["name"], f"{kg(d, left):.2f}", label])
    return str(path)
