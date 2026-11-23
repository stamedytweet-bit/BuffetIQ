"""About page, "/about": what the prototype is, links to every page, and (from
Phase 8) the presenter controls. Light mode, like the day-end report; there is
no approved design for this page, so it reuses the report's cards and type.
"""

from __future__ import annotations

import hmac
import os
import time

import gradio as gr

from buffetiq import qr, state
from buffetiq.style import check_copy, esc

PAGE_INFO = [
    ("kitchen", "Kitchen board", "Full screen on the TV or projector at the pass. Read, not touched."),
    ("runner", "Runner phone", "Tray check with the phone camera, and Ask BuffetIQ by voice or text."),
    ("guest", "Guest page", "Opened from the QR code on the key-card sleeve. Guests share their plans and pick a quieter time."),
    ("report", "Day-end report", "Leftovers, cost and stock-outs against a usual day, the NEA waste file, and retraining."),
]


def _href(path: str) -> str:
    # Relative links keep working behind a Colab or Gradio share-link prefix.
    return "./" if path == "/" else "." + path


def render_about(pages: dict) -> str:
    links = "".join(
        f'<a class="ab-link" href="{_href(pages[key])}"><span class="n">{esc(name)}</span>'
        f'<span class="p">{esc(pages[key])}</span><span class="d">{esc(desc)}</span></a>'
        for key, name, desc in PAGE_INFO
    )
    html = f"""
<div class="rp-title">
  <span class="brand">BuffetIQ</span>
  <h1>About this prototype</h1>
  <span class="sub">Ngee Ann Polytechnic AI showcase · Leisure and hospitality · Fictional data</span>
</div>
<div class="rp-body" style="margin-top:24px">
  <section class="ab-section">
    <h2>What BuffetIQ does</h2>
    <p>BuffetIQ helps a hotel kitchen match breakfast supply to demand while service is running. The night before,
    it forecasts how many guests will eat, when they will arrive in 15-minute slots, and how many kilograms of each dish
    they will need. During service it revises that forecast with what has already happened (a nowcast) and tells chefs
    what to cook, when to stop, and when to switch to cook-to-order, on the kitchen board and by voice.</p>
    <p class="muted">Most tools plan quantities before service or weigh waste after it is binned. BuffetIQ guides decisions
    during service and links them to what guests have told us.</p>
  </section>
  <section class="ab-section">
    <h2>Tray checks by camera</h2>
    <p>A runner photographs a tray with a phone and a small image model (YOLO26n-cls) sorts it into Empty, Low, Half or
    Full, with how sure it is. Below 60% sure, nothing is sent to the board and the runner retakes the photo or sets
    the level by hand. In a real kitchen, a fixed camera above the buffet would check every tray every one to two
    minutes; this prototype has no fixed cameras, so it checks on demand.</p>
  </section>
  <section class="ab-section">
    <h2>Pages</h2>
    <div class="ab-links">{links}</div>
  </section>
</div>"""
    return check_copy(html)


QR_INTRO = check_copy("""
<div style="display:flex;flex-direction:column;gap:12px">
  <h2 style="margin:0;font-size:20px;font-weight:800">Guest page QR code</h2>
  <p class="muted" style="margin:0;font-size:15px;line-height:1.55;color:var(--bq-muted)">Show the code on this laptop, or
  download the key-card sleeve insert (85 x 55 mm) and print it. Phones can open the link only if they are on the same
  Wi-Fi and the app was started with <code>--host 0.0.0.0</code>, or through the Colab share link.</p>
</div>""")

PRESENTER_INTRO = check_copy("""
<div style="display:flex;flex-direction:column;gap:8px">
  <h2 style="margin:0;font-size:20px;font-weight:800">Presenter controls</h2>
  <p style="margin:0;font-size:15px;line-height:1.55;color:var(--bq-muted)">"Load showcase morning" sets up the prepared
  fictional morning: Tuesday 24 November at 82% occupancy, with a tour group of 24 that nobody booked arriving at 07:45.
  The clock then runs at the chosen speed, or jumps to a time; simulated guests arrive and a simulated runner checks
  every tray every 15 minutes, while your taps, photos and questions are added on top. "Reset" returns the morning to
  06:15 and removes its bookings and log rows.</p>
</div>""")

