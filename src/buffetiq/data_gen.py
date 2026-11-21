"""Synthetic breakfast history for a fictional 300-room Singapore city hotel (Phase 1).

One row per breakfast service from 25 November 2025 to 24 November 2026, with
sixteen 15-minute arrival slots from 06:30 to 10:30. Every number comes from the
`simulation` and `calendar` sections of config.yaml and is explained in
docs/ASSUMPTIONS.md. The output was frozen before Phase 2 (see docs/EVIDENCE.md);
the generator must not be changed to make BuffetIQ look better.

Run:  python -m buffetiq.data_gen      (writes data/synthetic_breakfast.csv)
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import pandas as pd

from buffetiq.state import ROOT, load_config

OUT_PATH = ROOT / "data" / "synthetic_breakfast.csv"
SLOT_START_MIN = 6 * 60 + 30
SLOT_MINUTES = 15
N_SLOTS = 16
SLOT_LABELS = [f"{(SLOT_START_MIN + i * SLOT_MINUTES) // 60:02d}{(SLOT_START_MIN + i * SLOT_MINUTES) % 60:02d}"
               for i in range(N_SLOTS)]
ARRIVAL_COLUMNS = [f"arr_{s}" for s in SLOT_LABELS]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Columns that only the simulation knows. Models must never use them as features:
# a real hotel cannot observe true demand, the check-in response rate or the cause
# of a surprise in advance.
HIDDEN_SUFFIXES = ("_demand",)
HIDDEN_COLUMNS = ("surprise", "checkin_response_rate")


def unit_suffix(dish: dict) -> str:
    return "pcs" if dish["unit"] == "pieces" else "kg"


def dish_columns(dish: dict) -> dict[str, str]:
    s = unit_suffix(dish)
    return {k: f"{dish['id']}_{k}_{s}" for k in ("prepared", "consumed", "leftover", "demand")}


def hidden_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c in HIDDEN_COLUMNS or "_demand_" in c]


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

def _school_holiday_set(cal: dict) -> set[pd.Timestamp]:
    days: set[pd.Timestamp] = set()
    for start, end in cal["school_holidays"]:
        days.update(pd.date_range(start, end, freq="D"))
    return days


def build_calendar(sim: dict, cal: dict) -> pd.DataFrame:
    start = pd.Timestamp(sim["start"]) - pd.Timedelta(days=sim["burn_in_days"])
    dates = pd.date_range(start, sim["end"], freq="D")
    holidays = {pd.Timestamp(d) for d in cal["public_holidays"]}
    school = _school_holiday_set(cal)
    df = pd.DataFrame({"date": dates})
    df["day_of_week"] = df["date"].dt.day_of_week.map(lambda i: WEEKDAYS[i])
    df["is_weekend"] = df["date"].dt.day_of_week >= 5
    df["public_holiday"] = df["date"].isin(holidays)
    df["school_holiday"] = df["date"].isin(school)
    df["burn_in"] = df["date"] < pd.Timestamp(sim["start"])
    return df


# ---------------------------------------------------------------------------
# Occupancy and guests
# ---------------------------------------------------------------------------

def simulate_occupancy(df: pd.DataFrame, sim: dict, rng: np.random.Generator) -> np.ndarray:
    """Night-before occupancy whose monthly mean equals the STB figure for that month."""
    shift = df["day_of_week"].map(sim["weekday_occupancy_shift"]).to_numpy(float)
    shift = shift + np.where(df["public_holiday"], 2.0, 0.0)
    noise = np.zeros(len(df))
    phi, sd = sim["occupancy_noise_persistence"], sim["occupancy_noise_pp"]
    for i in range(len(df)):
        prev = noise[i - 1] if i else 0.0
        noise[i] = phi * prev + rng.normal(0, sd * math.sqrt(1 - phi ** 2))
    pattern = shift + noise
    month = df["date"].dt.strftime("%Y-%m")
    occ = np.zeros(len(df))
    for m, idx in df.groupby(month).groups.items():
        target = sim["monthly_occupancy"][m]
        p = pattern[idx]
        occ[idx] = target + (p - p.mean())
    return np.clip(occ / 100.0, 0.40, 0.99)


def business_share(row, sim: dict, rng: np.random.Generator) -> float:
    b = sim["business_share"]
    if row.public_holiday:
        base = b["public_holiday"]
    elif row.is_weekend:
        base = b["weekend"]
    elif row.day_of_week == "Mon":
        base = b["monday"]
    else:
        base = b["weekday"]
    if row.school_holiday:
        base *= sim["business_share_school_holiday_factor"]
    return float(np.clip(base + rng.normal(0, sim["business_share_sd"]), 0.05, 0.85))


def _beta(rng, mean, sd):
    k = mean * (1 - mean) / sd ** 2 - 1
    return rng.beta(mean * k, (1 - mean) * k)


# ---------------------------------------------------------------------------
# Arrival curve
# ---------------------------------------------------------------------------

def slot_shares(mean: float, sd: float) -> np.ndarray:
    """Share of a normal arrival-time distribution in each slot, truncated to service hours."""
    edges = SLOT_START_MIN + SLOT_MINUTES * np.arange(N_SLOTS + 1)
    cdf = 0.5 * (1 + np.vectorize(math.erf)((edges - mean) / (sd * math.sqrt(2))))
    p = np.diff(cdf)
    return p / p.sum()


def arrival_probabilities(business: float, weekend_like: bool, sim: dict, rng, surprise: str) -> np.ndarray:
    comp = sim["arrival_components"]
    b_mean = comp["business"]["mean"] + rng.normal(0, 5)
    b_sd = comp["business"]["sd"]
    lk = comp["leisure_weekend"] if weekend_like else comp["leisure_weekday"]
    l_mean, l_sd = lk["mean"] + rng.normal(0, 8), lk["sd"]
    if surprise == "rain":            # guests linger in their rooms, then come later and spread out
        l_mean += 20
        l_sd += 10
        b_mean += 10
    elif surprise == "early_event":   # a conference or early flights pull business guests forward
        b_mean -= 20
    p = business * slot_shares(b_mean, b_sd) + (1 - business) * slot_shares(l_mean, l_sd)
    return p / p.sum()


# ---------------------------------------------------------------------------
# One service
# ---------------------------------------------------------------------------

def simulate_day(row, occ: float, sim: dict, rng: np.random.Generator, rooms_total: int) -> dict:
    rooms = int(round(rooms_total * occ))
    weekend_like = bool(row.is_weekend or row.public_holiday)

    # group bookings (counted inside occupancy; tour groups always take breakfast)
    gp = sim["group_probability"]
    p_group = (gp["weekend"] if weekend_like else gp["weekday"]) + (gp["school_holiday_extra"] if row.school_holiday else 0)
    group = rng.random() < p_group
    group_size = int(rng.integers(sim["group_size"][0], sim["group_size"][1] + 1)) if group else 0
    group_rooms = min(rooms, math.ceil(group_size / 2))

    share = business_share(row, sim, rng)
    other_rooms = rooms - group_rooms
    bus_rooms = int(rng.binomial(other_rooms, share))
    lei_rooms = other_rooms - bus_rooms
    apr = sim["adults_per_room"]
    bus_adults = bus_rooms + int(rng.binomial(bus_rooms, apr["business"] - 1))
    lei_adults = lei_rooms + int(rng.binomial(lei_rooms, apr["leisure"] - 1))
    cpr = sim["children_per_leisure_room"]
    if row.school_holiday:
        kids_rate = cpr["school_holiday_weekend"] if weekend_like else cpr["school_holiday"]
    else:
        kids_rate = cpr["weekend"] if weekend_like else cpr["weekday"]
    children = int(rng.poisson(kids_rate * lei_rooms))
    adults = bus_adults + lei_adults + group_size

    incl_share = float(np.clip(_beta(rng, sim["breakfast_inclusive_share"], sim["breakfast_inclusive_sd"]), 0.5, 0.97))
    incl_rooms = group_rooms + int(rng.binomial(other_rooms, incl_share))

    # surprises: about one day in fifteen, never visible in the features
    surprise = "none"
    if rng.random() < sim["surprise_probability"]:
        kinds = list(sim["surprise_weights"])
        w = np.array([sim["surprise_weights"][k] for k in kinds], float)
        surprise = str(rng.choice(kinds, p=w / w.sum()))

    sr = dict(sim["show_rate"])
    if surprise == "rain":
        sr = {k: min(0.98, v * 1.08) for k, v in sr.items()}
    elif surprise == "quiet_morning":
        sr = {k: v * 0.88 for k, v in sr.items()}

    # who eats: inclusive guests by their show rate, others buy breakfast at a low rate
    incl_other = incl_rooms - group_rooms
    bus_in = int(round(bus_adults * incl_other / max(other_rooms, 1)))
    lei_in = int(round(lei_adults * incl_other / max(other_rooms, 1)))
    kid_in = int(round(children * incl_other / max(other_rooms, 1)))
    buy = sim["non_inclusive_buy_rate"]
    d_bus = rng.binomial(bus_in, sr["business"]) + rng.binomial(bus_adults - bus_in, buy)
    d_lei = rng.binomial(lei_in, sr["leisure"]) + rng.binomial(lei_adults - lei_in, buy)
    d_kid = rng.binomial(kid_in, sr["leisure"]) + rng.binomial(children - kid_in, buy)
    d_grp = rng.binomial(group_size, sr["group"])
    extra = 0
    if surprise == "tour_group_early":   # an unannounced tour party on a voucher, arriving early
        extra = int(rng.integers(18, 31))
    adult_diners = int(d_bus + d_lei + d_grp + extra)
    diners = adult_diners + int(d_kid)

    # arrivals per slot
    bus_frac = d_bus / max(diners, 1)
    p = arrival_probabilities(bus_frac, weekend_like, sim, rng, surprise)
    block = int(d_grp + extra)
    free = diners - block
    arrivals = rng.multinomial(free, p) if free > 0 else np.zeros(N_SLOTS, int)
    if block:
        # groups come together: most within two slots between 06:45 and 08:00
        start = int(rng.integers(1, 6)) if surprise != "tour_group_early" else int(rng.integers(1, 4))
        core = int(round(block * 0.7))
        arrivals[start] += core // 2
        arrivals[start + 1] += core - core // 2
        arrivals += rng.multinomial(block - core, p)
    assert arrivals.sum() == diners

    return {
        "occupancy_rate": round(occ, 4),
        "rooms_occupied": rooms,
        "adults": adults,
        "children": children,
        "breakfast_inclusive_rooms": incl_rooms,
        "business_share": round(share, 3),
        "group_booking": group,
        "group_size": group_size,
        "surprise": surprise,
        "diners": diners,
        "_adult_diners": adult_diners,
        "_business_diners": int(d_bus),
        "_child_diners": int(d_kid),
        **dict(zip(ARRIVAL_COLUMNS, arrivals.tolist())),
    }


def dish_demand(day: dict, dish: dict, rates: dict, sim: dict, rng) -> float:
    r = rates[dish["id"]]
    leisure_adults = day["_adult_diners"] - day["_business_diners"]
    units = (leisure_adults + day["_business_diners"] * r["business"]
             + day["_child_diners"] * sim["child_portion"] * r["child"])
    noise = rng.lognormal(0, sim["consumption_noise_sd"])
    return max(0.0, r["per_diner"] * units * noise)


def round_up(x: float, step: float) -> float:
    return math.ceil(round(x / step, 9)) * step


# ---------------------------------------------------------------------------
# Whole year
# ---------------------------------------------------------------------------

def generate(config: dict | None = None) -> pd.DataFrame:
    cfg = config or load_config()
    sim, cal, dishes = cfg["simulation"], cfg["calendar"], cfg["dishes"]
    rng = np.random.default_rng(sim["seed"])
    df = build_calendar(sim, cal)
    occ = simulate_occupancy(df, sim, rng)
    days = [simulate_day(row, occ[i], sim, rng, cfg["hotel"]["rooms"]) for i, row in enumerate(df.itertuples())]
    out = pd.concat([df.reset_index(drop=True), pd.DataFrame(days)], axis=1)

    # check-ins from the guest page: a random 0 to 40% response each day
    lo, hi = sim["checkin_response_rate"]
    rate = rng.uniform(lo, hi, len(out))
    no_show = rng.binomial((out["diners"] * sim["checkin_no_show_share"]).round().astype(int), rate)
    out["checkin_response_rate"] = rate.round(3)
    out["check_ins"] = rng.binomial(out["diners"], rate) + no_show

    # dishes: true demand, the chef rule for prepared, then consumed and leftover
    weeks = sim["chef_history_weeks"]
    for dish in dishes:
        cols = dish_columns(dish)
        demand = np.array([dish_demand(d, dish, sim["dish_rates"], sim, rng) for d in days])
        prepared = np.zeros(len(out))
        consumed = np.zeros(len(out))
        for i in range(len(out)):
            hist = [consumed[i - 7 * k] for k in range(1, weeks + 1) if i - 7 * k >= 0]
            if len(hist) < weeks:   # first burn-in weeks: the chef starts from occupancy
                base = demand[i]
            else:
                base = float(np.mean(hist))
            prepared[i] = round_up(base * (1 + sim["chef_buffer"]), dish["batch"])
            consumed[i] = min(demand[i], prepared[i])
        if dish["unit"] == "pieces":
            demand, consumed = np.round(demand), np.minimum(np.round(demand), prepared)
            out[cols["prepared"]] = prepared.astype(int)
            out[cols["consumed"]] = consumed.astype(int)
            out[cols["leftover"]] = (prepared - consumed).astype(int)
            out[cols["demand"]] = demand.astype(int)
        else:
            out[cols["prepared"]] = prepared.round(2)
            out[cols["consumed"]] = consumed.round(2)
            out[cols["leftover"]] = (out[cols["prepared"]] - out[cols["consumed"]]).round(2)
            out[cols["demand"]] = demand.round(2)

    out = out[~out["burn_in"]].drop(columns=["burn_in"] + [c for c in out.columns if c.startswith("_")])
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    lead = ["date", "day_of_week", "is_weekend", "public_holiday", "school_holiday", "occupancy_rate",
            "rooms_occupied", "adults", "children", "breakfast_inclusive_rooms", "business_share",
            "group_booking", "group_size", "check_ins", "diners"]
    rest = [c for c in out.columns if c not in lead]
    return out[lead + rest].reset_index(drop=True)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> None:
    df = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, lineterminator="\n")
    print(f"Wrote {len(df)} days to {OUT_PATH}")
    print(f"SHA-256 {file_sha256(OUT_PATH)}")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Evidence chart
# ---------------------------------------------------------------------------

def plot_arrival_curves(df: pd.DataFrame, path: Path) -> Path:
    """Average share of the morning's diners in each 15-minute slot, weekdays against weekends."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    weekend = df["is_weekend"] | df["public_holiday"]
    groups = {"Weekdays": (~weekend, "#0F6E6E", "o"), "Weekends and public holidays": (weekend, "#B5560B", "s")}
    labels = [f"{s[:2]}:{s[2:]}" for s in SLOT_LABELS]
    x = np.arange(N_SLOTS)
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=150)
    fig.patch.set_facecolor("#FAF8F4")
    ax.set_facecolor("#FFFFFF")
    for name, (mask, colour, marker) in groups.items():
        sub = df.loc[mask, ARRIVAL_COLUMNS]
        share = sub.div(sub.sum(axis=1), axis=0) * 100
        mean = share.mean()
        lo, hi = share.quantile(0.1), share.quantile(0.9)
        ax.fill_between(x, lo, hi, color=colour, alpha=0.10, linewidth=0)
        ax.plot(x, mean, color=colour, linewidth=2, marker=marker, markersize=6,
                markeredgecolor="#FFFFFF", markeredgewidth=1.5, label=f"{name} ({mask.sum()} days)")
        peak = int(mean.to_numpy().argmax())
        ax.annotate(f"{name.split()[0]} peak {labels[peak]} · {mean.iloc[peak]:.1f}%", (peak, mean.iloc[peak]),
                    xytext=(0, 10), textcoords="offset points", ha="center", fontsize=10, color="#1F2328",
                    fontweight="bold")
    ax.set_xticks(x[::2], labels[::2])
    ax.set_ylabel("Share of the morning's diners (%)", color="#5F646B")
    ax.set_xlabel("Arrival slot (start of each 15 minutes)", color="#5F646B")
    ax.set_ylim(0, None)
    ax.grid(axis="y", color="#EFEAE0", linewidth=1)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#CFC8BA")
    ax.tick_params(colors="#5F646B")
    ax.legend(frameon=False, loc="upper right")
    fig.suptitle("Weekday arrivals peak at 07:30; weekend arrivals peak about 90 minutes later, at 09:00",
                 x=0.06, ha="left", fontsize=13, fontweight="bold", color="#1F2328")
    ax.set_title("Average arrival curve per 15-minute slot, with the 10th to 90th percentile band. "
                 "Simulated on fictional data.", loc="left", fontsize=10, color="#5F646B")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path
