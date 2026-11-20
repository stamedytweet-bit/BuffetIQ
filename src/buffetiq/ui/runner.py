"""Runner phone, page "/runner": Tray check and Tray result (screens 03 and 04)
and Ask BuffetIQ (screen 02).

A two-option switch at the bottom moves between the tools. It is the one element
that is not on the design screens (agreed in Phase 0). Phase 0 shows sample data;
the camera model arrives in Phase 4 and the voice pipeline in Phase 6.
"""

from __future__ import annotations

import gradio as gr

from buffetiq.style import check_copy, esc, icon
from buffetiq.ui import sample

TRAY, ASK = "Tray check", "Ask BuffetIQ"

LEVEL_LOOK = {
    # level: (result card class, text colour class, icon)
    "Full": ("ok", "lv-ok", "check-circle"),
    "Half": ("ok", "lv-ok", "check-circle"),
    "Low": ("act", "lv-act", "warning"),
    "Empty": ("empty", "lv-empty", "x-circle"),
}
STATUS_PILL = {
    "connected": ("", "Board connected"),
    "basic": (" basic", "Basic answers"),
    "offline": (" offline", "Board offline"),
}


def render_head(title: str, sub: str) -> str:
    return check_copy(f'<div class="r-head"><h1>{esc(title)}</h1><span class="sub">{esc(sub)}</span></div>')


def render_viewfinder(dish: str) -> str:
    return check_copy(f"""
<div class="r-viewfinder" role="img" aria-label="Camera viewfinder">
  <span class="c tl"></span><span class="c tr"></span><span class="c bl"></span><span class="c br"></span>
  <div class="tray">{esc(dish)} tray</div>
  <div class="hint">Hold the phone above the tray</div>
  <div class="hint2">Whole tray in frame · flash off</div>
</div>""")


def render_photo(dish: str) -> str:
    return check_copy(
        f'<div class="r-photo" role="img" aria-label="Photo taken of the {esc(dish.lower())} tray">'
        f"[Photo of the {esc(dish.lower())} tray]</div>"
    )


def render_result(r: dict) -> str:
    card, colour, icon_name = LEVEL_LOOK[r["level"]]
    scale = []
    for lv in sample.LEVELS:
        on = lv == r["level"]
        bar = f' class="{colour}-bg"' if on else ""
        scale.append(f'<div class="{"on" if on else ""}"><i{bar}></i><span class="{colour if on else ""}">{lv}</span></div>')
    return check_copy(f"""
<section class="r-result {card}" aria-label="Result">
  <div class="lvl">
    <span class="word {colour}">{icon(icon_name, 40, 2.4)} {esc(r['level'])}</span>
    <span class="sure">{round(r['confidence'] * 100)}% sure</span>
  </div>
  <div class="est">{esc(r['estimate'])}</div>
  <div class="r-scale" aria-label="Fill level scale">{''.join(scale)}</div>
</section>""")


def render_board_updated(call: str) -> str:
    return check_copy(f"""
<section class="r-done" aria-label="Kitchen board update">
  <span class="tick">{icon('tick', 22, 2.6)}</span>
  <div class="txt"><span class="small">Kitchen board updated</span><span class="big">{esc(call)}</span></div>
</section>""")


def render_ask_head(time: str, status: str) -> str:
    cls, text = STATUS_PILL[status]
    return check_copy(f"""
<header class="bq-between" style="display:flex">
  <div class="r-head"><h1>Ask BuffetIQ</h1><span class="sub">{esc(time)} · Breakfast service</span></div>
  <span class="r-pill{cls}" role="status"><i></i>{text}</span>
</header>""")


def render_said(question: str, at: str) -> str:
    return check_copy(
        f'<div class="r-said"><span class="meta">You said · {esc(at)}</span>'
        f'<div class="bubble">{esc(question)}</div></div>'
    )


def render_answer(main: str, more: str) -> str:
    return check_copy(
        f'<div style="display:flex;flex-direction:column;gap:12px"><span class="kicker">BuffetIQ answer</span>'
        f'<div class="main">{esc(main)}</div><div class="more">{esc(more)}</div></div>'
    )


def _show(view: str):
    return gr.update(visible=view == TRAY), gr.update(visible=False), gr.update(visible=view == ASK)


