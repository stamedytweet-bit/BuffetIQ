"""Runner phone, page "/runner": Tray check and Tray result (screens 03 and 04)
and Ask BuffetIQ (screen 02).

A two-option switch at the bottom moves between the tools. It is the one element
that is not on the design screens (agreed in Phase 0).

Tray check (Phase 4): "Check tray" opens the phone camera, the photo is
classified by camera.py, and a sure result updates the dish's level on the
kitchen board. Below 0.6 confidence the "Not sure about this one" card appears
and nothing is sent. "Camera not working? Set the level by hand" and "Wrong
level? Fix it" open the manual level buttons, labelled as manual. "Record
leftovers" at the end of service writes the amount left to the history instead.

Ask BuffetIQ still shows sample data; the voice pipeline arrives in Phase 6.
"""

from __future__ import annotations

import base64
import io

import gradio as gr

from buffetiq import camera, state
from buffetiq.style import check_copy, esc, icon
from buffetiq.ui import sample

TRAY, ASK = "Tray check", "Ask BuffetIQ"

LEVEL_LOOK = {
    # level word: (result card class, text colour class, icon)
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
OPEN_CAMERA_JS = """() => {
  const input = document.querySelector('#r-photo-input input[type=file]');
  if (input) { input.setAttribute('accept', 'image/*'); input.setAttribute('capture', 'environment'); input.click(); }
}"""


# ---------------------------------------------------------------------------
# Stations and dishes
# ---------------------------------------------------------------------------

def stations() -> list[str]:
    seen: list[str] = []
    for d in state.load_config()["dishes"]:
        if d["station"] not in seen:
            seen.append(d["station"])
    return seen


def dishes_at(station: str) -> list[dict]:
    return [d for d in state.load_config()["dishes"] if d["station"] == station]


def dish_by_name(name: str) -> dict:
    return next(d for d in state.load_config()["dishes"] if d["name"] == name)


def clock() -> str:
    return state.service().clock.strftime("%H:%M")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

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


def photo_data_uri(image, max_side: int = 640) -> str:
    img = camera.to_rgb(image)
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def render_photo(dish: str, image=None) -> str:
    label = f"Photo taken of the {esc(dish.lower())} tray"
    if image is None:
        return check_copy(f'<div class="r-photo" role="img" aria-label="{label}">'
                          f"[Photo of the {esc(dish.lower())} tray]</div>")
    return check_copy(f'<div class="r-photo"><img src="{photo_data_uri(image)}" alt="{label}"></div>')


def render_result(r: dict) -> str:
    """The level card. r has 'level' (a word such as 'Low'), 'confidence' (None when set by hand) and 'estimate'."""
    card, colour, icon_name = LEVEL_LOOK[r["level"]]
    scale = []
    for lv in sample.LEVELS:
        on = lv == r["level"]
        bar = f' class="{colour}-bg"' if on else ""
        scale.append(f'<div class="{"on" if on else ""}"><i{bar}></i><span class="{colour if on else ""}">{lv}</span></div>')
    pill = "Set by hand" if r.get("confidence") is None else f"{round(r['confidence'] * 100)}% sure"
    return check_copy(f"""
<section class="r-result {card}" aria-label="Result">
  <div class="lvl">
    <span class="word {colour}">{icon(icon_name, 40, 2.4)} {esc(r['level'])}</span>
    <span class="sure">{pill}</span>
  </div>
  <div class="est">{esc(r['estimate'])}</div>
  <div class="r-scale" aria-label="Fill level scale">{''.join(scale)}</div>
</section>""")


def render_unsure(level: str, confidence: float) -> str:
    return check_copy(f"""
<section class="r-result act r-unsure" aria-label="Result" role="status">
  <div class="title">{icon('warning', 30, 2.4)} Not sure about this one</div>
  <div class="est">Closest guess: {esc(camera.WORDS[level])} ({round(confidence * 100)}% sure). Nothing was sent to the kitchen board.</div>
  <div class="est">Retake the photo with the whole tray in frame and the flash off, or set the level by hand.</div>
</section>""")


def render_board_updated(call: str, small: str = "Kitchen board updated") -> str:
    return check_copy(f"""
<section class="r-done" aria-label="{esc(small)}">
  <span class="tick">{icon('tick', 22, 2.6)}</span>
  <div class="txt"><span class="small">{esc(small)}</span><span class="big">{esc(call)}</span></div>
</section>""")


def render_model_note(kind: str | None) -> str:
    if kind == "stand-in":
        return ('<p class="bq-note r-model-note">Test model trained on computer-drawn trays, '
                "not real photos. Results are for trying the app only.</p>")
    return ""


def render_manual_head(dish: str, fixing: bool) -> str:
    title = "Fix the level" if fixing else "Set the level by hand"
    sub = f"{dish} · Manual" + (" · the photo will help train the model" if fixing else "")
    return render_head(title, sub)


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


# ---------------------------------------------------------------------------
# What a result says
# ---------------------------------------------------------------------------

def outcome(dish_name: str, level: str, confidence: float | None, source: str, leftover: bool) -> dict:
    """Record a sure level and return the texts for the result screen."""
    d = dish_by_name(dish_name)
    state.service().record_tray(d["id"], level, source, confidence, leftover=leftover)
    est = camera.estimate_text(level, d)
    word = camera.WORDS[level]
    if leftover:
        small = "Recorded as leftover"
        call = f"{dish_name}: {est[0].lower() + est[1:]} at close"
    else:
        small = "Kitchen board updated"
        call = f"{dish_name}: tray {word.lower()}, {est[0].lower() + est[1:]}"
    return {"card": render_result({"level": word, "confidence": confidence, "estimate": est}),
            "done": render_board_updated(call, small)}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def _show(view: str):
    return gr.update(visible=view == TRAY), gr.update(visible=False), gr.update(visible=False), gr.update(visible=view == ASK)


def build_page() -> dict:
    ask = sample.ASK
    first_station = stations()[0]
    first_dishes = [d["name"] for d in dishes_at(first_station)]
    gr.Navbar(visible=False)

    station = gr.State(first_station)
    photo = gr.State(None)           # the last photo, kept for "Wrong level? Fix it"
    leftover = gr.State(False)       # "Record leftovers" mode
    fixing = gr.State(False)         # manual panel opened from "Wrong level? Fix it"

    with gr.Column(elem_classes=["bq-page", "bq-kitchen", "bq-phone"], elem_id="r-root"):
        # ---- 03 Tray check ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-18"]) as v_check:
            with gr.Row(elem_classes=["bq-between"]):
                check_head = gr.HTML(lambda: render_head("Tray check", f"{first_station} · {clock()}"))
                change_station = gr.Button("Change station", elem_classes=["bq-btn", "r-secondary"])
            with gr.Column(elem_classes=["bq-gap-10"]):
                gr.HTML('<span class="r-label" aria-hidden="true">Which tray?</span>')
                dish = gr.Radio(first_dishes, value=first_dishes[0], label="Which tray?", show_label=False,
                                container=False, interactive=True, elem_classes=["r-chips"])
            viewfinder = gr.HTML(render_viewfinder(first_dishes[0]))
            camera_input = gr.Image(type="pil", sources=["upload"], label="Tray photo", show_label=False,
                                    elem_id="r-photo-input", elem_classes=["r-photo-input"])
            check_btn = gr.Button("Check tray", elem_classes=["bq-btn", "r-primary", "bq-ico-camera"])
            manual_btn = gr.Button("Camera not working? Set the level by hand", elem_classes=["bq-btn", "bq-link-btn"])
            leftover_btn = gr.Button("End of service? Record leftovers", elem_classes=["bq-btn", "bq-link-btn", "r-small-link"])

        # ---- 04 Tray result ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-16"], visible=False) as v_result:
            with gr.Row(elem_classes=["bq-between"]):
                back_btn = gr.Button("Tray check", elem_classes=["bq-btn", "r-back", "bq-ico-chevron-left"])
                result_meta = gr.HTML("")
            result_photo = gr.HTML("")
            result_card = gr.HTML("")
            result_done = gr.HTML("")
            model_note = gr.HTML("")
            gr.HTML("", elem_classes=["bq-spacer"])
            next_btn = gr.Button("Check next tray", elem_classes=["bq-btn", "r-primary"])
            retake_primary = gr.Button("Retake photo", visible=False, elem_classes=["bq-btn", "r-primary", "bq-ico-camera"])
            with gr.Row(elem_classes=["r-two"]):
                retake_btn = gr.Button("Retake photo", elem_classes=["bq-btn", "r-raised"])
                fix_btn = gr.Button("Wrong level? Fix it", elem_classes=["bq-btn", "r-raised"])

        # ---- Manual levels (fallback and corrections) ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-16"], visible=False) as v_manual:
            manual_head = gr.HTML("")
            gr.HTML('<p class="r-label">How full is the tray?</p>')
            level_icons = {"full": "check-circle", "half": "check-circle", "low": "warning", "empty": "x-circle"}
            level_btns = {lv: gr.Button(camera.WORDS[lv], elem_classes=["bq-btn", "r-level", f"r-level-{lv}",
                                                                         f"bq-ico-{level_icons[lv]}"])
                          for lv in ("full", "half", "low", "empty")}
            gr.HTML("", elem_classes=["bq-spacer"])
            cancel_btn = gr.Button("Cancel", elem_classes=["bq-btn", "r-raised"])

        # ---- 02 Ask BuffetIQ (sample until Phase 6) ----
        with gr.Column(elem_classes=["bq-view", "bq-gap-18"], visible=False) as v_ask:
            gr.HTML(lambda: render_ask_head(clock(), ask["status"]))
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

    views = [v_check, v_result, v_manual]

    def show(which):
        return [gr.update(visible=v is which) for v in views]

    # ---- station, dish and mode ----
    def head_text(st, left):
        return render_head("Record leftovers" if left else "Tray check", f"{st} · {clock()}")

    def next_station(st, left):
        names = stations()
        st = names[(names.index(st) + 1) % len(names)]
        ds = [d["name"] for d in dishes_at(st)]
        return st, head_text(st, left), gr.update(choices=ds, value=ds[0]), render_viewfinder(ds[0])

    change_station.click(next_station, [station, leftover], [station, check_head, dish, viewfinder])
    dish.change(lambda d: render_viewfinder(d or ""), dish, viewfinder)

    def toggle_leftover(left, st):
        left = not left
        return (left, head_text(st, left),
                gr.update(value="Photograph leftovers" if left else "Check tray"),
                gr.update(value="Back to tray checks" if left else "End of service? Record leftovers"))

    leftover_btn.click(toggle_leftover, [leftover, station], [leftover, check_head, check_btn, leftover_btn])

    # ---- camera ----
    check_btn.click(None, None, None, js=OPEN_CAMERA_JS)
    for b in (retake_btn, retake_primary):
        b.click(lambda: show(v_check), None, views).then(None, None, None, js=OPEN_CAMERA_JS)

    def on_photo(image, d, left):
        if image is None:
            return [gr.update()] * 13
        meta = f'<span class="r-label">{esc(d)} · {clock()}</span>'
        res = camera.classify(image)
        if res is None:   # no model yet: go straight to the manual buttons
            return (*show(v_manual), image, False, render_manual_head(d, False), gr.update(), gr.update(),
                    gr.update(), gr.update(), gr.update(), gr.update(value=None), gr.update())
        if not res.sure:
            return (*show(v_result), image, False, gr.update(), meta, render_photo(d, image),
                    render_unsure(res.level, res.confidence), "", render_model_note(res.model_kind),
                    gr.update(value=None), "unsure")
        out = outcome(d, res.level, res.confidence, "camera", left)
        return (*show(v_result), image, False, gr.update(), meta, render_photo(d, image), out["card"],
                out["done"], render_model_note(res.model_kind), gr.update(value=None), "sure")

    mode = gr.State("sure")
    camera_input.upload(on_photo, [camera_input, dish, leftover],
                        [*views, photo, fixing, manual_head, result_meta, result_photo, result_card, result_done,
                         model_note, camera_input, mode]
                        ).then(
        lambda m: (gr.update(visible=m != "unsure"), gr.update(visible=m == "unsure"),
                   gr.update(visible=m != "unsure"),
                   gr.update(value="Set the level by hand" if m == "unsure" else "Wrong level? Fix it")),
        mode, [next_btn, retake_primary, retake_btn, fix_btn])

    # ---- manual levels ----
    manual_btn.click(lambda d: (*show(v_manual), render_manual_head(d, False), False), dish,
                     [*views, manual_head, fixing])
    fix_btn.click(lambda d, img: (*show(v_manual), render_manual_head(d, img is not None), img is not None),
                  [dish, photo], [*views, manual_head, fixing])
    cancel_btn.click(lambda: show(v_check), None, views)

    def set_level(level, d, img, fix, left):
        if fix and img is not None:
            camera.save_correction(img, level)
        out = outcome(d, level, None, "correction" if fix else "manual", left)
        meta = f'<span class="r-label">{esc(d)} · {clock()}</span>'
        return (*show(v_result), meta, render_photo(d, img), out["card"], out["done"], "",
                gr.update(visible=True), gr.update(visible=False), gr.update(visible=True),
                gr.update(value="Wrong level? Fix it"))

    for lv, b in level_btns.items():
        b.click(lambda d, img, fix, left, lv=lv: set_level(lv, d, img, fix, left), [dish, photo, fixing, leftover],
                [*views, result_meta, result_photo, result_card, result_done, model_note,
                 next_btn, retake_primary, retake_btn, fix_btn])

    for b in (back_btn, next_btn):
        b.click(lambda: (*show(v_check), None), None, [*views, photo])

    # ---- switching tools ----
    switch.change(_show, switch, [v_check, v_result, v_manual, v_ask])
    type_btn.click(lambda: gr.update(visible=True), None, typed)

    return {"dish": dish, "check": check_btn, "manual": manual_btn, "change_station": change_station,
            "fix": fix_btn, "replay": replay_btn, "chips": chips, "mic": mic_btn, "typed": typed,
            "switch": switch, "camera_input": camera_input}
