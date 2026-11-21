"""Phase 3 tests: guest plans, the crowd view and how check-ins move the forecast."""

import csv
from datetime import datetime

import numpy as np
import pytest

from buffetiq import qr, state


@pytest.fixture(scope="module")
def model():
    s = state.Service(checkins_path=state.ROOT / "data" / "_test_model.csv")
    (state.ROOT / "data" / "_test_model.csv").unlink(missing_ok=True)
    return s.model


@pytest.fixture
def svc(tmp_path, model):
    return state.Service(checkins_path=tmp_path / "checkins.csv", model=model)


def plan(room="1204", attending=True, party=2, slot="09:30", halal=0, vegetarian=0):
    return state.GuestPlan(service_date="", room=room, attending=attending, party=party,
                           halal=halal, vegetarian=vegetarian, slot=slot)


def test_crowd_words_use_the_brief_thresholds():
    assert state.crowd_word(39, 100) == "Quiet"
    assert state.crowd_word(40, 100) == "Moderate"
    assert state.crowd_word(75, 100) == "Moderate"
    assert state.crowd_word(76, 100) == "Busy"


def test_crowd_view_has_eight_half_hours_adding_two_slots(svc):
    view = svc.crowd_view()
    assert [r["time"] for r in view] == ["06:30", "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "10:00"]
    per_slot = svc.expected_slots()
    assert view[0]["expected"] == pytest.approx(per_slot[0] + per_slot[1])
    assert max(r["bar_pct"] for r in view) == 100
    assert all(r["word"] in ("Quiet", "Moderate", "Busy") for r in view)


def test_expected_slots_add_up_to_expected_diners(svc):
    svc.save_plan(plan(party=3, slot="07:00"))
    assert svc.expected_slots().sum() == pytest.approx(svc.expected_diners())


def test_confirmed_guests_are_placed_in_their_half_hour(svc):
    before = svc.expected_slots()
    svc.save_plan(plan(party=8, slot="10:00"))
    after = svc.expected_slots()
    i = state.service_slots().index("10:00")
    assert after[i] + after[i + 1] > before[i] + before[i + 1] + 7   # most of the 8 land at 10:00


def test_confirmations_feed_the_diner_model_without_double_counting(svc):
    n0 = svc.expected_diners()
    for k in range(20):
        svc.save_plan(plan(room=str(1000 + k), party=2, slot="09:30"))
    n1 = svc.expected_diners()
    assert n1 >= n0 - 1e-9          # more check-ins never lower the forecast
    assert n1 < n0 + 40             # 40 confirmed guests are not simply added on top


def test_declines_lower_the_forecast(svc):
    n0 = svc.expected_diners()
    svc.save_plan(plan(room="1305", attending=False, party=4, slot=None))
    assert svc.expected_diners() == pytest.approx(n0 - 4 * svc.p_dine)


def test_change_my_plans_replaces_the_room(svc):
    svc.save_plan(plan(party=2, slot="09:00"))
    svc.save_plan(plan(party=3, slot="09:30"))
    assert len(svc.plans) == 1
    assert svc.confirmed_guests() == 3 and svc.plans["1204"].slot == "09:30"


def test_meal_counts_capped_at_party_size(svc):
    saved = svc.save_plan(plan(party=2, halal=5, vegetarian=3))
    assert saved.halal == 2 and saved.vegetarian == 2
    assert svc.dietary_counts() == {"halal": 2, "vegetarian": 2}


@pytest.mark.parametrize("room", ["", "12", "12a4", "123456", "  "])
def test_room_must_be_3_to_5_digits(svc, room):
    with pytest.raises(ValueError):
        svc.save_plan(plan(room=room))


def test_plans_survive_a_restart_and_are_deleted_after_checkout(tmp_path, model):
    path = tmp_path / "checkins.csv"
    s = state.Service(checkins_path=path, model=model)
    s.save_plan(plan())
    assert state.Service(checkins_path=path, model=model).confirmed_guests() == 2
    # a row from an earlier service date belongs to a guest who has checked out
    with open(path, "a", newline="") as fh:
        csv.writer(fh).writerow(["2026-11-20", "0999", "True", 2, 0, 0, "09:00", "2026-11-19T20:00:00"])
    state.Service(checkins_path=path, model=model)
    rooms = [r["room"] for r in csv.DictReader(open(path))]
    assert rooms == ["1204"]


def test_dietary_needs_stored_as_counts_only(svc):
    svc.save_plan(plan(halal=1))
    header = open(svc.checkins_path).readline().strip().split(",")
    assert "name" not in header and "email" not in header


def test_checkins_file_is_ignored_by_git():
    ignore = (state.ROOT / ".gitignore").read_text()
    assert "data/*" in ignore.splitlines()


def test_heading_follows_the_clock(svc):
    svc.set_clock(datetime(2026, 11, 23, 20, 0))
    assert svc.breakfast_heading() == "Breakfast tomorrow"
    assert all(r["available"] for r in svc.crowd_view())
    svc.set_clock(datetime(2026, 11, 24, 8, 40))
    assert svc.breakfast_heading() == "Breakfast this morning"
    available = [r["time"] for r in svc.crowd_view() if r["available"]]
    assert available[0] == "08:30"            # half hours that have ended cannot be chosen


def test_next_15_minutes(svc):
    svc.set_clock(datetime(2026, 11, 24, 7, 35))
    word, count = svc.next_15()
    assert word in ("Quiet", "Moderate", "Busy") and count > 0
    assert svc.current_slot_index() == 4


def test_qr_link_replaces_localhost_with_the_network_address(monkeypatch):
    monkeypatch.delenv("BUFFETIQ_PUBLIC_URL", raising=False)
    monkeypatch.setattr(qr, "lan_ip", lambda: "192.168.1.20")
    assert qr.guest_url("127.0.0.1:7860") == "http://192.168.1.20:7860/guest"
    assert qr.guest_url("abc123.gradio.live", "https") == "https://abc123.gradio.live/guest"
    monkeypatch.setenv("BUFFETIQ_PUBLIC_URL", "https://example.test/")
    assert qr.guest_url("127.0.0.1:7860") == "https://example.test/guest"


def test_qr_sleeve_is_key_card_size(tmp_path):
    from PIL import Image

    path = qr.sleeve("http://192.168.1.20:7860/guest", tmp_path / "sleeve.png")
    w, h = Image.open(path).size
    assert (w, h) == (1004, 650)     # 85 x 55 mm at 300 dpi
