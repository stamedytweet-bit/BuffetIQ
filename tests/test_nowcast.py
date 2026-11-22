"""Phase 5 tests: nowcast, refill rule, pan timer, engine, replay and live board."""

import random

import numpy as np
import pytest

from buffetiq import nowcast, simulate, state
from buffetiq.nowcast import SERVICE_START, Engine, hhmm

FLAT = [1 / 16] * 16
RULES = state.load_config()["rules"]


def at(text):
    h, m = text.split(":")
    return int(h) * 60 + int(m)


# ---- nowcast ----

def test_cumulative_share_runs_from_0_to_1():
    assert nowcast.cumulative_share(FLAT, at("06:30")) == 0
    assert nowcast.cumulative_share(FLAT, at("08:30")) == pytest.approx(0.5)
    assert nowcast.cumulative_share(FLAT, at("06:30") + 7.5) == pytest.approx(1 / 32)   # half of the first slot
    assert nowcast.cumulative_share(FLAT, at("10:30")) == 1


def test_zero_arrivals_keep_the_forecast_early_on():
    assert nowcast.nowcast(0, 0.0, 268) == 268
    assert nowcast.nowcast(0, 0.04, 268) == 268          # below F = 0.05
    assert nowcast.nowcast(0, 0.5, 268) == pytest.approx(134)   # half the morning gone and nobody came


def test_nowcast_formula():
    # N = w A / F + (1 - w) N0 with w = F
    assert nowcast.nowcast(150, 0.5, 268) == pytest.approx(0.5 * 150 / 0.5 + 0.5 * 268)
    assert nowcast.nowcast(120, 0.4, 268) == pytest.approx(120 + 0.6 * 268)
    assert nowcast.nowcast(300, 0.9, 268) >= 300          # never below diners already in


def test_remaining_arrivals_use_guests_still_to_come_after_now():
    # regression: late slots once looked hugely busy because the share was taken from the slot, not from now
    total = sum(nowcast.remaining_between(200, 0, FLAT, s, s + 15, now=at("06:30")) for s in range(at("06:30"), at("10:30"), 15))
    assert total == pytest.approx(200)
    last = nowcast.remaining_between(200, 0, FLAT, at("10:15"), at("10:30"), now=at("06:30"))
    assert last == pytest.approx(200 / 16)


# ---- refill rule ----

def call(**kw):
    base = dict(now=at("08:00"), n=268, arrived=134, shares=FLAT, rate=0.07, stock=0.4, cooking=0.0, buffer=0.10,
                batch=1.0, lead=8, last_cook=at("10:15"), check=15, cover=45)
    base.update(kw)
    return nowcast.refill_call(**base)


def test_refill_rounds_up_to_whole_batches():
    c = call()
    assert c.action == "cook"
    assert c.amount == pytest.approx(round(c.amount))      # whole 1 kg batches
    assert nowcast.round_up(2.01, 1.25) == 2.5
    assert nowcast.round_up(0, 1.0) == 0
    assert nowcast.remaining_need(268, 134, 0.07, 0.4, 0.0, 0.10, 1.0) == 10.0   # 1.1 x 134 x 0.07 - 0.4 = 9.9


def test_no_need_means_hold():
    c = call(stock=20.0)
    assert c.action == "hold" and c.line == "Next check 08:15"


def test_lead_time_cut_off_lets_it_run_down():
    c = call(now=at("09:35"), lead=20, last_cook=at("09:50"))       # ready 09:55, after the 09:50 last bake
    assert c.action == "run_down" and "09:50" in c.line
    c = call(now=at("09:30"), lead=20, last_cook=at("09:50"))       # ready exactly at 09:50
    assert c.action == "cook"


def test_enough_stock_for_now_holds_until_next_check():
    c = call(stock=3.0)        # need later in the morning, but 3 kg lasts beyond lead time + one check
    assert c.action == "hold"


def test_cook_amount_never_exceeds_remaining_need():
    c = call(now=at("10:10"), arrived=265, stock=0.0, last_cook=at("10:15"), lead=5)
    need = nowcast.remaining_need(268, 265, 0.07, 0.0, 0.0, 0.10, 1.0)
    assert c.action == "cook" and c.amount <= need


# ---- pan timer ----

@pytest.mark.parametrize("held,kind", [(0, "ok"), (209, "ok"), (210, "warn"), (239, "warn"), (240, "limit"), (300, "limit")])
def test_pan_timer_thresholds(held, kind):
    status, text = nowcast.pan_status(at("06:30"), at("06:30") + held)
    assert status == kind
    if kind == "limit":
        assert text.endswith("Swap now")
    else:
        assert "swap by 10:30" in text


def test_pan_timer_before_any_batch():
    assert nowcast.pan_status(None, at("07:00")) == ("ok", "Next batch starts the timer")


# ---- cook-to-order and the engine ----

def test_cook_to_order_switch_time():
    shares = np.array([0.02, 0.04, 0.07, 0.10, 0.12, 0.12, 0.11, 0.10, 0.09, 0.07, 0.06, 0.04, 0.03, 0.015, 0.01, 0.005])
    start = nowcast.cook_to_order_from(268, 0, shares, at("06:30"), 12)
    assert start is not None and hhmm(start) >= "09:15"
    assert nowcast.cook_to_order_from(2000, 0, FLAT, at("06:30"), 12) is None


def engine():
    cfg = state.load_config()
    rates = {d["id"]: (0.4 if d["unit"] == "pieces" else 0.05) for d in cfg["dishes"]}
    return Engine(dishes=cfg["dishes"], rules=cfg["rules"], n0=268, shares=FLAT, rates=rates)


