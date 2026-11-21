"""Demand forecast for the night before (Phase 2).

Three parts, each trained only on days before the one it predicts:

1. Diners: a Random Forest regressor on what the hotel knows the night before
   (day of week, holidays, occupancy, guests, breakfast-inclusive rooms, business
   share, group flag and guest-page check-ins).
2. Arrival curve: each 15-minute slot's share of the morning. A per-slot Random
   Forest is compared with a simple average profile by day type, and the simpler
   one is kept unless the model is clearly better (see `curve_tolerance`).
3. Dishes: kg (or pieces) per diner from a small linear regression on the guest
   mix, multiplied by predicted diners, plus a shopping list from the recipe card
   sized for the 80th percentile, with margins calibrated on held-back training days.

Evaluation (`python -m buffetiq.forecast` from the src folder) trains on the first
300 days, tests on the last 65, compares with the same-weekday four-week average,
and writes the numbers and charts used in docs/EVIDENCE.md. Every result is
simulated on fictional data.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

from buffetiq import data_gen
from buffetiq.state import ROOT, load_config

DATA_PATH = data_gen.OUT_PATH
CHARTS = ROOT / "docs" / "charts"
RESULTS_PATH = ROOT / "docs" / "phase2_results.json"
WEEKDAYS = data_gen.WEEKDAYS
SLOTS = data_gen.ARRIVAL_COLUMNS

# What the hotel knows the night before. Hidden simulation columns are never used.
DINER_FEATURES = [
    "dow", "is_weekend", "public_holiday", "school_holiday", "occupancy_rate", "adults", "children",
    "breakfast_inclusive_rooms", "business_share", "group_booking", "check_ins",
]
FEATURE_NAMES = {
    "dow": "Day of week", "is_weekend": "Weekend", "public_holiday": "Public holiday",
    "school_holiday": "School holiday", "occupancy_rate": "Occupancy", "adults": "Adults in house",
    "children": "Children in house", "breakfast_inclusive_rooms": "Breakfast-inclusive rooms",
    "business_share": "Business guest share", "group_booking": "Group booking", "check_ins": "Guest check-ins",
}
CURVE_FEATURES = ["dow", "is_weekend", "public_holiday", "school_holiday", "business_share",
                  "group_booking", "child_share"]
DISH_FEATURES = ["business_share", "child_share", "weekend_like"]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def load_history(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    return add_features(df)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dow"] = df["day_of_week"].map({d: i for i, d in enumerate(WEEKDAYS)})
    for col in ("is_weekend", "public_holiday", "school_holiday", "group_booking"):
        df[col] = df[col].astype(int)
    df["weekend_like"] = ((df["is_weekend"] == 1) | (df["public_holiday"] == 1)).astype(int)
    df["child_share"] = df["children"] / (df["adults"] + df["children"]).clip(lower=1)
    return df


def assert_no_hidden(features: list[str]) -> None:
    banned = set(data_gen.HIDDEN_COLUMNS) | {"diners"} | set(SLOTS)
    leaked = [f for f in features if f in banned or "_demand_" in f or "_consumed_" in f or "_leftover_" in f]
    if leaked:
        raise ValueError(f"Features must be known the night before; found {leaked}")


def split(df: pd.DataFrame, train_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("date").reset_index(drop=True)
    return df.iloc[:train_days].copy(), df.iloc[train_days:].copy()


# ---------------------------------------------------------------------------
# Metrics and baseline
# ---------------------------------------------------------------------------

def metrics(actual, predicted) -> dict:
    a, p = np.asarray(actual, float), np.asarray(predicted, float)
    err = p - a
    mask = a > 0
    return {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "mape": float(np.mean(np.abs(err[mask]) / a[mask]) * 100),
    }


def same_weekday_baseline(full: pd.DataFrame, column: str, weeks: int) -> pd.Series:
    """Average of the same weekday over the previous `weeks` weeks (actuals only, never the day itself)."""
    full = full.sort_values("date").reset_index(drop=True)
    lags = [full[column].shift(7 * k) for k in range(1, weeks + 1)]
    return pd.concat(lags, axis=1).mean(axis=1, skipna=False)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def stocked_out(df: pd.DataFrame, dish: dict) -> pd.Series:
    """Observable: the kitchen knows a dish ran out when everything prepared was eaten."""
    c = data_gen.dish_columns(dish)
    return df[c["consumed"]] >= df[c["prepared"]] - 1e-6


@dataclass
class Forecaster:
    config: dict
    diners_model: RandomForestRegressor | None = None
    diners_params: dict = field(default_factory=dict)
    curve_model: RandomForestRegressor | None = None
    curve_profile: dict = field(default_factory=dict)
    curve_method: str = "profile"
    dish_models: dict = field(default_factory=dict)
    dish_fixed_rates: dict = field(default_factory=dict)
    use_mix_rates: dict = field(default_factory=dict)
    diners_p80_factor: float = 1.0
    dish_p80_factors: dict = field(default_factory=dict)
    selection: dict = field(default_factory=dict)

    # ---- fitting ----
    def fit(self, train: pd.DataFrame, tune: bool = True) -> "Forecaster":
        """Fit, then make every choice and calibration from out-of-fold predictions.

        The training days are cut into time-ordered folds. For each fold, a model
        trained only on the days before it predicts the fold's days. Those
        out-of-fold predictions decide the arrival-curve method and the dish-rate
        method and set the shopping margins, so the test days are never used for
        any choice, and later days never inform earlier ones.
        """
        fc = self.config["forecast"]
        q = fc["shopping_quantile"]
        tol = fc["curve_tolerance"]
        folds = []
        for fit_idx, val_idx in TimeSeriesSplit(n_splits=fc["cv_splits"]).split(train):
            sub = Forecaster(self.config).fit_core(train.iloc[fit_idx], tune=False)
            folds.append((sub, train.iloc[val_idx]))

        # arrival curve: keep the simple profile unless the model is clearly better
        e = {"profile": [], "model": []}
        for sub, val in folds:
            actual = val[SLOTS].div(val["diners"], axis=0).to_numpy()
            for m in e:
                e[m].append(np.abs(sub._curve(val, m) - actual).mean(axis=1))
        e_prof, e_model = (float(np.concatenate(e[m]).mean()) for m in ("profile", "model"))
        curve_method = "model" if e_model < e_prof * (1 - tol) else "profile"
        self.selection["curve"] = {"profile_mae_pp": e_prof * 100, "model_mae_pp": e_model * 100,
                                   "chosen": curve_method}

        # diners margin: how far actual diners ran above the forecast on 4 in 5 days
        ratios = np.concatenate([val["diners"] / sub.predict_diners(val) for sub, val in folds])
        self.diners_p80_factor = float(np.quantile(ratios, q))

        # dishes: rate method on days the dish did not run out; margin on all days
        use_mix, self.selection["dishes"] = {}, {}
        for dish in self.config["dishes"]:
            c = data_gen.dish_columns(dish)
            err = {True: [], False: []}
            ratio = []
            for sub, val in folds:
                ok = val[~stocked_out(val, dish)]
                rate = ok[c["consumed"]] / ok["diners"]
                for mix in err:
                    err[mix].append(np.abs(sub.dish_rate(ok, dish["id"], mix) - rate))
            e_mix, e_fix = (float(np.concatenate(err[m]).mean()) for m in (True, False))
            mix = e_mix <= e_fix
            use_mix[dish["id"]] = mix
            for sub, val in folds:
                central = sub.dish_rate(val, dish["id"], mix) * sub.predict_diners(val)
                ratio.append(val[c["consumed"]] / central)
            self.dish_p80_factors[dish["id"]] = float(np.quantile(np.concatenate(ratio), q))
            self.selection["dishes"][dish["id"]] = {"mix_error": e_mix, "fixed_error": e_fix,
                                                     "chosen": "guest mix" if mix else "fixed"}

        self.fit_core(train, tune=tune)
        self.curve_method, self.use_mix_rates = curve_method, use_mix
        return self

    def fit_core(self, train: pd.DataFrame, tune: bool = True) -> "Forecaster":
        assert_no_hidden(DINER_FEATURES)
        assert_no_hidden(CURVE_FEATURES)
        fc = self.config["forecast"]
        seed = self.config["simulation"]["seed"]
        X, y = train[DINER_FEATURES], train["diners"]
        if tune:
            grid = GridSearchCV(
                RandomForestRegressor(n_estimators=fc["rf_trees"], random_state=seed, n_jobs=-1),
                {k: v for k, v in fc["rf_grid"].items()},
                cv=TimeSeriesSplit(n_splits=fc["cv_splits"]),
                scoring="neg_mean_absolute_error",
            )
            grid.fit(X, y)
            self.diners_params = grid.best_params_
        self.diners_model = RandomForestRegressor(
            n_estimators=fc["rf_trees"], random_state=seed, n_jobs=-1, **self.diners_params).fit(X, y)

        shares = train[SLOTS].div(train["diners"], axis=0)
        self.curve_profile = {
            int(k): shares[train["weekend_like"] == k].mean().to_numpy() for k in (0, 1)
        }
        self.curve_model = RandomForestRegressor(
            n_estimators=fc["rf_trees"], random_state=seed, n_jobs=-1, min_samples_leaf=3
        ).fit(train[CURVE_FEATURES], shares)

        for dish in self.config["dishes"]:
            ok = train[~stocked_out(train, dish)]
            c = data_gen.dish_columns(dish)
            rate = ok[c["consumed"]] / ok["diners"]
            self.dish_fixed_rates[dish["id"]] = float(rate.mean())
            self.dish_models[dish["id"]] = LinearRegression().fit(ok[DISH_FEATURES], rate)
            self.use_mix_rates[dish["id"]] = True
        return self

    def choose_curve(self, validation: pd.DataFrame) -> dict:
        """Compare the profile and the model on held-back training days; keep the simpler unless clearly worse."""
        tol = self.config["forecast"]["curve_tolerance"]
        actual = validation[SLOTS].div(validation["diners"], axis=0).to_numpy()
        e_prof = np.abs(self._curve(validation, "profile") - actual).mean()
        e_model = np.abs(self._curve(validation, "model") - actual).mean()
        self.curve_method = "model" if e_model < e_prof * (1 - tol) else "profile"
        return {"profile_mae_pp": e_prof * 100, "model_mae_pp": e_model * 100, "chosen": self.curve_method}

    # ---- predicting ----
    def predict_diners(self, df: pd.DataFrame) -> np.ndarray:
        return self.diners_model.predict(df[DINER_FEATURES])

    def diners_p80(self, df: pd.DataFrame) -> np.ndarray:
        return self.predict_diners(df) * self.diners_p80_factor

    def dishes_p80(self, df: pd.DataFrame) -> pd.DataFrame:
        central = self.predict_dishes(df)
        return central * pd.Series(self.dish_p80_factors)

    def tree_quantile(self, df: pd.DataFrame, q: float) -> np.ndarray:
        """Spread of the forest's trees, kept for comparison with the calibrated margin."""
        trees = np.stack([t.predict(df[DINER_FEATURES].to_numpy()) for t in self.diners_model.estimators_])
        return np.quantile(trees, q, axis=0)

    def _curve(self, df: pd.DataFrame, method: str) -> np.ndarray:
        if method == "profile":
            p = np.stack([self.curve_profile[int(k)] for k in df["weekend_like"]])
        else:
            p = np.clip(self.curve_model.predict(df[CURVE_FEATURES]), 0, None)
        return p / p.sum(axis=1, keepdims=True)

    def predict_curve(self, df: pd.DataFrame) -> np.ndarray:
        return self._curve(df, self.curve_method)

    def dish_rate(self, df: pd.DataFrame, dish_id: str, mix: bool | None = None) -> np.ndarray:
        mix = self.use_mix_rates[dish_id] if mix is None else mix
        if not mix:
            return np.full(len(df), self.dish_fixed_rates[dish_id])
        return np.clip(self.dish_models[dish_id].predict(df[DISH_FEATURES]), 0, None)

    def predict_dishes(self, df: pd.DataFrame, diners: np.ndarray | None = None, mix: bool | None = None) -> pd.DataFrame:
        diners = self.predict_diners(df) if diners is None else diners
        return pd.DataFrame({d["id"]: self.dish_rate(df, d["id"], mix) * diners for d in self.config["dishes"]},
                            index=df.index)

    def forecast_day(self, row: pd.DataFrame) -> dict:
        """Everything the board, guest page and shopping list need for one morning."""
        diners = float(self.predict_diners(row)[0])
        diners_hi = float(self.diners_p80(row)[0])
        curve = self.predict_curve(row)[0]
        dishes = self.predict_dishes(row, np.array([diners])).iloc[0].to_dict()
        dishes_hi = self.dishes_p80(row).iloc[0].to_dict()
        return {
            "diners": diners,
            "diners_p80": diners_hi,
            "slot_shares": curve.tolist(),
            "slot_diners": (curve * diners).tolist(),
            "dishes": dishes,
            "dishes_p80": dishes_hi,
            "shopping_list": shopping_list(dishes_hi, self.config),
        }


