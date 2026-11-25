"""Kitchen board, page "/" (screen 01).

Read, not touched: full screen on a TV at the pass, fixed dish order, no scrolling.
Each read-only region is a gr.HTML rendered from the kitchen engine in state.py
and refreshed every 5 seconds with gr.Timer. The backup buttons are native
gr.Buttons: "Start breakfast" runs the clock live from 06:30 (only logged diners count) and then becomes
"Restart" (two taps, back to 06:15), +1, +2 and +5 log diners at the door,
"Check a tray" shows a QR code for the runner page, and "Override a call" opens the override chooser. "Hold to ask
BuffetIQ" records from the laptop microphone; the answer is spoken through the
laptop and shown in the "Last voice answer" panel.
"""

from __future__ import annotations

import time

import gradio as gr

from buffetiq import nowcast, state, style
from buffetiq.style import check_copy, esc, fmt_amount, icon
from buffetiq.ui import sample, voice

REFRESH_SECONDS = state.load_config()["service"]["refresh_seconds"]
BAR_AREA_PX = 130

LEVEL_STYLE = {
    # level word: (colour class, icon name)
    "Full": ("lv-ok", "check-circle"),
    "Half": ("lv-ok", "check-circle"),
    "Low": ("lv-act", "warning"),
    "Empty": ("lv-empty", "x-circle"),
}

ALERT_DOT = {"stop": "!", "info": "i", "suggest": "›"}
ALERT_NAME = {"stop": "Stop-out or safety alert", "info": "Information", "suggest": "Suggestion"}


def render_header(h: dict) -> str:
    busy = h["next15_word"] == "Busy"
    was = f' <span class="was">was {h["expected_was"]}</span>' if h.get("expected_was") is not None else ""
    html = f"""
<header class="k-header">
  <div class="k-brand">
    <div class="name">BuffetIQ</div>
    <div class="sub">{esc(h['date_line'])}</div>
  </div>
  <div class="k-clock" aria-label="Time now {esc(h['clock'])}">
    <div class="time">{esc(h['clock'])}</div><div class="now">now</div>
  </div>
  <div class="k-pills">
    <div class="k-pill narrow"><span class="label">Diners so far</span><span class="value">{h['diners_so_far']}</span></div>
    <div class="k-pill"><span class="label">Expected today</span>
      <span class="value">{h['expected']}{was}</span></div>
    <div class="k-pill{' busy' if busy else ''}"><span class="label">Next 15 minutes</span>
      <span class="value">{esc(h['next15_word'])} · {h['next15_count']}</span></div>
  </div>
</header>"""
    return check_copy(html)


def render_dish_card(d: dict) -> str:
    colour, icon_name = LEVEL_STYLE[d["level"]]
    card_cls = {"act": " act", "empty": " empty"}.get(d["card_kind"], "")
    action_cls = {"act": " act", "empty": " empty"}.get(d["action_kind"], "")
    foot_cls = {"warn": " warn", "limit": " limit"}.get(d["timer_kind"], "")
    foot_icon = "warning" if d["timer_kind"] in ("warn", "limit") else "clock"
    return f"""
<article class="k-card{card_cls}" aria-label="{esc(d['name'])}">
  <div class="top"><h2>{esc(d['name'])}</h2><span class="station">{esc(d['station'])}</span></div>
  <div class="k-level">
    <div class="k-bar" role="img" aria-label="Tray {d['fill_pct']}% full"><span class="{colour}-bg" style="width:{d['fill_pct']}%"></span></div>
    <div class="row2">
      <span class="word {colour}">{icon(icon_name, 24, 2.4)} {esc(d['level'])}</span>
      <span class="amount">{esc(d['amount'])}</span>
    </div>
  </div>
  <div class="k-action{action_cls}">
    <div class="do">{esc(d['action'])}</div>
    <div class="why">{esc(d['action_line'])}</div>
  </div>
  <div class="k-foot{foot_cls}">{icon(foot_icon, 18, 2)}<span>{esc(d['timer'])}</span></div>
</article>"""


