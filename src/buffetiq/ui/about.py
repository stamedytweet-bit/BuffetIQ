"""About page, "/about": what the prototype is, links to every page, and (from
Phase 8) the presenter controls. Light mode, like the day-end report; there is
no approved design for this page, so it reuses the report's cards and type.
"""

from __future__ import annotations

import gradio as gr

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
    <h2>Pages</h2>
    <div class="ab-links">{links}</div>
  </section>
  <section class="ab-section">
    <h2>Presenter controls</h2>
    <p class="muted">Load showcase morning, reset, jump to a time and the clock speed will appear here when the showcase
    mode is built.</p>
  </section>
  <p class="rp-foot">All hotel names, guests, dishes and numbers in this prototype are fictional. Every result is
  simulated on fictional data.</p>
</div>"""
    return check_copy(html)


def build_page(pages: dict) -> dict:
    gr.Navbar(visible=False)
    with gr.Column(elem_classes=["bq-page", "bq-guest", "bq-wide"]):
        with gr.Column(elem_classes=["bq-wide-inner"]):
            body = gr.HTML(render_about(pages))
    return {"body": body}
