"""Phase 7 tests: day-end report, history, NEA file and retraining."""

import csv

import pandas as pd
import pytest

from buffetiq import forecast, reports, state
from buffetiq.style import EM_DASH


@pytest.fixture
def svc(tmp_path, monkeypatch):
    s = state.Service(checkins_path=tmp_path / "c.csv", log_path=tmp_path / "log.csv")
    monkeypatch.setattr(state, "_SERVICE", s)
    monkeypatch.setattr(reports, "LOGGED_DAYS_PATH", tmp_path / "service_days.csv")
    monkeypatch.setattr(reports, "NEA_PATH", tmp_path / "nea.csv")
    monkeypatch.setattr(reports, "RETRAIN_PATH", tmp_path / "retrain.json")
    monkeypatch.setattr(forecast, "MODEL_PATH", tmp_path / "forecast.joblib")
    s.replay_to("08:40")
    return s


def test_report_balances_and_leaves_the_board_alone(svc):
    r = reports.build(svc)
    assert svc.clock.strftime("%H:%M") == "08:40"          # finished on a copy, not the live service
    for row in r["rows"]:
        assert row["prepared"] == pytest.approx(row["eaten"] + row["left"])
        assert row["left"] >= 0 and row["usual_left"] >= 0
    assert r["left_total"] == pytest.approx(sum(x["left"] for x in r["rows"]))
    assert r["diners"] == 291 and len(r["events"]) <= 4


def test_recorded_leftovers_win_and_discards_count(svc):
    base = {x["id"]: x["left"] for x in reports.build(svc)["rows"]}
    svc.record_tray("cut_fruit", "half", "manual", leftover=True)        # 2.5 kg recorded at close
    svc.override("mee_goreng", "discard", "Pan reached 4 hours")
    rows = {x["id"]: x for x in reports.build(svc)["rows"]}
    assert rows["cut_fruit"]["left"] == pytest.approx(2.5) and rows["cut_fruit"]["recorded"]
    assert rows["mee_goreng"]["left"] >= base["mee_goreng"]


def test_report_view_text(svc):
    from buffetiq.ui import report

    v = report.report_view()
    assert v["date_line"].endswith("Simulated on fictional data")
    assert [f["label"] for f in v["figures"]] == ["Food left over", "Cost of food wasted",
                                                  "Minutes a dish was empty", "Guests served"]
    html = report.render_body(v)
    assert EM_DASH not in html and "a usual day" in html


def test_learning_curve_falls_with_more_history():
    curve = reports.learning_curve()
    assert [label for label, _ in curve] == ["1 month", "2 months", "3 months", "10 months"]
    assert curve[-1][1] < curve[0][1]


def test_logged_day_replaces_the_synthetic_row(svc):
    reports.log_day(svc)
    hist = reports.history_with_logged()
    assert (hist["date"] == "2026-11-24").sum() == 1
    logged = pd.read_csv(reports.LOGGED_DAYS_PATH)
    assert logged["date"].tolist() == ["2026-11-24"]


def test_nea_file_has_every_day_and_dish(svc):
    reports.log_day(svc)
    path = reports.nea_csv()
    rows = list(csv.DictReader(open(path)))
    assert len(rows) == 365 * 8
    assert set(rows[0]) == {"date", "dish", "food_waste_kg", "source"}
    today = [r for r in rows if r["date"] == "2026-11-24"]
    assert len(today) == 8 and all(r["source"].startswith("logged service") for r in today)
    assert all(float(r["food_waste_kg"]) >= 0 for r in rows)


def test_retraining_changes_tomorrows_forecast(svc):
    st = reports.retrain(svc)
    assert st["tomorrow"] == "2026-11-25" and st["days"] == 365
    assert st["after"] != st["before"]                      # today's service changes the next forecast
    assert forecast.MODEL_PATH.exists()
    assert "retrain" in open(svc.log_path).read()


def test_engine_actions_are_logged(svc):
    svc.kitchen()
    actions = {r["action"] for r in csv.DictReader(open(svc.log_path))}
    assert "cook" in actions and "batch_out" in actions