def render_dishes(dishes: list[dict]) -> str:
    cards = "".join(render_dish_card(d) for d in dishes)
    return check_copy(f'<section class="k-dishes" aria-label="Dishes on the buffet">{cards}</section>')


def render_arrivals(a: dict) -> str:
    slots = []
    for i, fc in enumerate(a["forecast_px"]):
        ac = a["actual_px"][i]
        bar = ""
        if ac is not None:
            now = " now" if i == a["current_index"] else ""
            bar = f'<div class="ac{now}" style="height:{ac}px"></div>'
        slots.append(f'<div class="slot"><div class="fc" style="height:{fc}px"></div>{bar}</div>')
    html = f"""
<div class="k-panel">
  <div class="k-arr-head"><h2>Arrivals</h2><span class="finding">{esc(a['finding'])}</span></div>
  <div class="k-bars" role="img" aria-label="Arrivals per 15 minutes: actual so far against forecast. {esc(a['finding'])}.">{''.join(slots)}</div>
  <div class="k-axis"><span>{esc(a['start'])}</span><span class="now">{esc(a['now_label'])}</span><span>{esc(a['end'])}</span></div>
  <div class="k-legend"><span><i class="ac"></i>Actual</span><span><i class="fc"></i>Forecast</span></div>
</div>"""
    return check_copy(html)


def render_alerts(alerts: list[dict]) -> str:
    if not alerts:
        return check_copy('<div class="k-panel k-alerts"><h2>Alerts</h2>'
                          '<p class="k-empty">No alerts yet. Guest bookings and kitchen calls appear here.</p></div>')
    items = []
    for al in alerts[:3]:
        items.append(
            f"""<div class="k-alert"><span class="dot {al['kind']}" role="img" aria-label="{ALERT_NAME[al['kind']]}">{ALERT_DOT[al['kind']]}</span>
<div class="txt"><span class="title">{esc(al['title'])}</span><span class="line">{esc(al['line'])}</span></div></div>"""
        )
    return check_copy(f'<div class="k-panel k-alerts"><h2>Alerts</h2>{"".join(items)}</div>')


def render_voice(v: dict) -> str:
    q = f'<div class="q">“{esc(v["question"])}”</div>' if v.get("question") else ""
    cls = "a problem" if v.get("problem") else ("a empty" if v.get("empty") else "a")
    html = f"""
<div class="k-panel k-voice">
  <div class="head">{icon('mic', 20, 2)} Last voice answer</div>
  {q}
  <div class="{cls}">{esc(v['answer'])}</div>
</div>"""
    return check_copy(html)


# ---------------------------------------------------------------------------
# Live view models (Phase 5: everything except the last voice answer, Phase 6)
# ---------------------------------------------------------------------------

def _level_word(stock: float, capacity: float) -> str:
    frac = min(stock, capacity) / capacity
    if frac <= 0.02:
        return "Empty"
    if frac < 0.25:
        return "Low"
    if frac <= 0.75:
        return "Half"
    return "Full"


def live_header() -> dict:
    s = state.service()
    e = s.kitchen()
    cfg = s.config["service"]
    n = e.n() if e.started else s.expected_diners()
    expected, was = int(round(n)), int(round(s.n0))
    slots = s.expected_slots()
    now = s.clock_minutes()
    if e.started and now < nowcast.SERVICE_END:
        nxt = nowcast.remaining_between(n, e.arrived(), e.shares, now, now + 15)
    else:
        nxt = float(slots[0]) if now < nowcast.SERVICE_START else 0.0
    word = state.crowd_word(nxt, float(max(slots.max(), 1)))
    return {
        "date_line": f"Breakfast service · {state.long_date(s.service_date)} · {cfg['start']} to {cfg['end']} · Fictional data",
        "clock": s.clock.strftime("%H:%M"),
        "diners_so_far": int(round(e.arrived())),
        "expected": expected,
        "expected_was": was if was != expected else None,
        "next15_word": word,
        "next15_count": int(round(nxt)),
    }