ABOUT_END = check_copy("""
<div class="rp-body">
  <p class="rp-foot">All hotel names, guests, dishes and numbers in this prototype are fictional. Every result is
  simulated on fictional data.</p>
</div>""")


def make_qr(request: gr.Request):
    url = qr.url_from_request(request)
    path = qr.sleeve(url)
    link = f'<p class="ab-qr-link">Guest page: <a href="{esc(url)}" target="_blank">{esc(url)}</a></p>'
    return qr.qr_image(url), link, gr.update(value=str(path), visible=True)


# ---------------------------------------------------------------------------
# Presenter passcode
# ---------------------------------------------------------------------------
# On a public link (the Hugging Face Space) anyone could press Reset or Jump during the demo, so the
# presenter controls stay locked until the passcode in BUFFETIQ_PASSCODE is entered. On the laptop with
# no passcode set they are open, as before. Each browser session unlocks separately, every control checks
# the session on the server, and five wrong tries lock the box for a minute.

MAX_TRIES = 5
LOCKOUT_S = 60


try:  # on the laptop the passcode can sit in the git-ignored .env file
    from dotenv import load_dotenv

    load_dotenv(state.ROOT / ".env")
except ImportError:  # pragma: no cover
    pass


def passcode() -> str:
    return os.environ.get("BUFFETIQ_PASSCODE", "").strip()


def passcode_required() -> bool:
    return bool(passcode()) or bool(os.environ.get("SPACE_ID"))


def new_session() -> dict:
    return {"open": not passcode_required(), "tries": 0, "until": 0.0}


def try_passcode(session: dict, entered: str, now: float | None = None) -> tuple[dict, str]:
    """Check a passcode for one browser session. Returns the new session and a message for the page."""
    now = time.time() if now is None else now
    session = dict(session or new_session())
    code = passcode()
    if not code:
        return session, "No passcode is set. Add BUFFETIQ_PASSCODE to the Space secrets (or .env), then restart."
    if now < session["until"]:
        return session, f"Too many wrong tries. Wait {int(session['until'] - now) + 1} seconds, then try again."
    if hmac.compare_digest((entered or "").strip().encode(), code.encode()):
        return {"open": True, "tries": 0, "until": 0.0}, ""
    session["tries"] += 1
    if session["tries"] >= MAX_TRIES:
        session["tries"], session["until"] = 0, now + LOCKOUT_S
        return session, f"Too many wrong tries. Wait {LOCKOUT_S} seconds, then try again."
    return session, "That passcode is not right. Check it and try again."


def _note(text: str) -> str:
    return check_copy(f'<p class="ab-lock-note" role="status">{esc(text)}</p>') if text else ""


SPEED_LABELS = ["Paused", "1x", "2x", "5x", "10x"]
JUMP_TIMES = ["06:15", "06:30", "07:00", "07:30", "07:45", "08:00", "08:15", "08:40", "09:00", "09:30", "09:50",
              "10:15", "10:30"]


def render_status() -> str:
    from buffetiq import showcase

    s = state.service()
    e = s.kitchen()
    speed = next((k for k, v in showcase.SPEEDS.items() if v == showcase.CLOCK.speed), "Paused")
    mode = "Showcase morning" if s.mode == "showcase" else "Demo morning from the data"
    return check_copy(
        f'<p class="ab-status" role="status"><b>{esc(mode)}</b> · {esc(state.long_date(s.service_date))} · '
        f'clock {s.clock.strftime("%H:%M")} · {esc(speed)} · {int(round(e.arrived()))} diners so far · '
        f'expected {int(round(e.n() if e.started else s.expected_diners()))}</p>')


