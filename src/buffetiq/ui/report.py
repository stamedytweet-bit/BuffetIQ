"""Day-end report, page "/report" (screen 08). Light, fluid laptop layout.

The report is built by reports.py from today's service: the morning finished to
10:30, compared with the same morning under the usual chef rule. "Export NEA
waste file (CSV)" downloads every logged day's waste by dish in kilograms, and
"Retrain tonight" adds today to the history and retrains the forecast.
"""

from __future__ import annotations

import gradio as gr

from buffetiq import state
from buffetiq.style import GUEST, check_copy, esc
from buffetiq.ui import sample  # noqa: F401  (kept for the Phase 0 tests)


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


def render_learning(weeks: list[tuple[str, float]], unit: str = "week of use") -> str:
    """Bar per week; the latest week (the one the title is about) is the accent."""
    top = max(v for _, v in weeks) or 1
    bars, axis = [], []
    for i, (label, v) in enumerate(weeks):
        colour = GUEST["chart-today"] if i == len(weeks) - 1 else GUEST["chart-earlier"]
        h = round(98 * v / top)
        bars.append(f'<div><b>{v:.1f}%</b><i style="height:{h}px;background:{colour}"></i></div>')
        axis.append(f"<span>{esc(label)}</span>")
    first, last = weeks[0], weeks[-1]
    verb = "falls" if last[1] < first[1] else "moves"
    desc = f"Forecast error {verb} from {first[1]:.1f}% at {first[0].lower()} to {last[1]:.1f}% at {last[0].lower()}"
    return f"""
<section class="rp-panel rp-learn" aria-label="Forecast learning">
  <div style="display:flex;flex-direction:column;gap:4px"><h2>Forecast keeps improving</h2>
    <span class="sub">Average error in guests per day, by {esc(unit)}</span></div>
  <div class="rp-learn-bars" role="img" aria-label="{esc(desc)}">{''.join(bars)}</div>
  <div class="rp-learn-axis">{''.join(axis)}</div>
</section>"""


def render_simulation(sim: dict | None) -> str:
    """The 65-day replay result, so one morning is seen next to the average."""
    if not sim:
        return ""
    b, q = sim["baseline"], sim["buffetiq"]
    return check_copy(f"""
<section class="rp-panel" aria-label="65 days simulated">
  <div style="display:flex;flex-direction:column;gap:4px"><h2>Across 65 simulated days</h2>
    <span class="sub" style="font-size:14px;color:{GUEST['muted']}">Full BuffetIQ against the usual chef rule, simulated on fictional data</span></div>
  <div class="rp-event"><span class="t">{abs(q['change_left_pct']):.0f}% less food left over</span>
    <span class="d">{q['left_kg']:.1f} kg a day against {b['left_kg']:.1f} kg</span></div>
  <div class="rp-event"><span class="t">S${b['cost'] - q['cost']:.0f} a day less food wasted</span>
    <span class="d">S${q['cost']:.0f} against S${b['cost']:.0f}</span></div>
  <div class="rp-event"><span class="t">{q['empty_minutes']:.0f} minutes a day with an empty dish</span>
    <span class="d">Against {b['empty_minutes']:.0f} minutes under the chef rule</span></div>
</section>""")


def render_body(r: dict) -> str:
    html = f"""
<div class="rp-body">
  {render_figures(r['figures'])}
  <div class="rp-split">
    {render_leftovers(r['leftovers'], r['usual_total'])}
    <div class="rp-right">{render_events(r['events'])}{render_simulation(r.get('simulation'))}{render_learning(r['learning'], r.get('learning_unit', 'week of use'))}</div>
  </div>
  <p class="rp-foot">{esc(r['footnote'])}</p>
</div>"""
    return check_copy(html)


def _pct_change(today: float, usual: float) -> tuple[str, bool]:
    if usual <= 0:
        return "", False
    change = today / usual - 1
    if abs(change) < 0.005:
        return "The same as a usual day", False
    word = "less" if change < 0 else "more"
    return f"{abs(change):.0%} {word} than a usual day", change < 0


