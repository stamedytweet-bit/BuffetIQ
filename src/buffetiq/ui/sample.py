"""Sample data copied from the approved screenshots (fictional).

Each page renders from plain dictionaries ("view models"). In Phase 0 they come
from here; later phases build the same shapes from live state in state.py, one
screen at a time, so the look stays right while the logic arrives.
"""

from __future__ import annotations

# Level words map to colours and icons in one place (never colour alone).
LEVELS = ("Empty", "Low", "Half", "Full")

# ---------------------------------------------------------------------------
# 01 Kitchen board, Tuesday 24 November, 08:40
# ---------------------------------------------------------------------------

KITCHEN_HEADER = {
    "date_line": "Breakfast service · Tuesday 24 November · 06:30 to 10:30 · Fictional data",
    "clock": "08:40",
    "diners_so_far": 164,
    "expected": 286,
    "expected_was": 268,
    "next15_word": "Busy",
    "next15_count": 24,
}

# action kinds: "act" (cook now, saffron), "empty" (tray empty, coral), "hold" (raised dark)
# timer kinds: "ok", "warn" (3 h 30 min), "limit" (4 h, swap now), "none" (plain note)
KITCHEN_DISHES = [
    {"name": "Scrambled eggs", "station": "Hot station 1", "level": "Low", "fill_pct": 16,
     "amount": "0.4 of 2.5 kg", "action": "Cook 4 kg", "action_kind": "act",
     "action_line": "Now · ready in 8 min", "timer": "Out since 08:10 · swap by 12:10", "timer_kind": "ok"},
    {"name": "Chicken sausages", "station": "Hot station 1", "level": "Half", "fill_pct": 52,
     "amount": "1.3 of 2.5 kg", "action": "Hold", "action_kind": "hold",
     "action_line": "Next check 08:55", "timer": "Out since 07:50 · swap by 11:50", "timer_kind": "ok"},
    {"name": "Hash browns", "station": "Hot station 1", "level": "Low", "fill_pct": 20,
     "amount": "0.4 of 2.0 kg", "action": "Cook 2 kg", "action_kind": "act",
     "action_line": "Now · ready in 12 min", "timer": "Out since 08:05 · swap by 12:05", "timer_kind": "ok"},
    {"name": "Pancakes", "station": "Live station", "level": "Empty", "fill_pct": 0,
     "amount": "0 of 1.5 kg", "action": "Cook 1.5 kg", "action_kind": "empty",
     "action_line": "Now · tray empty since 08:36", "timer": "Next batch starts the timer", "timer_kind": "ok"},
    {"name": "Mee goreng", "station": "Hot station 2", "level": "Full", "fill_pct": 88,
     "amount": "2.6 of 3.0 kg", "action": "Hold", "action_kind": "hold",
     "action_line": "Next check 09:05", "timer": "Out since 08:25 · swap by 12:25", "timer_kind": "ok"},
    {"name": "Nasi lemak rice", "station": "Hot station 2", "level": "Half", "fill_pct": 60,
     "amount": "1.8 of 3.0 kg", "action": "Hold", "action_kind": "hold",
     "action_line": "Next check 09:00", "timer": "Out since 06:30 · swap by 10:30", "timer_kind": "ok"},
    {"name": "Croissants", "station": "Bakery", "level": "Half", "fill_pct": 45,
     "amount": "18 of 40 pieces", "action": "Bake 24", "action_kind": "act",
     "action_line": "Now · last bake 09:50", "timer": "Out since 07:40 · swap by 11:40", "timer_kind": "ok"},
    {"name": "Cut fruit", "station": "Cold station", "level": "Full", "fill_pct": 80,
     "amount": "4.0 of 5.0 kg", "action": "Hold", "action_kind": "hold",
     "action_line": "Next check 09:10", "timer": "Chilled display · check temperature", "timer_kind": "ok"},
]

# Card border follows the most urgent state.
for _d in KITCHEN_DISHES:
    _d["card_kind"] = _d["action_kind"] if _d["action_kind"] in ("act", "empty") else "normal"

# Bar heights in pixels (of 130) from the design snapshot; None = slot not reached yet.
KITCHEN_ARRIVALS = {
    "finding": "12% ahead of forecast",
    "start": "06:30",
    "now_label": "08:40 now",
    "end": "10:30",
    "forecast_px": [10, 19, 32, 48, 64, 77, 83, 83, 77, 77, 70, 64, 54, 45, 32, 22],
    "actual_px": [16, 29, 45, 61, 77, 122, 80, 54, 42, None, None, None, None, None, None, None],
    "current_index": 8,
}

# kinds: "stop" (coral !), "info" (teal i), "suggest" (saffron ›); newest first, at most three
KITCHEN_ALERTS = [
    {"kind": "stop", "title": "Pancakes ran out at 08:36",
     "line": "Cook 1.5 kg now. The live station has been told."},
    {"kind": "info", "title": "Tour group of 24 arrived at 07:45",
     "line": "Expected diners raised from 268 to 286."},
    {"kind": "suggest", "title": "Switch to cook-to-order from about 09:45",
     "line": "Under 12 guests per 15 minutes expected, so use smaller pans."},
]

