"""Phase 8 tests: the showcase morning and the presenter controls."""

import time

import pytest

from buffetiq import data_gen, showcase, state


@pytest.fixture
def live(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "CHECKINS_PATH", tmp_path / "c.csv")
    monkeypatch.setattr(state, "SERVICE_LOG_PATH", tmp_path / "log.csv")
    base = state.Service(checkins_path=tmp_path / "c.csv", log_path=tmp_path / "log.csv")
    monkeypatch.setattr(state, "_SERVICE", base)
    yield
    showcase.CLOCK.set_speed(0)


def test_showcase_row_is_82_percent_with_an_unbooked_tour_group():
    row = showcase.showcase_row().iloc[0]
    assert row["occupancy_rate"] == 0.82 and row["rooms_occupied"] == 246
    assert row["group_booking"] == 0                      # nobody told the kitchen
    arrivals = row[data_gen.ARRIVAL_COLUMNS].to_numpy()
    assert arrivals.sum() == row["diners"]
    assert arrivals[data_gen.ARRIVAL_COLUMNS.index("arr_0745")] >= showcase.TOUR_GROUP


def test_load_showcase_starts_at_0615_with_no_bookings(live):
    s = state.load_showcase()
    assert s.mode == "showcase" and s.clock.strftime("%H:%M") == "06:15" and not s.plans


def test_tour_group_alert_and_nowcast(live):
    s = state.load_showcase()
    n0 = s.n0
    s.advance_to(state.minutes("08:05"))
    e = s.kitchen()
    tour = [a for a in e.alerts if a.key == "tour-group"]
    assert tour and tour[0].title == "Tour group of 24 arrived at 07:45"
    assert e.n() > n0 + 10                                   # the nowcast caught the unbooked group
    assert not any(a.key.startswith("jump-") and a.at >= state.minutes("07:45") for a in e.alerts)


def test_reset_returns_to_0615_and_clears_bookings(live):
    s = state.load_showcase()
    s.save_plan(state.GuestPlan(service_date="", room="1204", attending=True, party=2, slot="09:30"))
    s.advance_to(state.minutes("08:00"))
    r = state.reset()
    assert r.mode == "showcase" and r.clock.strftime("%H:%M") == "06:15" and not r.plans
    assert r.kitchen().arrived() == 0


def test_jumping_back_replays_the_morning(live):
    s = state.load_showcase()
    s.advance_to(state.minutes("09:00"))
    s.replay_to("07:30")
    assert s.clock.strftime("%H:%M") == "07:30"
    assert s.kitchen().arrived() < 120


def test_the_clock_runs_at_the_chosen_speed(live):
    s = state.load_showcase()
    s.advance_to(state.minutes("07:00"))
    showcase.CLOCK.set_speed(600)                           # 10 service minutes a second, for the test
    time.sleep(2.5)
    showcase.CLOCK.set_speed(0)
    assert s.clock_minutes() >= state.minutes("07:15")


def test_a_photo_is_the_truth_for_that_tray(live):
    s = state.load_showcase()
    s.advance_to(state.minutes("08:40"))
    s.record_tray("pancakes", "low", "camera", 0.91)
    assert s.world.stock["pancakes"] == pytest.approx(0.225)
    assert s.kitchen().calls["pancakes"].action in ("cook", "hold")