def build_page(pages: dict) -> dict:
    gr.Navbar(visible=False)
    with gr.Column(elem_classes=["bq-page", "bq-guest", "bq-wide"]):
        with gr.Column(elem_classes=["bq-wide-inner"]):
            body = gr.HTML(render_about(pages))
            with gr.Column(elem_classes=["ab-section", "ab-qr"]):
                gr.HTML(QR_INTRO)
                with gr.Row(elem_classes=["rp-actions"]):
                    show_btn = gr.Button("Show the guest QR code", elem_classes=["bq-btn", "rp-primary"])
                    sleeve_btn = gr.DownloadButton("Download sleeve insert (PNG)", visible=False,
                                                   elem_classes=["bq-btn", "rp-secondary", "bq-ico-download"])
                link = gr.HTML("")
                code = gr.Image(show_label=False, interactive=False, height=320, width=320,
                                elem_classes=["ab-qr-image"], buttons=[])
            with gr.Column(elem_classes=["ab-section", "ab-presenter"]):
                gr.HTML(PRESENTER_INTRO)
                status = gr.HTML(render_status)
                session = gr.State(new_session)
                with gr.Column(visible=passcode_required()) as lock_box:
                    with gr.Row(elem_classes=["rp-actions", "ab-controls"]):
                        code_in = gr.Textbox(label="Presenter passcode", type="password", max_lines=1,
                                             elem_classes=["ab-field", "ab-pass"])
                        unlock_btn = gr.Button("Unlock controls", elem_classes=["bq-btn", "rp-primary"])
                    lock_note = gr.HTML("")
                with gr.Column(visible=not passcode_required()) as controls:
                    with gr.Row(elem_classes=["rp-actions"]):
                        load_btn = gr.Button("Load showcase morning", elem_classes=["bq-btn", "rp-primary"])
                        reset_btn = gr.Button("Reset to 06:15", elem_classes=["bq-btn", "rp-secondary"])
                    with gr.Row(elem_classes=["rp-actions", "ab-controls"]):
                        jump_to = gr.Dropdown(JUMP_TIMES, value="07:45", label="Jump to", elem_classes=["ab-field"])
                        jump_btn = gr.Button("Jump", elem_classes=["bq-btn", "rp-secondary"])
                        speed = gr.Radio(list(SPEED_LABELS), value="Paused", label="Clock speed",
                                         elem_classes=["ab-field", "ab-speed"])
                    with gr.Row(elem_classes=["rp-actions"]):
                        plus1 = gr.Button("Log arrivals +1", elem_classes=["bq-btn", "rp-secondary"])
                        plus10 = gr.Button("Log arrivals +10", elem_classes=["bq-btn", "rp-secondary"])
            gr.HTML(ABOUT_END)
    ticker = gr.Timer(2)
    ticker.tick(render_status, None, status, show_progress="hidden", queue=False)

    def unlock(sess, entered):
        sess, msg = try_passcode(sess, entered)
        return (sess, gr.update(visible=not sess["open"]), gr.update(visible=sess["open"]),
                _note(msg), gr.update(value=""))

    def guarded(fn, with_speed: bool = False):
        """Run a control only for a session that has entered the passcode; otherwise change nothing."""
        def run(sess, *args):
            if not (sess or {}).get("open"):
                return (render_status(), gr.update()) if with_speed else render_status()
            return fn(*args)
        return run

    def load():
        from buffetiq import showcase

        showcase.CLOCK.set_speed(0)
        state.load_showcase()
        return render_status(), "Paused"

    def do_reset():
        from buffetiq import showcase

        showcase.CLOCK.set_speed(0)
        state.reset()
        return render_status(), "Paused"

    def jump(t):
        svc = state.service()
        if state.minutes(t) < svc.clock_minutes():
            svc.replay_to(t)          # going back replays the morning from 06:30
        else:
            svc.advance_to(state.minutes(t))
        return render_status()

    def set_speed(label):
        from buffetiq import showcase

        showcase.CLOCK.set_speed(showcase.SPEEDS[label])
        return render_status()

    def log(n):
        state.service().log_arrivals(n)
        return render_status()

    unlock_btn.click(unlock, [session, code_in], [session, lock_box, controls, lock_note, code_in])
    code_in.submit(unlock, [session, code_in], [session, lock_box, controls, lock_note, code_in])
    load_btn.click(guarded(load, with_speed=True), session, [status, speed])
    reset_btn.click(guarded(do_reset, with_speed=True), session, [status, speed])
    jump_btn.click(guarded(jump), [session, jump_to], status)
    speed.change(guarded(set_speed), [session, speed], status)
    plus1.click(guarded(lambda: log(1)), session, status)
    plus10.click(guarded(lambda: log(10)), session, status)
    show_btn.click(make_qr, None, [code, link, sleeve_btn])
    return {"body": body, "qr": code}
