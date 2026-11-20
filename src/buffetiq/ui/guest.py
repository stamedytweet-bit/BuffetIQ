"""Guest flow, page "/guest" (screens 05 to 07), opened from the QR code.

Light mode, no navbar, so guests never see kitchen pages. Three steps are three
gr.Columns whose visibility is switched. Phase 0 shows the forecast crowd view
from sample data and moves between the steps; Phase 3 saves check-ins to shared
state and feeds them into the forecast.
"""

from __future__ import annotations

import gradio as gr

from buffetiq import state
from buffetiq.style import GUEST, check_copy, esc, icon
from buffetiq.ui import sample

CROWD = {
    # word: (bar colour, word colour)
    "Quiet": (GUEST["crowd-quiet"], GUEST["crowd-word"]),
    "Moderate": (GUEST["crowd-moderate"], GUEST["crowd-word"]),
    "Busy": (GUEST["crowd-busy"], GUEST["teal-dark"]),
}
MAX_PARTY = 8


def render_head(step: str | None) -> str:
    h = state.hotel()
    pill = f'<span class="g-step">{esc(step)}</span>' if step else ""
    return check_copy(f'<header class="g-head"><span class="g-hotel">{esc(h["name"])}</span>{pill}</header>')


def render_intro(date: str, hours: str) -> str:
    h = state.hotel()
    return check_copy(f"""
<div class="g-title">
  <h1>Breakfast tomorrow</h1>
  <p>{esc(date)} · {esc(hours)} at {esc(h['restaurant'])}. Tell us your plans and we will prepare just the right amount, fresh.</p>
</div>""")


def render_count(n: int) -> str:
    return f'<span class="count" aria-live="polite">{n}</span>'


def render_slot_style(slots: list[dict]) -> str:
    """Per-row bar width, bar colour and crowd word for the time-slot radio group.

    The word is drawn after the time with CSS so each row reads "09:00 ... Busy";
    the bar length and colour repeat the word, never replace it.
    """
    rules = []
    for i, s in enumerate(slots, start=1):
        bar, word_colour = CROWD[s["word"]]
        rules.append(
            f'#g-slots label:nth-of-type({i}){{--w:{s["bar_pct"]}%;--c:{bar};--wc:{word_colour};--word:"{s["word"]}"}}'
        )
    return "<style>" + "".join(rules) + "</style>"


def nearest_quiet(slots: list[dict], chosen: str) -> str | None:
    """The Quiet half hour closest to the chosen one (earlier wins a tie)."""
    times = [s["time"] for s in slots]
    if chosen not in times:
        return None
    i = times.index(chosen)
    quiet = [j for j, s in enumerate(slots) if s["word"] == "Quiet"]
    if not quiet:
        return None
    best = min(quiet, key=lambda j: (abs(j - i), j))
    return times[best]


def render_tip(slot: str) -> str:
    return check_copy(
        f'<div class="txt"><span class="t">{esc(slot)} is usually quiet</span>'
        f'<span class="b">Shorter queues and dishes straight from the kitchen.</span></div>'
    )


def confirm_label(slot: str, party: int) -> str:
    return f"Confirm {slot} for {party} guest{'s' if party != 1 else ''}"


def render_confirmed(date: str, slot: str, party: int, room: str) -> str:
    h = state.hotel()
    guests = f"{party} guest{'s' if party != 1 else ''}"
    room_part = f" · Room {esc(room)}" if room else ""
    teal = GUEST["teal"]
    return check_copy(f"""
<div class="g-done">
  <span class="circle">{icon('tick', 34, 2.6)}</span>
  <h1>You're all set</h1>
  <p>We look forward to seeing you tomorrow.</p>
</div>
<section class="g-details" aria-label="Your breakfast" style="margin-top:18px">
  <div class="item">{icon('calendar', 22, 2, teal)}<div class="txt"><span class="k">When</span><span class="v">{esc(date)}, {esc(slot)}</span></div></div>
  <div class="item">{icon('users', 22, 2, teal)}<div class="txt"><span class="k">Guests</span><span class="v">{guests}{room_part}</span></div></div>
  <div class="item">{icon('pin', 22, 2, teal)}<div class="txt"><span class="k">Where</span><span class="v">{esc(h['restaurant'])}, {esc(h['level'])}</span></div></div>
</section>""")


