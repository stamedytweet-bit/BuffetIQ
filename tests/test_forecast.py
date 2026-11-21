"""Phase 2 tests for the night-before forecast."""

import numpy as np
import pandas as pd
import pytest

from buffetiq import data_gen, forecast
from buffetiq.state import load_config


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def history():
    return forecast.load_history()


@pytest.fixture(scope="module")
def results():
    return forecast.evaluate(write=False)


def test_hidden_columns_can_never_be_features():
    for bad in ("surprise", "checkin_response_rate", "diners", "arr_0730", "pancakes_demand_kg",
                "pancakes_consumed_kg"):
        with pytest.raises(ValueError):
            forecast.assert_no_hidden(["occupancy_rate", bad])
    forecast.assert_no_hidden(forecast.DINER_FEATURES)
    forecast.assert_no_hidden(forecast.CURVE_FEATURES)


def test_split_is_by_date_300_then_65(history, cfg):
    train, test = forecast.split(history, cfg["forecast"]["train_days"])
    assert len(train) == 300 and len(test) == 65
    assert train["date"].max() < test["date"].min()
    assert test["date"].iloc[0] == "2026-09-21" and test["date"].iloc[-1] == "2026-11-24"


def test_baseline_uses_only_the_previous_four_same_weekdays(history):
    base = forecast.same_weekday_baseline(history, "diners", 4)
    i = 100
    expected = np.mean([history["diners"].iloc[i - 7 * k] for k in range(1, 5)])
    assert base.iloc[i] == pytest.approx(expected)
    assert np.isnan(base.iloc[27])  # not enough history yet


def test_metrics_on_known_values():
    m = forecast.metrics([100, 200], [110, 190])
    assert m["mae"] == pytest.approx(10)
    assert m["rmse"] == pytest.approx(10)
    assert m["mape"] == pytest.approx(7.5)


def test_model_beats_baseline_for_diners_and_every_dish(results):
    assert results["diners"]["model"]["mae"] < results["diners"]["baseline"]["mae"]
    for dish in results["dishes"].values():
        assert dish["model"]["mae"] < dish["baseline"]["mae"], dish["name"]


def test_arrival_choice_made_on_training_days_only(results):
    sel = results["curve"]["selection_on_training_days"]
    assert sel["chosen"] in ("profile", "model")
    assert results["curve"]["chosen"] == sel["chosen"]


def test_forecast_day_is_consistent(history, cfg):
    train, test = forecast.split(history, cfg["forecast"]["train_days"])
    model = forecast.Forecaster(cfg).fit(train, tune=False)
    day = model.forecast_day(test.iloc[[-1]])
    assert len(day["slot_shares"]) == 16
    assert sum(day["slot_shares"]) == pytest.approx(1.0)
    assert min(day["slot_shares"]) >= 0
    assert sum(day["slot_diners"]) == pytest.approx(day["diners"])
    assert day["diners_p80"] >= day["diners"]
    for dish_id, amount in day["dishes"].items():
        assert day["dishes_p80"][dish_id] >= amount > 0
    assert set(day["dishes"]) == {d["id"] for d in cfg["dishes"]}


def test_shopping_list_arithmetic(cfg):
    items = forecast.shopping_list({"scrambled_eggs": 2.0, "pancakes": 1.0, "croissants": 10.4}, cfg)
    assert items["eggs_pcs"] == 2 * 18 + 3          # eggs from both dishes, whole pieces
    assert items["milk_l"] == pytest.approx(0.2 + 0.4)
    assert items["frozen_croissant_dough_pcs"] == 11  # rounded up


def test_stock_out_detection(cfg):
    eggs = next(d for d in cfg["dishes"] if d["id"] == "scrambled_eggs")
    df = pd.DataFrame({"scrambled_eggs_prepared_kg": [20.0, 20.0], "scrambled_eggs_consumed_kg": [20.0, 18.5]})
    assert forecast.stocked_out(df, eggs).tolist() == [True, False]


def test_every_dish_has_a_recipe(cfg):
    assert {d["id"] for d in cfg["dishes"]} == set(cfg["recipes"])