MODEL_PATH = ROOT / "models" / "forecast.joblib"


def save(model: Forecaster, path: Path = MODEL_PATH) -> Path:
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return path


def load(path: Path = MODEL_PATH) -> Forecaster:
    import joblib

    return joblib.load(path)


def train_on_all(config: dict | None = None) -> Forecaster:
    """The model the app uses: trained on every logged day (Phase 7 retrains it nightly)."""
    cfg = config or load_config()
    return Forecaster(cfg).fit(load_history(), tune=True)


def shopping_list(dish_amounts: dict, config: dict) -> dict:
    """Raw ingredients for the given finished amounts, from the recipe card. Pieces are rounded up."""
    total: dict[str, float] = {}
    for dish_id, amount in dish_amounts.items():
        for item, per_unit in config["recipes"][dish_id].items():
            total[item] = total.get(item, 0.0) + per_unit * amount
    return {k: (math.ceil(v) if k.endswith("_pcs") else round(v, 2)) for k, v in sorted(total.items())}


# ---------------------------------------------------------------------------
# Evaluation for docs/EVIDENCE.md
# ---------------------------------------------------------------------------

def evaluate(config: dict | None = None, write: bool = True) -> dict:
    cfg = config or load_config()
    fc = cfg["forecast"]
    full = load_history()
    train, test = split(full, fc["train_days"])
    weeks = fc["baseline_weeks"]

    model = Forecaster(cfg).fit(train, tune=True)

    results: dict = {"train": [train["date"].iloc[0], train["date"].iloc[-1]],
                     "test": [test["date"].iloc[0], test["date"].iloc[-1]],
                     "diners_params": {k: v for k, v in model.diners_params.items()}}

    # ---- diners ----
    pred = model.predict_diners(test)
    base = same_weekday_baseline(full, "diners", weeks).iloc[test.index].to_numpy()
    results["diners"] = {"model": metrics(test["diners"], pred), "baseline": metrics(test["diners"], base),
                         "mean_actual": float(test["diners"].mean())}
    hi = model.diners_p80(test)
    results["diners"]["p80_coverage"] = float((test["diners"] <= hi).mean())
    results["diners"]["tree_p80_coverage"] = float((test["diners"] <= model.tree_quantile(test, fc["shopping_quantile"])).mean())
    results["diners"]["p80_factor"] = model.diners_p80_factor

    # ---- arrival curve ----
    actual_shares = test[SLOTS].div(test["diners"], axis=0).to_numpy()
    results["curve"] = {
        "selection_on_training_days": model.selection["curve"],
        "test_profile_mae_pp": float(np.abs(model._curve(test, "profile") - actual_shares).mean() * 100),
        "test_model_mae_pp": float(np.abs(model._curve(test, "model") - actual_shares).mean() * 100),
        "chosen": model.curve_method,
    }
    slot_pred = model.predict_curve(test) * pred[:, None]
    results["curve"]["slot_diners_mae"] = float(np.abs(slot_pred - test[SLOTS].to_numpy()).mean())
    base_slots = np.stack([same_weekday_baseline(full, s, weeks).iloc[test.index].to_numpy() for s in SLOTS], axis=1)
    results["curve"]["slot_diners_mae_baseline"] = float(np.abs(base_slots - test[SLOTS].to_numpy()).mean())

    # ---- dishes, scored against the simulation's true demand ----
    results["dishes"] = {}
    dishes_pred = model.predict_dishes(test, pred)
    dishes_fixed = model.predict_dishes(test, pred, mix=False)
    dishes_hi = model.dishes_p80(test)
    dishes_tree = model.predict_dishes(test, model.tree_quantile(test, fc["shopping_quantile"]))
    for dish in cfg["dishes"]:
        c = data_gen.dish_columns(dish)
        truth = test[c["demand"]]
        b = same_weekday_baseline(full, c["consumed"], weeks).iloc[test.index]
        results["dishes"][dish["id"]] = {
            "name": dish["name"], "unit": dish["unit"],
            "model": metrics(truth, dishes_pred[dish["id"]]),
            "fixed_rate": metrics(truth, dishes_fixed[dish["id"]]),
            "baseline": metrics(truth, b),
            "rate_choice": model.selection["dishes"][dish["id"]]["chosen"],
            "p80_coverage": float((truth <= dishes_hi[dish["id"]]).mean()),
            "tree_p80_coverage": float((truth <= dishes_tree[dish["id"]]).mean()),
            "p80_factor": model.dish_p80_factors[dish["id"]],
            "mean_demand": float(truth.mean()),
        }

    # ---- feature importance (permutation on the test days) ----
    imp = permutation_importance(model.diners_model, test[DINER_FEATURES], test["diners"], n_repeats=30,
                                 random_state=cfg["simulation"]["seed"], scoring="neg_mean_absolute_error")
    results["importance"] = {f: float(m) for f, m in zip(DINER_FEATURES, imp.importances_mean)}

    # ---- the demo morning, Tuesday 24 November 2026 ----
    demo = model.forecast_day(test.iloc[[-1]])
    results["demo_morning"] = {"date": test["date"].iloc[-1], "diners": demo["diners"],
                               "diners_p80": demo["diners_p80"], "actual": int(test["diners"].iloc[-1]),
                               "shopping_list": demo["shopping_list"],
                               "dishes": demo["dishes"], "dishes_p80": demo["dishes_p80"]}

    if write:
        CHARTS.mkdir(parents=True, exist_ok=True)
        plot_importance(results["importance"], CHARTS / "phase2_feature_importance.png")
        plot_test_days(test, pred, base, CHARTS / "phase2_diners_test.png")
        RESULTS_PATH.write_text(json.dumps(results, indent=2, default=float))
    return results


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _style(ax, fig):
    fig.patch.set_facecolor("#FAF8F4")
    ax.set_facecolor("#FFFFFF")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#CFC8BA")
    ax.tick_params(colors="#5F646B")


