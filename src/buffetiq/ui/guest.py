"""Guest flow, page "/guest" (screens 05 to 07), opened from the QR code.

Light mode, no navbar, so guests never see kitchen pages. Three steps are three
gr.Columns whose visibility is switched. The crowd view comes from the live
forecast in state.py, and confirming saves the plan to shared state, so the
kitchen board's forecast changes within one refresh (5 seconds).

Dietary needs are stored as counts only, and the room number stays on this
laptop (see state.py).
"""

from __future__ import annotations

import gradio as gr

from buffetiq import state
from buffetiq.style import GUEST, check_copy, esc, icon

CROWD = {
    # word: (bar colour, word colour)
    "Quiet": (GUEST["crowd-quiet"], GUEST["crowd-word"]),
    "Moderate": (GUEST["crowd-moderate"], GUEST["crowd-word"]),
    "Busy": (GUEST["crowd-busy"], GUEST["teal-dark"]),
}
MAX_PARTY = 8
ROOM_ERROR = "Enter your room number, such as 1204, so we can plan for you."


def render_head(step: str | None) -> str:
    h = state.hotel()
    pill = f'<span class="g-step">{esc(step)}</span>' if step else ""
    return check_copy(f'<header class="g-head"><span class="g-hotel">{esc(h["name"])}</span>{pill}</header>')


def render_intro() -> str:
    s = state.service()
    h = state.hotel()
    hours = f"{s.config['service']['start']} to {s.config['service']['end']}"
    return check_copy(f"""
<div class="g-title">
  <h1>{esc(s.breakfast_heading())}</h1>
  <p>{esc(state.long_date(s.service_date))} · {esc(hours)} at {esc(h['restaurant'])}. Tell us your plans and we will prepare just the right amount, fresh.</p>
</div>""")


def render_times_title() -> str:
    s = state.service()
    return check_copy(
        '<div class="g-title" style="gap:4px"><h1 class="t30">When would you like to come?</h1>'
        f'<p class="small">How busy each half hour usually is, based on {esc(s.bookings_phrase())}.</p></div>'
    )


def render_count(n: int) -> str:
    return f'<span class="count" aria-live="polite">{n}</span>'


def render_error(text: str) -> str:
    return f'<p class="g-error" role="alert">{esc(text)}</p>' if text else ""


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


def available_slots() -> list[dict]:
    return [s for s in state.service().crowd_view() if s["available"]]


def slot_choices(slots: list[dict]) -> list[tuple[str, str]]:
    # the label carries the word too, so screen readers hear "09:00, Busy"
    return [(s["time"], s["time"]) for s in slots]


def nearest_quiet(slots: list[dict], chosen: str) -> str | None:
    """The Quiet half hour closest to the chosen one; a later one wins a tie."""
    times = [s["time"] for s in slots]
    if chosen not in times:
        return None
    i = times.index(chosen)
    quiet = [j for j, s in enumerate(slots) if s["word"] == "Quiet"]
    if not quiet:
        return None
    best = min(quiet, key=lambda j: (abs(j - i), -j))
    return times[best]


def word_for(slots: list[dict], time: str | None) -> str | None:
    return next((s["word"] for s in slots if s["time"] == time), None)


def render_tip(slot: str) -> str:
    return check_copy(
        f'<div class="txt"><span class="t">{esc(slot)} is usually quiet</span>'
        f'<span class="b">Shorter queues and dishes straight from the kitchen.</span></div>'
    )


def confirm_label(slot: str | None, party: int) -> str:
    if not slot:
        return "Choose a time to confirm"
    return f"Confirm {slot} for {party} guest{'s' if party != 1 else ''}"


def render_confirmed(slot: str, party: int, room: str) -> str:
    s = state.service()
    h = state.hotel()
    guests = f"{party} guest{'s' if party != 1 else ''}"
    teal = GUEST["teal"]
    when = "tomorrow" if s.breakfast_heading() == "Breakfast tomorrow" else "this morning"
    return check_copy(f"""
<div class="g-done">
  <span class="circle">{icon('tick', 34, 2.6)}</span>
  <h1>You're all set</h1>
  <p>We look forward to seeing you {when}.</p>
</div>
<section class="g-details" aria-label="Your breakfast" style="margin-top:18px">
  <div class="item">{icon('calendar', 22, 2, teal)}<div class="txt"><span class="k">When</span><span class="v">{esc(state.long_date(s.service_date))}, {esc(slot)}</span></div></div>
  <div class="item">{icon('users', 22, 2, teal)}<div class="txt"><span class="k">Guests</span><span class="v">{guests} · Room {esc(room)}</span></div></div>
  <div class="item">{icon('pin', 22, 2, teal)}<div class="txt"><span class="k">Where</span><span class="v">{esc(h['restaurant'])}, {esc(h['level'])}</span></div></div>
</section>""")


