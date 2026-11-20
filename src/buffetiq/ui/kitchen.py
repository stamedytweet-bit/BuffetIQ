"""Kitchen board, page "/" (screen 01).

Read, not touched: full screen on a TV at the pass, fixed dish order, no scrolling.
Each read-only region is a gr.HTML rendered by a function below from a view model
(sample data in Phase 0, live state from Phase 5). The four backup buttons are
native gr.Buttons.
"""

from __future__ import annotations

import gradio as gr

from buffetiq.style import check_copy, esc, icon
from buffetiq.ui import sample

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
      <span class="value">{h['expected']} <span class="was">was {h['expected_was']}</span></span></div>
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
    items = []
    for al in alerts[:3]:
        items.append(
            f"""<div class="k-alert"><span class="dot {al['kind']}" role="img" aria-label="{ALERT_NAME[al['kind']]}">{ALERT_DOT[al['kind']]}</span>
<div class="txt"><span class="title">{esc(al['title'])}</span><span class="line">{esc(al['line'])}</span></div></div>"""
        )
    return check_copy(f'<div class="k-panel k-alerts"><h2>Alerts</h2>{"".join(items)}</div>')


def render_voice(v: dict) -> str:
    html = f"""
<div class="k-panel k-voice">
  <div class="head">{icon('mic', 20, 2)} Last voice answer</div>
  <div class="q">“{esc(v['question'])}”</div>
  <div class="a">{esc(v['answer'])}</div>
</div>"""
    return check_copy(html)


def build_page() -> dict:
    """Build the kitchen board inside the current Blocks/route context."""
    gr.Navbar(visible=False)
    with gr.Column(elem_classes=["bq-page", "bq-kitchen", "bq-board-viewport"]):
        with gr.Column(elem_id="bq-board"):
            header = gr.HTML(render_header(sample.KITCHEN_HEADER), elem_id="bq-header")
            with gr.Row(elem_id="bq-main"):
                dishes = gr.HTML(render_dishes(sample.KITCHEN_DISHES), elem_id="bq-dishes")
                with gr.Column(elem_id="bq-rail"):
                    arrivals = gr.HTML(render_arrivals(sample.KITCHEN_ARRIVALS), elem_id="bq-arrivals")
                    alerts = gr.HTML(render_alerts(sample.KITCHEN_ALERTS), elem_id="bq-alerts")
                    voice = gr.HTML(render_voice(sample.KITCHEN_VOICE), elem_id="bq-voice")
            with gr.Row(elem_id="bq-strip"):
                log_btn = gr.Button("Log arrivals +5", elem_id="k-log", elem_classes=["bq-btn", "bq-ico-user-plus"])
                tray_btn = gr.Button("Check a tray", elem_id="k-tray", elem_classes=["bq-btn", "bq-ico-camera"])
                ask_btn = gr.Button("Hold to ask BuffetIQ", elem_id="k-ask", elem_classes=["bq-btn", "bq-primary", "bq-ico-mic"])
                override_btn = gr.Button("Override a call", elem_id="k-override", elem_classes=["bq-btn", "bq-ico-pencil"])
    return {
        "header": header, "dishes": dishes, "arrivals": arrivals, "alerts": alerts, "voice": voice,
        "log": log_btn, "tray": tray_btn, "ask": ask_btn, "override": override_btn,
    }