def plot_importance(importance: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    items = sorted(importance.items(), key=lambda kv: kv[1])
    names = [FEATURE_NAMES[k] for k, _ in items]
    values = [v for _, v in items]
    top = items[-1][0]
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150)
    _style(ax, fig)
    colours = ["#0F6E6E" if k == top else "#9FC9C3" for k, _ in items]
    ax.barh(names, values, color=colours, height=0.6)
    for i, v in enumerate(values):
        ax.text(v + max(values) * 0.01, i, f"{v:.1f}", va="center", fontsize=9, color="#1F2328")
    ax.set_xlabel("Rise in mean absolute error (diners) when the feature is shuffled", color="#5F646B")
    ax.grid(axis="x", color="#EFEAE0")
    ax.set_axisbelow(True)
    fig.suptitle(f"{FEATURE_NAMES[top]} has the most influence on the diner forecast", x=0.03, ha="left",
                 fontsize=13, fontweight="bold", color="#1F2328")
    ax.set_title("Permutation importance on the 65 test days. Simulated on fictional data.", loc="left",
                 fontsize=10, color="#5F646B")
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_test_days(test: pd.DataFrame, pred: np.ndarray, base: np.ndarray, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dates = pd.to_datetime(test["date"])
    fig, ax = plt.subplots(figsize=(11, 5), dpi=150)
    _style(ax, fig)
    ax.plot(dates, test["diners"], color="#1F2328", linewidth=1.6, label="Actual diners")
    ax.plot(dates, pred, color="#0F6E6E", linewidth=2, marker="o", markersize=3.5, label="Random Forest forecast")
    ax.plot(dates, base, color="#B5560B", linewidth=1.4, linestyle="--", label="Same weekday, last 4 weeks")
    m, b = metrics(test["diners"], pred)["mae"], metrics(test["diners"], base)["mae"]
    ax.grid(axis="y", color="#EFEAE0")
    ax.set_ylabel("Diners", color="#5F646B")
    ax.legend(frameon=False, loc="upper left", ncol=3)
    fig.suptitle(f"The forecast misses by {m:.0f} diners a day on average; the baseline by {b:.0f}",
                 x=0.03, ha="left", fontsize=13, fontweight="bold", color="#1F2328")
    ax.set_title("65 test days, 21 September to 24 November 2026. Simulated on fictional data.", loc="left",
                 fontsize=10, color="#5F646B")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    r = evaluate()
    d = r["diners"]
    print(f"Diners MAE {d['model']['mae']:.1f} (baseline {d['baseline']['mae']:.1f}), "
          f"MAPE {d['model']['mape']:.1f}% (baseline {d['baseline']['mape']:.1f}%)")
    print("Arrival curve:", r["curve"])
    for k, v in r["dishes"].items():
        print(f"{v['name']:<18} MAE {v['model']['mae']:.2f} fixed {v['fixed_rate']['mae']:.2f} "
              f"baseline {v['baseline']['mae']:.2f}  rate {v['rate_choice']}  P80 cover {v['p80_coverage']:.0%} (trees {v['tree_p80_coverage']:.0%})")
    print("Params:", r["diners_params"], "P80 coverage diners:", f"{d['p80_coverage']:.0%} (trees {d['tree_p80_coverage']:.0%})")
    print("Demo morning:", {k: r["demo_morning"][k] for k in ("date", "diners", "diners_p80", "actual")})


if __name__ == "__main__":
    main()