def render_declined() -> str:
    return check_copy(f"""
<div class="g-done">
  <span class="circle">{icon('tick', 34, 2.6)}</span>
  <h1>Thank you for letting us know</h1>
  <p>We hope to see you at breakfast another morning.</p>
</div>""")


TIP_SMALL_PLATE = check_copy("""
<section class="g-tip big" aria-label="Breakfast tip">
  <div class="txt"><span class="t">A small plate, as often as you like</span>
  <span class="b">The buffet is topped up with fresh batches all morning, so start small and come back for more.</span></div>
</section>""")

QUIET_LINE = '<p class="g-quiet">Planning ahead helps our kitchen cook fresh and waste less food.</p>'


def _stepper(label: str, prefix: str, value: int, diet: bool, plus_on: bool = False):
    with gr.Row(elem_classes=["g-stepper"] + (["diet"] if diet else [])):
        gr.HTML(f'<span class="lbl" id="{prefix}-label">{esc(label)}</span>')
        minus = gr.Button("−", elem_id=f"{prefix}-minus", elem_classes=["bq-btn", "g-step-btn"])
        count = gr.HTML(render_count(value))
        plus = gr.Button("+", elem_id=f"{prefix}-plus", elem_classes=["bq-btn", "g-step-btn"] + (["on"] if plus_on else []))
    return minus, count, plus


