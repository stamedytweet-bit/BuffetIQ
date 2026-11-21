"""Phase 1 sanity tests for the synthetic breakfast history."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from buffetiq import data_gen
from buffetiq.state import load_config

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "data" / "synthetic_breakfast.csv"
# Recorded in docs/EVIDENCE.md when the data was frozen, before Phase 2.
FROZEN_SHA256 = "86846b20aca06899e35f41c1546282924d0ccd92a01cb5f8f375dc1df7497022"


@pytest.fixture(scope="module")
def df():
    return data_gen.generate()


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def test_frozen_file_is_unchanged():
    assert data_gen.file_sha256(FROZEN) == FROZEN_SHA256, "the frozen data must not change after Phase 1"


def test_generation_is_deterministic(df):
    again = data_gen.generate()
    pd.testing.assert_frame_equal(df, again)


def test_365_days_ending_on_the_demo_morning(df):
    assert len(df) == 365
    assert df["date"].iloc[0] == "2025-11-25"
    assert df["date"].iloc[-1] == "2026-11-24"
    assert df["day_of_week"].iloc[-1] == "Tue"
    assert df["date"].is_unique


def test_no_negative_numbers(df):
    numeric = df.select_dtypes("number")
    assert (numeric >= 0).all().all()


def test_arrivals_sum_to_diners(df):
    assert len(data_gen.ARRIVAL_COLUMNS) == 16
    assert (df[data_gen.ARRIVAL_COLUMNS].sum(axis=1) == df["diners"]).all()


def test_leftover_equals_prepared_minus_consumed(df, cfg):
    for dish in cfg["dishes"]:
        c = data_gen.dish_columns(dish)
        assert np.allclose(df[c["leftover"]], df[c["prepared"]] - df[c["consumed"]], atol=0.011), dish["id"]
        assert (df[c["consumed"]] <= df[c["prepared"]] + 1e-9).all(), dish["id"]
        assert (df[c["consumed"]] <= df[c["demand"]] + 1e-9).all(), dish["id"]


def test_prepared_is_whole_batches(df, cfg):
    for dish in cfg["dishes"]:
        col = data_gen.dish_columns(dish)["prepared"]
        batches = df[col] / dish["batch"]
        assert np.allclose(batches, batches.round(), atol=1e-6), dish["id"]


def test_diners_fit_the_hotel(df):
    assert (df["rooms_occupied"] <= 300).all()
    assert (df["breakfast_inclusive_rooms"] <= df["rooms_occupied"]).all()
    assert (df["diners"] <= df["adults"] + df["children"] + 31).all()  # 31 = largest surprise tour party


def test_check_in_response_never_above_40_percent(df):
    assert df["checkin_response_rate"].between(0, 0.40).all()
    assert (df["check_ins"] <= df["diners"] * 1.06 + 1).all()


def test_monthly_occupancy_follows_stb(df, cfg):
    month = df["date"].str[:7]
    means = df.groupby(month)["occupancy_rate"].mean() * 100
    for m, value in means.items():
        if m in ("2025-11",):   # only 6 days of this month are in range
            continue
        assert abs(value - cfg["simulation"]["monthly_occupancy"][m]) < 1.0, m


def test_breakfast_inclusive_share_near_hotel_booking_demand(df):
    share = (df["breakfast_inclusive_rooms"] / df["rooms_occupied"]).mean()
    assert 0.74 < share < 0.82


def _peak_slot(df, mask):
    totals = df.loc[mask, data_gen.ARRIVAL_COLUMNS].sum()
    return totals.idxmax()


def test_weekday_peak_between_0700_and_0800(df):
    weekday = ~(df["is_weekend"] | df["public_holiday"])
    assert _peak_slot(df, weekday) in {"arr_0700", "arr_0715", "arr_0730", "arr_0745"}


def test_weekend_peak_between_0830_and_0930(df):
    weekend = df["is_weekend"] | df["public_holiday"]
    assert _peak_slot(df, weekend) in {"arr_0830", "arr_0845", "arr_0900", "arr_0915"}


def test_children_raise_pancake_demand(df):
    per_diner = df["pancakes_demand_kg"] / df["diners"]
    child_share = df["children"] / (df["adults"] + df["children"])
    assert np.corrcoef(child_share, per_diner)[0, 1] > 0.3


def test_surprises_about_one_day_in_fifteen(df):
    rate = (df["surprise"] != "none").mean()
    assert 0.03 < rate < 0.11


def test_public_and_school_holidays_flagged(df):
    assert df.loc[df["date"] == "2026-08-10", "public_holiday"].item()
    assert df.loc[df["date"] == "2026-06-15", "school_holiday"].item()
    assert not df.loc[df["date"] == "2026-11-24", "public_holiday"].item()
    assert df["public_holiday"].sum() == 11


def test_hidden_columns_are_listed(df):
    hidden = data_gen.hidden_columns(df)
    assert "surprise" in hidden and "checkin_response_rate" in hidden
    assert sum(c.endswith(("_demand_kg", "_demand_pcs")) for c in hidden) == 8