def live_arrivals() -> dict:
    s = state.service()
    e = s.kitchen()
    cfg = s.config["service"]
    forecast_slots = s.expected_slots()
    actual = e.arrivals
    top = max(forecast_slots.max(), actual.max(), 1)
    current = s.current_slot_index()
    f = e.f() if e.started else 0.0
    if not e.started:
        finding = f"Service starts at {cfg['start']}"
    elif f < s.config["rules"]["min_forecast_share"]:
        finding = "Too early to compare"
    else:
        gap = e.arrived() / (f * e.n0) - 1
        finding = "On forecast" if abs(gap) < 0.03 else f"{abs(gap):.0%} {'ahead of' if gap > 0 else 'behind'} forecast"
    last = current if current is not None else (len(actual) - 1 if e.started and s.clock_minutes() >= nowcast.SERVICE_END else -1)
    return {
        "finding": finding,
        "start": cfg["start"],
        "now_label": f"{s.clock.strftime('%H:%M')} now" if current is not None else "",
        "end": cfg["end"],
        "forecast_px": [max(2, round(BAR_AREA_PX * v / top)) for v in forecast_slots],
        "actual_px": [max(3, round(BAR_AREA_PX * actual[i] / top)) if i <= last else None for i in range(len(actual))],
        "current_index": current if current is not None else -1,
    }


def live_dishes() -> list[dict]:
    """One card per dish from the engine: level, amount, call and pan timer."""
    s = state.service()
    e = s.kitchen()
    now = s.clock_minutes()
    cards = []
    for d in s.config["dishes"]:
        did, cap = d["id"], float(d["pan_capacity"])
        stock = e.stock.get(did, cap)            # before service the opening pan is ready
        word = _level_word(stock, cap)
        call = e.calls.get(did)
        if not e.started or call is None:
            action, line, kind = "Hold", f"Service starts at {s.config['service']['start']}", "hold"
        else:
            action, line = nowcast.action_text(d, call), call.line
            kind = "hold"
            if call.action == "cook":
                kind = "empty" if did in e.empty_since else "act"
        reserve = stock - cap
        if action == "Hold" and reserve > 0.05 * cap and e.started and "override" not in line:
            extra = f"{reserve:.1f} kg" if d["unit"] == "kg" else f"{int(round(reserve))} pieces"
            line += f" · {extra} in reserve"
        if d.get("chilled"):
            timer_kind, timer = "ok", "Chilled display · check temperature"
        else:
            timer_kind, timer = nowcast.pan_status(e.out_at.get(did) if e.started else None, now)
        border = {"limit": "empty", "warn": "act"}.get(timer_kind, kind if kind in ("act", "empty") else "normal")
        if kind == "empty":
            border = "empty"
        cards.append({
            "name": d["name"], "station": d["station"], "level": word,
            "fill_pct": round(100 * min(stock, cap) / cap),
            "amount": fmt_amount(min(stock, cap), cap, d["unit"]),
            "action": action, "action_kind": kind, "action_line": line,
            "timer": timer, "timer_kind": timer_kind, "card_kind": border,
        })
    return cards


def live_alerts() -> list[dict]:
    """Kitchen alerts from the engine and guest booking alerts, newest first, three at most."""
    s = state.service()
    e = s.kitchen()
    items = [(a.at, {"kind": a.kind, "title": a.title, "line": a.line}) for a in e.alerts]
    items += [(state.minutes(a["at"]), a) for a in s.latest_alerts(10)]
    items.sort(key=lambda x: -x[0])
    return [a for _, a in items[:3]]


def live_voice() -> dict:
    a = state.service().last_answer
    if not a:
        return {"question": "", "answer": "Hold the button and ask, such as \"How much egg should I cook?\"",
                "problem": False, "empty": True}
    return {"question": a["question"], "answer": a["spoken"], "problem": False}


def refresh():
    return (render_header(live_header()), render_dishes(live_dishes()), render_arrivals(live_arrivals()),
            render_alerts(live_alerts()))