def date_line() -> str:
    svc = state.service()
    cfg = svc.config["service"]
    return f"{state.long_date(svc.service_date)} · Breakfast {cfg['start']} to {cfg['end']} · Simulated on fictional data"


def report_view() -> dict:
    """The live day-end report in the shape render_body() draws (screen 08)."""
    from buffetiq import nowcast, reports

    svc = state.service()
    r = reports.build(svc)
    cfg = svc.config["service"]
    left_text, left_good = _pct_change(r["left_total"], r["usual_total"])
    cost_good = r["cost"] < r["usual_cost"]
    spell = r["spell"]
    spell_text = (f" · {spell[0].lower()}, {nowcast.hhmm(spell[1])} to {nowcast.hhmm(spell[2])}" if spell else "")
    revised = f" · revised to {r['revised'][0]} at {r['revised'][1]}" if r["revised"] else ""
    figures = [
        {"label": "Food left over", "value": f"{r['left_total']:.1f} kg",
         "compare": f"{left_text} ({r['usual_total']:.1f} kg)", "good": left_good},
        {"label": "Cost of food wasted", "value": f"S${r['cost']:.0f}",
         "compare": f"Usual day S${r['usual_cost']:.0f}", "good": cost_good},
        {"label": "Minutes a dish was empty", "value": f"{r['empty_minutes']:.0f} min",
         "compare": f"Usual day {r['usual_empty_minutes']:.0f} min{spell_text}",
         "good": r["empty_minutes"] < r["usual_empty_minutes"]},
        {"label": "Guests served", "value": f"{r['diners']}", "compare": f"Forecast {r['forecast']}{revised}", "good": False},
    ]
    return {
        "date_line": date_line(),
        "figures": figures,
        "leftovers": [(x["name"], x["prepared"], x["eaten"], x["left"], x["usual_left"]) for x in r["rows"]],
        "usual_total": r["usual_total"],
        "events": r["events"] or [{"title": "A quiet morning", "line": "No stock-outs, overrides or Treatsure offers."}],
        "learning": r["learning"],
        "learning_unit": "months of use, on the same 65 test days",
        "simulation": _simulation(),
        "footnote": ("Simulated on fictional data for the prototype. A usual day is this same morning replayed under "
                     "the usual chef rule. The NEA file lists each day's food waste by dish in kilograms, ready to "
                     "adapt to NEA's reporting template."),
    }


def _simulation() -> dict | None:
    import json

    path = state.ROOT / "docs" / "phase5_results.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())["policies"]


def render_retrain(status: dict | None) -> str:
    if not status:
        return ""
    change = status["after"] - status["before"]
    if abs(change) < 0.05:
        moved = "the same as before retraining"
    else:
        moved = f"{abs(change):.1f} {'more' if change > 0 else 'fewer'} than before retraining"
    return check_copy(
        f'<p class="rp-status" role="status">Retrained on {status["days"]} days, including today. '
        f'Forecast for {esc(state.long_date(status["tomorrow"]))}: {status["after"]:.0f} guests, {moved}.</p>')


def build_page() -> dict:
    from buffetiq import reports

    gr.Navbar(visible=False)
    with gr.Column(elem_classes=["bq-page", "bq-guest", "bq-wide"]):
        with gr.Column(elem_classes=["bq-wide-inner"]):
            with gr.Row(elem_classes=["rp-header"]):
                title = gr.HTML(lambda: render_title(date_line()))
                with gr.Row(elem_classes=["rp-actions"]):
                    export_btn = gr.DownloadButton("Export NEA waste file (CSV)", value=lambda: reports.nea_csv(),
                                                   elem_classes=["bq-btn", "rp-secondary", "bq-ico-download"])
                    retrain_btn = gr.Button("Retrain tonight", elem_classes=["bq-btn", "rp-primary", "bq-ico-refresh"])
            status = gr.HTML("")
            body = gr.HTML(lambda: render_body(report_view()))

    def do_retrain():
        st = reports.retrain()
        return render_retrain(st), render_body(report_view())

    retrain_btn.click(do_retrain, None, [status, body])
    return {"export": export_btn, "retrain": retrain_btn, "body": body, "status": status}