def build_page() -> dict:
    tc, tr, ask = sample.TRAY_CHECK, sample.TRAY_RESULT, sample.ASK
    gr.Navbar(visible=False)
    with gr.Column(elem_classes=["bq-page", "bq-kitchen", "bq-phone"], elem_id="r-root"):
        # ---- 03 Tray check ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-18"]) as v_check:
            with gr.Row(elem_classes=["bq-between"]):
                gr.HTML(render_head("Tray check", f"{tc['station']} · {sample.RUNNER_TIME}"))
                change_station = gr.Button("Change station", elem_classes=["bq-btn", "r-secondary"])
            with gr.Column(elem_classes=["bq-gap-10"]):
                gr.HTML('<span class="r-label" aria-hidden="true">Which tray?</span>')
                dish = gr.Radio(tc["dishes"], value=tc["selected"], label="Which tray?", show_label=False,
                                container=False, interactive=True, elem_classes=["r-chips"])
            viewfinder = gr.HTML(render_viewfinder(tc["selected"]))
            check_btn = gr.Button("Check tray", elem_classes=["bq-btn", "r-primary", "bq-ico-camera"])
            manual_btn = gr.Button("Camera not working? Set the level by hand", elem_classes=["bq-btn", "bq-link-btn"])

        # ---- 04 Tray result ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-16"], visible=False) as v_result:
            with gr.Row(elem_classes=["bq-between"]):
                back_btn = gr.Button("Tray check", elem_classes=["bq-btn", "r-back", "bq-ico-chevron-left"])
                gr.HTML(f'<span class="r-label">{esc(tr["dish"])} · {esc(tr["time"])}</span>')
            gr.HTML(render_photo(tr["dish"]))
            gr.HTML(render_result(tr))
            gr.HTML(render_board_updated(tr["board_call"]))
            gr.HTML("", elem_classes=["bq-spacer"])
            next_btn = gr.Button("Check next tray", elem_classes=["bq-btn", "r-primary"])
            with gr.Row(elem_classes=["r-two"]):
                retake_btn = gr.Button("Retake photo", elem_classes=["bq-btn", "r-raised"])
                fix_btn = gr.Button("Wrong level? Fix it", elem_classes=["bq-btn", "r-raised"])

        # ---- 02 Ask BuffetIQ ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-18"], visible=False) as v_ask:
            gr.HTML(render_ask_head(sample.RUNNER_TIME, ask["status"]))
            with gr.Column(elem_classes=["bq-gap-14", "bq-spacer"]):
                gr.HTML(render_said(ask["question"], ask["asked_at"]))
                with gr.Column(elem_classes=["r-answer"]):
                    gr.HTML(render_answer(ask["answer_main"], ask["answer_more"]))
                    with gr.Row(elem_classes=["bq-between", "r-answer-foot"]):
                        gr.HTML(f'<span class="same">{icon("check-circle", 18, 2)} Same numbers as the board</span>')
                        replay_btn = gr.Button("Replay", elem_id="r-replay",
                                               elem_classes=["bq-btn", "r-replay", "bq-ico-speaker"])
                with gr.Column(elem_classes=["bq-gap-10"]):
                    gr.HTML('<span class="r-label">Try asking</span>')
                    with gr.Row(elem_classes=["r-try"]):
                        chips = [gr.Button(q, elem_classes=["bq-btn"]) for q in ask["try_asking"]]
            with gr.Column(elem_classes=["r-mic-wrap"]):
                mic_btn = gr.Button("Hold to talk", elem_id="r-mic", elem_classes=["bq-btn", "r-mic", "bq-ico-mic"])
                type_btn = gr.Button("Type a question instead", elem_classes=["bq-btn", "bq-link-btn"])
                typed = gr.Textbox(label="Your question", placeholder="How much egg should I cook?",
                                   visible=False, lines=1, max_lines=1, elem_classes=["r-typed"])

        switch = gr.Radio([TRAY, ASK], value=TRAY, label="Runner tool", show_label=False, container=False,
                          interactive=True, elem_classes=["r-switch"])
        gr.HTML('<p class="bq-note">Fictional data</p>')

    # Phase 0 wiring: moving between the static screens only.
    dish.change(render_viewfinder, dish, viewfinder)
    check_btn.click(lambda: (gr.update(visible=False), gr.update(visible=True)), None, [v_check, v_result])
    for b in (back_btn, next_btn, retake_btn):
        b.click(lambda: (gr.update(visible=True), gr.update(visible=False)), None, [v_check, v_result])
    switch.change(_show, switch, [v_check, v_result, v_ask])
    type_btn.click(lambda: gr.update(visible=True), None, typed)

    return {"dish": dish, "check": check_btn, "manual": manual_btn, "change_station": change_station,
            "fix": fix_btn, "replay": replay_btn, "chips": chips, "mic": mic_btn, "typed": typed, "switch": switch}