def refresh_all():
    return (*refresh(), render_voice(live_voice()))


LOG_STEPS = (1, 2, 5)
RESTART_CONFIRM_SECONDS = 6
ARRIVALS_LABEL = (f'<div class="k-arr-label">{icon("user-plus", 28)}<span>Log<br>arrivals</span></div>')


def start_button(pending: float) -> dict:
    """Label and look of the Start / Restart slot: Start while the clock is stopped, Restart once it runs."""
    from buffetiq import showcase

    if pending and time.time() < pending:
        return {"value": "Tap again to restart", "elem_classes": ["bq-btn", "bq-ico-refresh", "k-confirm"]}
    if showcase.can_start():
        return {"value": "Start breakfast", "elem_classes": ["bq-btn", "bq-ico-play"]}
    return {"value": "Restart", "elem_classes": ["bq-btn", "bq-ico-refresh"]}


OVERRIDE_ACTIONS = [("Cook a batch now", "cook"), ("Hold", "hold"), ("Let it run down", "run_down"),
                    ("Cook to order", "cook_to_order"), ("Discard the pan (4-hour rule or spoiled)", "discard")]
OVERRIDE_REASONS = ["VIP or event breakfast", "Dropped or spoiled tray", "Quality problem",
                    "Looks different by eye", "Pan reached 4 hours", "Other"]