def test_engine_opens_with_full_pans_and_follows_calls():
    e = engine()
    e.step(SERVICE_START)
    assert e.stock["scrambled_eggs"] == 2.5 and e.out_at["scrambled_eggs"] == SERVICE_START
    e.tray_check("scrambled_eggs", 0.0, "empty", at("07:00"))
    e.step(at("07:00"))
    c = e.calls["scrambled_eggs"]
    assert c.action == "cook" and "tray empty since 07:00" in c.line
    assert len(e.batches_for("scrambled_eggs")) == 1          # the call is assumed to be followed
    e.step(at("07:05"))
    assert len(e.batches_for("scrambled_eggs")) == 1          # and not asked for twice
    e.step(at("07:10"))                                        # 8-minute lead time has passed
    assert not e.batches_for("scrambled_eggs") and e.stock["scrambled_eggs"] > 0
    assert e.out_at["scrambled_eggs"] == at("07:08")          # the timer restarts when the batch goes out


def test_empty_tray_raises_a_stop_alert():
    e = engine()
    e.step(SERVICE_START)
    e.tray_check("pancakes", 0.0, "empty", at("08:36"))
    e.step(at("08:40"))
    assert any(a.kind == "stop" and a.title == "Pancakes ran out at 08:36" for a in e.alerts)


def test_override_and_discard():
    e = engine()
    e.step(SERVICE_START)
    e.override("mee_goreng", "hold", "VIP or event breakfast", at("07:00"))
    e.step(at("07:05"))
    assert e.calls["mee_goreng"].action == "hold" and "Chef override" in e.calls["mee_goreng"].line
    e.step(at("07:31"))                                        # overrides stand for 30 minutes
    assert "Chef override" not in e.calls["mee_goreng"].line
    e.override("nasi_lemak_rice", "discard", "Pan reached 4 hours", at("07:40"))
    assert e.stock["nasi_lemak_rice"] == 0
    assert any(x[1] == "discard" and x[3] == 3.0 for x in e.log)


def test_treatsure_flag_in_the_last_hour_only():
    e = engine()
    e.step(SERVICE_START)
    e.arrivals[:] = 268 / 16 * 0                               # nobody came, so plenty is left
    e.step(at("09:00"))
    assert not any(a.key.startswith("treat-") for a in e.alerts)
    e.step(at("09:30"))
    assert any(a.key.startswith("treat-") for a in e.alerts)


# ---- the replay ----

def test_camera_reading_is_right_or_one_level_off():
    rng = random.Random(1)
    reads = [simulate.camera_reading("half", 0.85, rng) for _ in range(2000)]
    assert set(reads) <= {"low", "half", "full"}
    assert 0.82 < reads.count("half") / 2000 < 0.88


def test_shift_arrivals_keeps_the_total():
    arr = np.array([5, 10, 20, 30, 40, 40, 35, 30, 25, 20, 15, 10, 8, 5, 3, 2], float)
    moved = simulate.shift_arrivals(arr, arr, 0.2)
    assert moved.sum() == pytest.approx(arr.sum())
    # 07:30 and 08:00 are Busy; their nearest Quiet half hours are 06:30 and 09:00
    assert moved[4] < arr[4] and moved[0] > arr[0] and moved[10] > arr[10]


def test_replay_balances_food():
    cfg = state.load_config()
    dishes = cfg["dishes"]
    demand = {d["id"]: (100 if d["unit"] == "pieces" else 15.0) for d in dishes}
    arrivals = np.full(16, 280 / 16)
    day = {"demand": demand, "arrivals": arrivals, "planned": {d["id"]: demand[d["id"]] * 1.15 for d in dishes}}
    r = simulate.run_scheduled(day, day["planned"], np.full(16, 1 / 16), cfg)
    for d in dishes:
        did = d["id"]
        assert r.prepared[did] == pytest.approx(r.served[did] + r.left[did])   # nothing appears or vanishes
        assert r.served[did] + r.unmet[did] == pytest.approx(demand[did])


def test_buffetiq_cuts_surplus_without_adding_stock_outs():
    import json

    res = json.loads((state.ROOT / "docs" / "phase5_results.json").read_text())["policies"]
    assert res["buffetiq"]["left_kg"] < res["baseline"]["left_kg"]
    assert res["buffetiq"]["empty_minutes"] <= res["baseline"]["empty_minutes"]


# ---- the live board ----

@pytest.fixture
def live(tmp_path, monkeypatch):
    s = state.Service(checkins_path=tmp_path / "c.csv", log_path=tmp_path / "log.csv")
    monkeypatch.setattr(state, "_SERVICE", s)
    return s


def test_replay_to_puts_the_board_mid_service(live):
    from buffetiq.ui import kitchen

    live.replay_to("08:40")
    h = kitchen.live_header()
    assert h["clock"] == "08:40" and h["diners_so_far"] > 100
    cards = kitchen.live_dishes()
    assert [c["name"] for c in cards] == state.dish_names()           # fixed order, never re-sorted
    for c in cards:
        assert c["level"] in ("Empty", "Low", "Half", "Full") and c["action"]
    a = kitchen.live_arrivals()
    assert a["now_label"] == "08:40 now" and a["actual_px"][a["current_index"]] is not None
    assert len(kitchen.live_alerts()) <= 3


def test_log_arrivals_and_override_are_logged(live):
    import csv

    live.replay_to("07:30")
    before = live.kitchen().arrived()
    live.log_arrivals(5)
    assert live.kitchen().arrived() == pytest.approx(before + 5)
    live.override("croissants", "run_down", "Quality problem")
    rows = [r for r in csv.DictReader(open(live.log_path)) if r["action"] in ("arrivals", "override")]
    assert [r["action"] for r in rows] == ["arrivals", "override"]
    assert rows[1]["note"] == "run_down: Quality problem"
