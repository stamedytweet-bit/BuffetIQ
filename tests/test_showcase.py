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


# ---- presenter passcode ----

from buffetiq.ui import about as about_page  # noqa: E402


@pytest.fixture
def no_space(monkeypatch):
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("BUFFETIQ_PASSCODE", raising=False)


def test_controls_are_open_on_the_laptop_without_a_passcode(no_space):
    assert not about_page.passcode_required() and about_page.new_session()["open"]


def test_a_space_without_a_passcode_stays_locked(no_space, monkeypatch):
    monkeypatch.setenv("SPACE_ID", "someone/buffetiq")
    session = about_page.new_session()
    assert about_page.passcode_required() and not session["open"]
    session, msg = about_page.try_passcode(session, "anything")
    assert not session["open"] and "BUFFETIQ_PASSCODE" in msg


def test_right_passcode_unlocks_and_wrong_one_does_not(no_space, monkeypatch):
    monkeypatch.setenv("BUFFETIQ_PASSCODE", "kaya toast 42")
    session = about_page.new_session()
    assert not session["open"]
    session, msg = about_page.try_passcode(session, "kaya toast")
    assert not session["open"] and "not right" in msg
    session, msg = about_page.try_passcode(session, " kaya toast 42 ")
    assert session["open"] and msg == ""


def test_five_wrong_tries_lock_the_box_for_a_minute(no_space, monkeypatch):
    monkeypatch.setenv("BUFFETIQ_PASSCODE", "kaya toast 42")
    session = about_page.new_session()
    for _ in range(about_page.MAX_TRIES):
        session, msg = about_page.try_passcode(session, "guess", now=1000.0)
    assert "Wait 60 seconds" in msg
    session, msg = about_page.try_passcode(session, "kaya toast 42", now=1030.0)
    assert not session["open"] and "Wait" in msg
    session, msg = about_page.try_passcode(session, "kaya toast 42", now=1061.0)
    assert session["open"]


def test_start_breakfast_opens_at_0630_and_runs_live(live):
    s = state.load_showcase()
    assert showcase.can_start()
    showcase.start_breakfast()
    assert s.clock.strftime("%H:%M") == showcase.LIVE_START == "06:30" and showcase.CLOCK.speed == 1
    assert not showcase.can_start()                       # the board now offers Restart
    showcase.CLOCK.set_speed(0)
    s.advance_to(state.minutes("08:40"))
    showcase.start_breakfast()                            # a later clock is never wound back
    assert s.clock.strftime("%H:%M") == "08:40"


def test_after_start_only_logged_diners_count(live):
    s = state.load_showcase()
    showcase.start_breakfast()
    showcase.CLOCK.set_speed(0)
    s.log_arrivals(5)
    s.log_arrivals(2)
    s.advance_to(state.minutes("08:15"))                  # past the tour group's slot
    assert s.kitchen().arrivals.sum() == 7                # nobody added by the simulation
    assert not any(a.key == "tour-group" for a in s.kitchen().alerts)


def test_restart_goes_back_to_0615_stopped_with_no_arrivals(live):
    s = state.load_showcase()
    showcase.start_breakfast()
    s.log_arrivals(5)
    showcase.restart_morning()
    s = state.service()
    assert s.clock.strftime("%H:%M") == "06:15" and showcase.CLOCK.speed == 0 and showcase.can_start()
    assert s.mode == "showcase"


def test_board_start_button_needs_a_second_tap_to_restart(live):
    from buffetiq.ui import kitchen

    state.load_showcase()
    assert kitchen.start_button(0.0)["value"] == "Start breakfast"
    showcase.start_breakfast()
    assert kitchen.start_button(0.0)["value"] == "Restart"
    assert kitchen.start_button(time.time() + 5)["value"] == "Tap again to restart"
    assert kitchen.start_button(time.time() - 1)["value"] == "Restart"   # the second tap came too late