def build_page() -> dict:
    """Build the kitchen board inside the current Blocks/route context."""
    gr.Navbar(visible=False)
    dish_names = [d["name"] for d in state.load_config()["dishes"]]
    with gr.Column(elem_classes=["bq-page", "bq-kitchen", "bq-board-viewport"]):
        with gr.Column(elem_id="bq-board"):
            header = gr.HTML(lambda: render_header(live_header()), elem_id="bq-header")
            with gr.Row(elem_id="bq-main"):
                dishes = gr.HTML(lambda: render_dishes(live_dishes()), elem_id="bq-dishes")
                with gr.Column(elem_id="bq-rail"):
                    arrivals = gr.HTML(lambda: render_arrivals(live_arrivals()), elem_id="bq-arrivals")
                    alerts = gr.HTML(lambda: render_alerts(live_alerts()), elem_id="bq-alerts")
                    voice_panel = gr.HTML(lambda: render_voice(live_voice()), elem_id="bq-voice")
            with gr.Row(elem_id="bq-strip"):
                start_btn = gr.Button(**start_button(0.0), elem_id="k-start")
                with gr.Row(elem_id="k-arrivals"):
                    gr.HTML(ARRIVALS_LABEL, elem_id="k-arr-label")
                    log_btns = {n: gr.Button(f"+{n}", elem_id=f"k-log-{n}", elem_classes=["bq-btn"]) for n in LOG_STEPS}
                tray_btn = gr.Button("Check a tray", elem_id="k-tray", elem_classes=["bq-btn", "bq-ico-camera"])
                ask_btn = voice.hold_button("Hold to ask BuffetIQ", "Hold to ask BuffetIQ", "board", "k-ask")
                override_btn = gr.Button("Override a call", elem_id="k-override", elem_classes=["bq-btn", "bq-ico-pencil"])

            # ---- touch backups, shown over the board only when asked for ----
            with gr.Column(visible=False, elem_id="k-panel-override", elem_classes=["k-sheet"]) as override_panel:
                gr.HTML('<h2 class="k-sheet-title">Override a call</h2>')
                o_dish = gr.Dropdown(dish_names, value=dish_names[0], label="Dish", elem_classes=["k-field"])
                o_action = gr.Radio([a for a, _ in OVERRIDE_ACTIONS], value=OVERRIDE_ACTIONS[0][0], label="New action",
                                    elem_classes=["k-field", "k-choice"])
                o_reason = gr.Dropdown(OVERRIDE_REASONS, value=OVERRIDE_REASONS[0], label="Reason", elem_classes=["k-field"])
                with gr.Row(elem_classes=["k-sheet-buttons"]):
                    o_cancel = gr.Button("Cancel", elem_classes=["bq-btn", "k-sheet-secondary"])
                    o_apply = gr.Button("Apply override", elem_classes=["bq-btn", "k-sheet-primary"])
            with gr.Column(visible=False, elem_id="k-panel-tray", elem_classes=["k-sheet"]) as tray_panel:
                tray_html = gr.HTML("")
                tray_close = gr.Button("Close", elem_classes=["bq-btn", "k-sheet-secondary"])

    board_audio = gr.HTML("", elem_id="k-answer-audio", elem_classes=["bq-hidden-audio"])

    pending = gr.State(0.0)   # when set, Restart has been tapped once and waits for a second tap until this time
    timer = gr.Timer(REFRESH_SECONDS)
    timer.tick(lambda pend: (*refresh_all(), gr.update(**start_button(pend))), pending,
               [header, dishes, arrivals, alerts, voice_panel, start_btn], show_progress="hidden", queue=False)

    def start_or_restart(pend):
        """Start runs the clock live from 06:30; Restart needs a second tap within a few seconds."""
        from buffetiq import showcase

        if showcase.can_start():
            showcase.start_breakfast()
            pend = 0.0
        elif pend and time.time() < pend:
            showcase.restart_morning()
            pend = 0.0
        else:
            pend = time.time() + RESTART_CONFIRM_SECONDS
        return (*refresh_all(), gr.update(**start_button(pend)), pend)

    start_btn.click(start_or_restart, pending, [header, dishes, arrivals, alerts, voice_panel, start_btn, pending],
                    show_progress="hidden")

    def ask_aloud(path):
        """Board microphone: transcribe, answer, speak through the laptop and show it in the panel."""
        from buffetiq import assistant

        ans, problem = assistant.ask_from_audio(path)
        if ans is None:
            panel = render_voice({"question": "", "answer": problem, "problem": True})
            return panel, gr.update()
        return render_voice(live_voice()), assistant.audio_html(assistant.speak(ans.spoken))

    ask_btn.submit(ask_aloud, ask_btn, [voice_panel, board_audio], show_progress="hidden")

    def logger(n: int):
        def log_n():
            state.service().log_arrivals(n)
            return refresh()
        return log_n

    for n, btn in log_btns.items():
        btn.click(logger(n), None, [header, dishes, arrivals, alerts], show_progress="hidden")

    def open_tray(request: gr.Request):
        from buffetiq import qr

        url = qr.url_from_request(request).replace(qr.GUEST_PATH, "/runner")
        img = qr.qr_image(url, box=8)
        import base64, io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        src = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        html = (f'<h2 class="k-sheet-title">Check a tray with a phone</h2>'
                f'<p class="k-sheet-text">Scan with the runner\'s phone, photograph the tray, and this board updates '
                f'within 5 seconds.</p><img class="k-sheet-qr" src="{src}" alt="QR code for the runner page">'
                f'<p class="k-sheet-text">{esc(url)}</p>')
        return gr.update(visible=True), html

    tray_btn.click(open_tray, None, [tray_panel, tray_html])
    tray_close.click(lambda: gr.update(visible=False), None, tray_panel)

    override_btn.click(lambda: gr.update(visible=True), None, override_panel)
    o_cancel.click(lambda: gr.update(visible=False), None, override_panel)

    def apply_override(name, action_label, reason):
        dish_id = next(d["id"] for d in state.load_config()["dishes"] if d["name"] == name)
        action = dict(OVERRIDE_ACTIONS)[action_label]
        state.service().override(dish_id, action, reason)
        return (gr.update(visible=False), *refresh())

    o_apply.click(apply_override, [o_dish, o_action, o_reason], [override_panel, header, dishes, arrivals, alerts])

    return {
        "timer": timer, "header": header, "dishes": dishes, "arrivals": arrivals, "alerts": alerts, "voice": voice_panel,
        "start": start_btn, "log": log_btns, "tray": tray_btn, "ask": ask_btn, "override": override_btn,
    }
