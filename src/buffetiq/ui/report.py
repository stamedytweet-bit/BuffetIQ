"""Day-end report, page "/report" (screen 08). Light, fluid laptop layout.

Phase 0 renders the sample day from the design. Phase 7 builds the same view
model from data/service_log.csv and wires "Retrain tonight".
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import gradio as gr

from buffetiq.style import GUEST, check_copy, esc
from buffetiq.ui import sample


def render_title(date_line: str) -> str:
    return check_copy(f"""
<div class="rp-title">
  <span class="brand">BuffetIQ</span>
  <h1>Day-end report</h1>
  <span class="sub">{esc(date_line)}</span>
</div>""")


def render_figures(figures: list[dict]) -> str:
    cards = "".join(
        f'<div class="rp-card"><span class="k">{esc(f["label"])}</span><span class="v">{esc(f["value"])}</span>'
        f'<span class="c{" good" if f["good"] else ""}">{esc(f["compare"])}</span></div>'
        for f in figures
    )
    return f'<section class="rp-figures" aria-label="Key figures">{cards}</section>'


def render_leftovers(rows: list[tuple], usual_total: float) -> str:
    """Table with paired bars: today in teal, a usual day in beige, both labelled."""
    biggest = max(max(r[3], r[4]) for r in rows) or 1
    scale = 78 / biggest  # the largest bar takes 78% of the column, leaving room for its label
    body = []
    for name, prep, eaten, left, usual in rows:
        body.append(f"""
<div class="rp-row" role="row">
  <span role="rowheader" style="font-weight:600">{esc(name)}</span>
  <span role="cell" class="num">{prep:.1f} kg</span>
  <span role="cell" class="num">{eaten:.1f} kg</span>
  <span role="cell" class="num" style="font-weight:700">{left:.1f} kg</span>
  <span role="cell" class="bars" aria-label="Today {left:.1f} kg, usual day {usual:.1f} kg">
    <span><i style="width:{left * scale:.1f}%;background:{GUEST['chart-today']}"></i><b>{left:.1f}</b></span>
    <span><i style="width:{usual * scale:.1f}%;background:{GUEST['chart-usual']}"></i><b style="color:{GUEST['muted']}">{usual:.1f}</b></span>
  </span>
</div>""")
    tp = sum(r[1] for r in rows)
    te = sum(r[2] for r in rows)
    tl = sum(r[3] for r in rows)
    return f"""
<section class="rp-panel rp-left" aria-label="Leftovers by dish">
  <div class="ph"><h2>Leftovers by dish</h2>
    <span class="rp-legend"><span><i style="background:{GUEST['chart-today']}"></i>Today</span>
    <span><i style="background:{GUEST['chart-usual']}"></i>Usual day</span></span></div>
  <div class="rp-scroll"><div class="rp-table" role="table" aria-label="Leftovers by dish">
    <div class="rp-row head" role="row"><span role="columnheader">Dish</span><span role="columnheader" class="num">Prepared</span>
      <span role="columnheader" class="num">Eaten</span><span role="columnheader" class="num">Left</span>
      <span role="columnheader" style="padding-left:12px">Left over, today against a usual day</span></div>
    {''.join(body)}
    <div class="rp-row total" role="row"><span role="rowheader">Total</span><span role="cell" class="num">{tp:.1f} kg</span>
      <span role="cell" class="num">{te:.1f} kg</span><span role="cell" class="num">{tl:.1f} kg</span>
      <span role="cell" style="padding-left:12px;font-size:13px;font-weight:400;color:{GUEST['muted']}">Usual day {usual_total:.1f} kg</span></div>
  </div></div>
</section>"""


def render_events(events: list[dict]) -> str:
    items = "".join(
        f'<div class="rp-event"><span class="t">{esc(e["title"])}</span><span class="d">{esc(e["line"])}</span></div>'
        for e in events[:4]
    )
    return f'<section class="rp-panel" aria-label="What happened today"><h2>What happened today</h2><div class="rp-events">{items}</div></section>'


def render_learning(weeks: list[tuple[str, float]]) -> str:
    """Bar per week; the latest week (the one the title is about) is the accent."""
    top = max(v for _, v in weeks) or 1
    bars, axis = [], []
    for i, (label, v) in enumerate(weeks):
        colour = GUEST["chart-today"] if i == len(weeks) - 1 else GUEST["chart-earlier"]
        h = round(98 * v / top)
        bars.append(f'<div><b>{v:.1f}%</b><i style="height:{h}px;background:{colour}"></i></div>')
        axis.append(f"<span>{esc(label)}</span>")
    first, last = weeks[0], weeks[-1]
    desc = f"Forecast error falls from {first[1]:.1f}% in {first[0].lower()} to {last[1]:.1f}% in {last[0].lower()}"
    return f"""
<section class="rp-panel rp-learn" aria-label="Forecast learning">
  <div style="display:flex;flex-direction:column;gap:4px"><h2>Forecast keeps improving</h2>
    <span class="sub">Average error in guests per day, by week of use</span></div>
  <div class="rp-learn-bars" role="img" aria-label="{esc(desc)}">{''.join(bars)}</div>
  <div class="rp-learn-axis">{''.join(axis)}</div>
</section>"""


def render_body(r: dict) -> str:
    html = f"""
<div class="rp-body">
  {render_figures(r['figures'])}
  <div class="rp-split">
    {render_leftovers(r['leftovers'], r['usual_total'])}
    <div class="rp-right">{render_events(r['events'])}{render_learning(r['learning'])}</div>
  </div>
  <p class="rp-foot">{esc(r['footnote'])}</p>
</div>"""
    return check_copy(html)


def sample_waste_csv() -> str:
    """Write the sample day's waste by dish (kg) for the export button. Fictional data."""
    path = Path(tempfile.gettempdir()) / "buffetiq_nea_waste_sample.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "dish", "food_waste_kg", "note"])
        for name, _prep, _eaten, left, _usual in sample.REPORT["leftovers"]:
            w.writerow(["2026-11-24", name, f"{left:.1f}", "Simulated on fictional data"])
    return str(path)


def build_page() -> dict:
    r = sample.REPORT
    gr.Navbar(visible=False)
    with gr.Column(elem_classes=["bq-page", "bq-guest", "bq-wide"]):
        with gr.Column(elem_classes=["bq-wide-inner"]):
            with gr.Row(elem_classes=["rp-header"]):
                gr.HTML(render_title(r["date_line"]))
                with gr.Row(elem_classes=["rp-actions"]):
                    export_btn = gr.DownloadButton("Export NEA waste file (CSV)", value=sample_waste_csv(),
                                                   elem_classes=["bq-btn", "rp-secondary", "bq-ico-download"])
                    retrain_btn = gr.Button("Retrain tonight", elem_classes=["bq-btn", "rp-primary", "bq-ico-refresh"])
            body = gr.HTML(render_body(r))
    return {"export": export_btn, "retrain": retrain_btn, "body": body}