TIP_SMALL_PLATE = check_copy("""
<section class="g-tip big" aria-label="Breakfast tip">
  <div class="txt"><span class="t">A small plate, as often as you like</span>
  <span class="b">The buffet is topped up with fresh batches all morning, so start small and come back for more.</span></div>
</section>""")


def _stepper(label: str, prefix: str, value: int, diet: bool, plus_on: bool = False):
    with gr.Row(elem_classes=["g-stepper"] + (["diet"] if diet else [])):
        gr.HTML(f'<span class="lbl" id="{prefix}-label">{esc(label)}</span>')
        minus = gr.Button("−", elem_id=f"{prefix}-minus", elem_classes=["bq-btn", "g-step-btn"])
        count = gr.HTML(render_count(value))
        plus = gr.Button("+", elem_id=f"{prefix}-plus", elem_classes=["bq-btn", "g-step-btn"] + (["on"] if plus_on else []))
    return minus, count, plus


def build_page() -> dict:
    g = sample.GUEST
    slots = g["slots"]
    gr.Navbar(visible=False)
    party = gr.State(g["party"])
    halal = gr.State(g["halal"])
    veg = gr.State(g["vegetarian"])

    with gr.Column(elem_classes=["bq-page", "bq-guest", "bq-phone"], elem_id="g-root"):
        # ---- 05 Breakfast plan ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-18"]) as step1:
            gr.HTML(render_head("Step 1 of 2"))
            gr.HTML(render_intro(g["date"], g["hours"]))
            with gr.Column(elem_classes=["g-card"]):
                with gr.Column():
                    gr.HTML('<span class="g-q" aria-hidden="true">Will you join us?</span>')
                    attending = gr.Radio(["Yes", "Not this time"], value=g["attending"], label="Will you join us?",
                                         show_label=False, container=False, interactive=True, elem_classes=["g-toggle"])
                room = gr.Textbox(label="Room number", placeholder=g["room_placeholder"], lines=1, max_lines=1,
                                  container=True, show_label=True, elem_id="g-room", elem_classes=["g-room"])
                p_minus, p_count, p_plus = _stepper("How many guests?", "g-party", g["party"], diet=False, plus_on=True)
                with gr.Column(elem_classes=["g-diet"]):
                    gr.HTML('<span class="g-q">Dietary needs <span class="opt">(optional)</span></span>')
                    h_minus, h_count, h_plus = _stepper("Halal meals", "g-halal", g["halal"], diet=True)
                    v_minus, v_count, v_plus = _stepper("Vegetarian meals", "g-veg", g["vegetarian"], diet=True)
            gr.HTML("", elem_classes=["bq-spacer"])
            choose_btn = gr.Button("Choose a time", elem_classes=["bq-btn", "g-primary"])
            gr.HTML('<p class="g-privacy">We use your room number only to plan how much food to prepare, '
                    "and delete it when you check out.</p>")

        # ---- 06 Choose a time ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-14"], visible=False) as step2:
            with gr.Row(elem_classes=["bq-between", "g-head"]):
                back_btn = gr.Button("Back", elem_classes=["bq-btn", "g-back", "bq-ico-chevron-left"])
                gr.HTML('<span class="g-step">Step 2 of 2</span>')
            # the slot styles travel with the title so they add no extra gap
            gr.HTML('<div class="g-title" style="gap:4px"><h1 class="t30">When would you like to come?</h1>'
                    "<p class=\"small\">How busy each half hour usually is, based on tomorrow's bookings.</p></div>"
                    + render_slot_style(slots))
            slot = gr.Radio([s["time"] for s in slots], value=g["selected_slot"], label="Breakfast time",
                            show_label=False, container=False, interactive=True, elem_id="g-slots",
                            elem_classes=["g-slots"])
            first_tip = nearest_quiet(slots, g["selected_slot"])
            with gr.Column(elem_classes=["g-tip"], visible=first_tip is not None) as tip_box:
                tip_text = gr.HTML(render_tip(first_tip or ""))
                switch_btn = gr.Button(f"Switch to {first_tip}", elem_classes=["bq-btn", "g-tip-btn"])
            gr.HTML("", elem_classes=["bq-spacer"])
            confirm_btn = gr.Button(confirm_label(g["selected_slot"], g["party"]), elem_classes=["bq-btn", "g-primary"])

        # ---- 07 Confirmed ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-18"], visible=False) as step3:
            gr.HTML(render_head(None))
            confirmed = gr.HTML(render_confirmed(g["date"], g["confirmed_slot"], g["party"], g["confirmed_room"]))
            gr.HTML(TIP_SMALL_PLATE)
            gr.HTML('<p class="g-quiet">Planning ahead helps our kitchen cook fresh and waste less food.</p>')
            gr.HTML("", elem_classes=["bq-spacer"])
            change_btn = gr.Button("Change my plans", elem_classes=["bq-btn", "g-secondary"])

        gr.HTML('<p class="bq-note">Prototype · Fictional data</p>')

    # ---- Phase 0 wiring: steppers and moving between steps (no saving yet) ----
    def bump(n, delta, lo, hi):
        return max(lo, min(hi, n + delta))

    def set_party(p, h, v, delta):
        p = bump(p, delta, 1, MAX_PARTY)
        h, v = min(h, p), min(v, p)   # meal counts are capped at the party size
        return p, h, v, render_count(p), render_count(h), render_count(v)

    party_out = [party, halal, veg, p_count, h_count, v_count]
    p_minus.click(lambda p, h, v: set_party(p, h, v, -1), [party, halal, veg], party_out)
    p_plus.click(lambda p, h, v: set_party(p, h, v, +1), [party, halal, veg], party_out)
    for minus, plus, st, cnt in ((h_minus, h_plus, halal, h_count), (v_minus, v_plus, veg, v_count)):
        minus.click(lambda n, p: (bump(n, -1, 0, p), render_count(bump(n, -1, 0, p))), [st, party], [st, cnt])
        plus.click(lambda n, p: (bump(n, +1, 0, p), render_count(bump(n, +1, 0, p))), [st, party], [st, cnt])

    def on_slot(s, p):
        word = next(x["word"] for x in slots if x["time"] == s)
        tip = nearest_quiet(slots, s) if word == "Busy" else None
        return (gr.update(visible=tip is not None), render_tip(tip or ""),
                gr.update(value=f"Switch to {tip}"), gr.update(value=confirm_label(s, p)))

    slot.change(on_slot, [slot, party], [tip_box, tip_text, switch_btn, confirm_btn])
    switch_btn.click(lambda s: nearest_quiet(slots, s), slot, slot)

    def go_times(p, s):
        return gr.update(visible=False), gr.update(visible=True), gr.update(value=confirm_label(s, p))

    choose_btn.click(go_times, [party, slot], [step1, step2, confirm_btn])
    back_btn.click(lambda: (gr.update(visible=True), gr.update(visible=False)), None, [step1, step2])

    def do_confirm(s, p, r):
        return (gr.update(visible=False), gr.update(visible=True),
                render_confirmed(g["date"], s, p, (r or "").strip()))

    confirm_btn.click(do_confirm, [slot, party, room], [step2, step3, confirmed])
    change_btn.click(lambda: (gr.update(visible=True), gr.update(visible=False)), None, [step1, step3])

    return {"attending": attending, "room": room, "slot": slot, "confirm": confirm_btn}