def build_page() -> dict:
    gr.Navbar(visible=False)
    party = gr.State(2)
    halal = gr.State(0)
    veg = gr.State(0)
    crowd = gr.State([])           # the crowd view the guest saw when choosing a time

    with gr.Column(elem_classes=["bq-page", "bq-guest", "bq-phone"], elem_id="g-root"):
        # ---- 05 Breakfast plan ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-18"]) as step1:
            gr.HTML(render_head("Step 1 of 2"))
            gr.HTML(render_intro)          # a function, so each visit shows the current date and wording
            with gr.Column(elem_classes=["g-card"]):
                with gr.Column():
                    gr.HTML('<span class="g-q" aria-hidden="true">Will you join us?</span>')
                    attending = gr.Radio(["Yes", "Not this time"], value="Yes", label="Will you join us?",
                                         show_label=False, container=False, interactive=True, elem_classes=["g-toggle"])
                with gr.Column(elem_classes=["bq-gap-8"]):
                    room = gr.Textbox(label="Room number", placeholder="1204", lines=1, max_lines=1,
                                      container=True, show_label=True, elem_id="g-room", elem_classes=["g-room"])
                    room_error = gr.HTML("")
                with gr.Column(elem_classes=["bq-gap-18"]) as party_box:
                    p_minus, p_count, p_plus = _stepper("How many guests?", "g-party", 2, diet=False, plus_on=True)
                    with gr.Column(elem_classes=["g-diet"]):
                        gr.HTML('<span class="g-q">Dietary needs <span class="opt">(optional)</span></span>')
                        h_minus, h_count, h_plus = _stepper("Halal meals", "g-halal", 0, diet=True)
                        v_minus, v_count, v_plus = _stepper("Vegetarian meals", "g-veg", 0, diet=True)
            gr.HTML("", elem_classes=["bq-spacer"])
            choose_btn = gr.Button("Choose a time", elem_classes=["bq-btn", "g-primary"])
            gr.HTML('<p class="g-privacy">We use your room number only to plan how much food to prepare, '
                    "and delete it when you check out.</p>")

        # ---- 06 Choose a time ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-14"], visible=False) as step2:
            with gr.Row(elem_classes=["bq-between", "g-head"]):
                back_btn = gr.Button("Back", elem_classes=["bq-btn", "g-back", "bq-ico-chevron-left"])
                gr.HTML('<span class="g-step">Step 2 of 2</span>')
            times_title = gr.HTML(render_times_title())
            slot = gr.Radio([], value=None, label="Breakfast time", show_label=False, container=False,
                            interactive=True, elem_id="g-slots", elem_classes=["g-slots"])
            with gr.Column(elem_classes=["g-tip"], visible=False) as tip_box:
                tip_text = gr.HTML(render_tip(""))
                switch_btn = gr.Button("Switch", elem_classes=["bq-btn", "g-tip-btn"])
            gr.HTML("", elem_classes=["bq-spacer"])
            confirm_btn = gr.Button(confirm_label(None, 2), interactive=False, elem_classes=["bq-btn", "g-primary"])

        # ---- 07 Confirmed (or thank you, for "Not this time") ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-18"], visible=False) as step3:
            gr.HTML(render_head(None))
            confirmed = gr.HTML("")
            with gr.Column(elem_classes=["bq-gap-18"]) as confirmed_extra:
                gr.HTML(TIP_SMALL_PLATE)
                gr.HTML(QUIET_LINE)
            gr.HTML("", elem_classes=["bq-spacer"])
            change_btn = gr.Button("Change my plans", elem_classes=["bq-btn", "g-secondary"])

        gr.HTML('<p class="bq-note">Prototype · Fictional data</p>')

    # ---- steppers: party 1 to 8, meal counts capped at the party size ----
    def bump(n, delta, lo, hi):
        return max(lo, min(hi, n + delta))

    def set_party(p, h, v, delta):
        p = bump(p, delta, 1, MAX_PARTY)
        h, v = min(h, p), min(v, p)
        return p, h, v, render_count(p), render_count(h), render_count(v)

    party_out = [party, halal, veg, p_count, h_count, v_count]
    p_minus.click(lambda p, h, v: set_party(p, h, v, -1), [party, halal, veg], party_out)
    p_plus.click(lambda p, h, v: set_party(p, h, v, +1), [party, halal, veg], party_out)
    for minus, plus, st, cnt in ((h_minus, h_plus, halal, h_count), (v_minus, v_plus, veg, v_count)):
        minus.click(lambda n, p: (bump(n, -1, 0, p), render_count(bump(n, -1, 0, p))), [st, party], [st, cnt])
        plus.click(lambda n, p: (bump(n, +1, 0, p), render_count(bump(n, +1, 0, p))), [st, party], [st, cnt])

    # "Not this time" hides the party questions and turns the button into a reply
    def on_attending(choice):
        yes = choice == "Yes"
        return gr.update(visible=yes), gr.update(value="Choose a time" if yes else "Send my reply")

    attending.change(on_attending, attending, [party_box, choose_btn])

    # ---- step 1 to step 2 (or straight to the thank-you screen) ----
    def go_next(choice, r, p, h, v):
        if not state.valid_room(r):
            return (gr.update(), gr.update(), gr.update(), render_error(ROOM_ERROR), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
        if choice != "Yes":
            state.service().save_plan(state.GuestPlan(service_date="", room=r, attending=False, party=p))
            return (gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), "",
                    render_declined(), gr.update(visible=False), gr.update(), gr.update(), gr.update(),
                    gr.update(), gr.update())
        slots = available_slots()
        return (gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "",
                gr.update(), gr.update(), slots,
                gr.update(choices=slot_choices(slots), value=None),
                render_times_title() + render_slot_style(slots),
                gr.update(visible=False), gr.update(value=confirm_label(None, p), interactive=False))

    choose_btn.click(go_next, [attending, room, party, halal, veg],
                     [step1, step2, step3, room_error, confirmed, confirmed_extra, crowd, slot, times_title,
                      tip_box, confirm_btn])
    back_btn.click(lambda: (gr.update(visible=True), gr.update(visible=False)), None, [step1, step2])

    # ---- choosing a time: a Busy half hour suggests the nearest Quiet one ----
    def on_slot(s, p, slots):
        if not s:
            return gr.update(visible=False), gr.update(), gr.update(), gr.update(value=confirm_label(None, p), interactive=False)
        tip = nearest_quiet(slots, s) if word_for(slots, s) == "Busy" else None
        return (gr.update(visible=tip is not None), render_tip(tip or ""),
                gr.update(value=f"Switch to {tip}" if tip else "Switch"),
                gr.update(value=confirm_label(s, p), interactive=True))

    slot.change(on_slot, [slot, party, crowd], [tip_box, tip_text, switch_btn, confirm_btn])
    switch_btn.click(lambda s, slots: nearest_quiet(slots, s) or s, [slot, crowd], slot)

    # ---- confirm: save to shared state, then show the confirmation ----
    def do_confirm(s, r, p, h, v):
        plan = state.service().save_plan(state.GuestPlan(service_date="", room=r, attending=True, party=p,
                                                         halal=h, vegetarian=v, slot=s))
        return (gr.update(visible=False), gr.update(visible=True),
                render_confirmed(plan.slot, plan.party, plan.room), gr.update(visible=True))

    confirm_btn.click(do_confirm, [slot, room, party, halal, veg], [step2, step3, confirmed, confirmed_extra])
    change_btn.click(lambda: (gr.update(visible=True), gr.update(visible=False)), None, [step1, step3])

    return {"attending": attending, "room": room, "slot": slot, "confirm": confirm_btn}