KITCHEN_VOICE = {
    "question": "How much egg should I cook?",
    "answer": "Cook 4 kilograms of scrambled eggs now. Ready in 8 minutes.",
}

# ---------------------------------------------------------------------------
# 02 Ask BuffetIQ, 03 Tray check, 04 Tray result (runner phone, 08:40)
# ---------------------------------------------------------------------------

RUNNER_TIME = "08:40"

ASK = {
    "status": "connected",           # connected | basic | offline
    "question": "How much egg should I cook?",
    "asked_at": "08:40",
    "answer_main": "Cook 4 kg of scrambled eggs now.",
    "answer_more": "Ready in 8 minutes. Two more batches are likely before 09:30.",
    "try_asking": ["What is running low?", "Any pans near 4 hours?", "When do I stop croissants?",
                   "Which dishes have gluten?", "How much have we thrown away?"],
}

TRAY_CHECK = {
    "station": "Hot station 1",
    "dishes": ["Scrambled eggs", "Chicken sausages", "Hash browns"],
    "selected": "Scrambled eggs",
}

TRAY_RESULT = {
    "dish": "Scrambled eggs",
    "time": "08:40",
    "level": "Low",
    "confidence": 0.91,
    "estimate": "About 0.4 kg left of 2.5 kg",
    "board_call": "Scrambled eggs: cook 4 kg now",
}

# ---------------------------------------------------------------------------
# 05 to 07 Guest flow, for Wednesday 25 November
# ---------------------------------------------------------------------------

GUEST = {
    "date": "Wednesday 25 November",
    "hours": "06:30 to 10:30",
    "attending": "Yes",
    "room_placeholder": "1204",
    "party": 2,
    "halal": 0,
    "vegetarian": 0,
    # half-hour crowd view; bar widths copied from the design
    "slots": [
        {"time": "06:30", "word": "Quiet", "bar_pct": 30},
        {"time": "07:00", "word": "Moderate", "bar_pct": 62},
        {"time": "07:30", "word": "Busy", "bar_pct": 95},
        {"time": "08:00", "word": "Busy", "bar_pct": 95},
        {"time": "08:30", "word": "Busy", "bar_pct": 95},
        {"time": "09:00", "word": "Busy", "bar_pct": 95},
        {"time": "09:30", "word": "Quiet", "bar_pct": 30},
        {"time": "10:00", "word": "Quiet", "bar_pct": 30},
    ],
    "selected_slot": "09:00",
    "suggested_slot": "09:30",
    "confirmed_slot": "09:30",
    "confirmed_room": "1204",
}

# ---------------------------------------------------------------------------
# 08 Day-end report, Tuesday 24 November
# ---------------------------------------------------------------------------

REPORT = {
    "date_line": "Tuesday 24 November · Breakfast 06:30 to 10:30 · Simulated on fictional data",
    "figures": [
        {"label": "Food left over", "value": "18.6 kg", "compare": "55% less than a usual day (41.2 kg)", "good": True},
        {"label": "Cost of food wasted", "value": "S$96", "compare": "Usual day S$214", "good": True},
        {"label": "Minutes a dish was empty", "value": "6 min", "compare": "Usual day 9 min · pancakes, 08:36 to 08:42", "good": False},
        {"label": "Guests served", "value": "293", "compare": "Forecast 268 · revised to 286 at 08:40", "good": False},
    ],
    # dish, prepared kg, eaten kg, left kg, usual-day left kg
    "leftovers": [
        ("Scrambled eggs", 21.0, 19.8, 1.2, 4.8),
        ("Chicken sausages", 16.5, 14.1, 2.4, 5.1),
        ("Hash browns", 12.0, 10.2, 1.8, 3.9),
        ("Mee goreng", 18.0, 14.9, 3.1, 6.0),
        ("Nasi lemak rice", 20.0, 17.4, 2.6, 5.4),
        ("Croissants", 9.0, 7.0, 2.0, 4.6),
        ("Pancakes", 8.0, 7.1, 0.9, 2.8),
        ("Cut fruit", 24.0, 19.4, 4.6, 8.6),
    ],
    "usual_total": 41.2,
    "events": [
        {"title": "Tour group arrived early",
         "line": "24 guests at 07:45. The forecast was raised from 268 to 286 guests within one check."},
        {"title": "Pancakes ran out for 6 minutes",
         "line": "Empty from 08:36 to 08:42. The live station cooked 1.5 kg."},
        {"title": "2.1 kg offered on Treatsure",
         "line": "Mee goreng and cut fruit, flagged at 09:45."},
        {"title": "3 chef overrides",
         "line": "Two for a VIP breakfast, one for a dropped tray."},
    ],
    "learning": [("Week 1", 9.8), ("Week 2", 6.1), ("Week 3", 4.0), ("Week 4", 2.9)],
    "footnote": ("Simulated on fictional data for the prototype. The NEA file lists each day's food waste "
                 "by dish in kilograms, ready to adapt to NEA's reporting template."),
}
