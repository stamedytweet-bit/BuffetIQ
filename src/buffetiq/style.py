"""Design tokens, icons, CSS and copy helpers shared by every BuffetIQ page.

Colours live here as CSS custom properties scoped to `.bq-kitchen` (dark: kitchen
board and runner phone) and `.bq-guest` (light: guest flow, day-end report and
About page), so the group can change a colour in one place. Values come from
CLAUDE.md and the approved HTML snapshots in design/html/.
"""

from __future__ import annotations

import html
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

KITCHEN = {
    "bg": "#0E1415",
    "surface": "#172123",
    "raised": "#1F2B2D",
    "border": "#2C3A3C",
    "border-strong": "#3C4D4F",
    "text": "#F4F1EA",
    "text-2": "#C9D1D0",
    "text-3": "#A9B4B3",
    "brand": "#7FD3C3",
    "brand-hover": "#A8E6DA",
    "brand-ink": "#0B2420",      # text on a brand-teal fill (selected chips)
    "ok": "#5BC0A8",
    "act": "#F2B33D",
    "act-ink": "#1A1300",
    "act-ring": "#3A2D10",       # ring around the microphone button
    "empty": "#FF6B5E",
    "empty-ink": "#1A1300",
    "forecast": "#6F8584",
    "viewfinder": "#070B0C",
}

GUEST = {
    "bg": "#FAF8F4",
    "surface": "#FFFFFF",
    "border": "#E7E2D8",
    "border-strong": "#CFC8BA",
    "divider": "#EFEAE0",
    "text": "#1F2328",
    "muted": "#5F646B",
    "teal": "#0F6E6E",
    "teal-dark": "#0A4F4F",
    "teal-tint": "#E3F1EF",
    "crowd-quiet": "#7FC4BA",
    "crowd-moderate": "#3E938A",
    "crowd-busy": "#0F6E6E",
    "crowd-word": "#2E6E65",     # Quiet and Moderate labels (Busy uses teal-dark)
    "saffron": "#E0A030",
    "tip-bg": "#FFF4DD",
    "tip-title": "#3A2A00",
    "tip-body": "#5A4512",
    "tip-button-border": "#8A6410",
    "chart-today": "#0F6E6E",
    "chart-usual": "#D9D3C7",
    "chart-earlier": "#9FC9C3",
    "error": "#9B2C1F",          # form error text (not in the design tokens; 7:1 on the page)
}

FONT_STACK = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
SERIF_STACK = "Fraunces, Georgia, 'Times New Roman', serif"

# Board artboard size from design/html/01-kitchen-board.html.
BOARD_W, BOARD_H = 1920, 1080

HEAD = """
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap" rel="stylesheet">
"""

# ---------------------------------------------------------------------------
# Icons (paths copied from the design snapshots, 24 x 24 view box, stroked)
# ---------------------------------------------------------------------------

ICONS = {
    "warning": '<path d="M12 3.5L22 20H2L12 3.5z"/><path d="M12 10v4.5"/><path d="M12 17.2v.1"/>',
    "check-circle": '<circle cx="12" cy="12" r="9.5"/><path d="M7.5 12.5l3 3 6-6.5"/>',
    "x-circle": '<circle cx="12" cy="12" r="9.5"/><path d="M8.5 8.5l7 7"/><path d="M15.5 8.5l-7 7"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "mic": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v3"/>',
    "user-plus": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.5 3.4-5.5 6.5-5.5s5.7 2 6.5 5.5"/><path d="M18 8v6"/><path d="M15 11h6"/>',
    "camera": '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
    "pencil": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    "speaker": '<path d="M4 10v4h4l5 4V6L8 10z"/><path d="M16 9a4 4 0 0 1 0 6"/>',
    "chevron-left": '<path d="M15 5l-7 7 7 7"/>',
    "tick": '<path d="M6 12.5l4 4 8-9"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17"/><path d="M8 3v4"/><path d="M16 3v4"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.5 3.4-5.5 6.5-5.5s5.7 2 6.5 5.5"/><circle cx="17" cy="9" r="2.5"/><path d="M16 14.5c2.6.2 4.7 2 5.5 5.5"/>',
    "pin": '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    "download": '<path d="M12 4v11"/><path d="M7 10l5 5 5-5"/><path d="M5 20h14"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 5v6h-6"/>',
}


def icon(name: str, size: int = 24, stroke: float = 2, color: str = "currentColor") -> str:
    """Return an inline, decorative SVG icon (hidden from screen readers)."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>'
    )


def _icon_data_uri(name: str, stroke: float = 2) -> str:
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
        f"stroke='black' stroke-width='{stroke}' stroke-linecap='round' "
        f"stroke-linejoin='round'>{ICONS[name]}</svg>"
    ).replace('"', "'")
    return "data:image/svg+xml;utf8," + quote(svg, safe=":/=' ;,.-")


def _icon_button_css() -> str:
    """CSS that puts an icon in front of a native gr.Button with class bq-ico-<name>.

    The icon is drawn with a CSS mask so it takes the button's text colour.
    """
    rules = []
    for name in ICONS:
        stroke = 2.2 if name in {"mic", "chevron-left"} else 2
        rules.append(
            f".bq-ico-{name}::before{{content:'';flex:none;width:var(--bq-ico,24px);"
            f"height:var(--bq-ico,24px);background:currentColor;"
            f'-webkit-mask:url("{_icon_data_uri(name, stroke)}") center/contain no-repeat;'
            f'mask:url("{_icon_data_uri(name, stroke)}") center/contain no-repeat;}}'
        )
    return "\n".join(rules)


# ---------------------------------------------------------------------------
# Copy helpers
# ---------------------------------------------------------------------------

EM_DASH = "\u2014"


def esc(text) -> str:
    """Escape text for safe use inside gr.HTML."""
    return html.escape(str(text), quote=True)


def fmt_kg(value: float) -> str:
    """Kilograms to one decimal place, with integers shown without a trailing .0
    only when the design does so (it never does for amounts below 10)."""
    return f"{value:.1f}"


def fmt_amount(value: float, capacity: float, unit: str) -> str:
    """'0.4 of 2.5 kg' or '18 of 40 pieces', as on the dish cards."""
    if unit == "pieces":
        return f"{int(round(value))} of {int(round(capacity))} pieces"
    shown = "0" if round(value, 1) == 0 else fmt_kg(value)
    return f"{shown} of {fmt_kg(capacity)} kg"


def fmt_cook_amount(value: float, unit: str) -> str:
    """'4 kg', '1.5 kg' or '24' (pieces), for action blocks."""
    if unit == "pieces":
        return f"{int(round(value))}"
    return f"{value:g} kg"


def check_copy(text: str) -> str:
    """Raise if on-screen copy breaks the writing rules that are cheap to check."""
    if EM_DASH in text:
        raise ValueError(f"Em dash found in copy: {text!r}")
    return text


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def _vars(scope: str, tokens: dict) -> str:
    body = ";".join(f"--bq-{k}:{v}" for k, v in tokens.items())
    return f"{scope}{{{body}}}"


BASE_CSS = """
/* Gradio chrome: no navbar, no footer, no outer padding. The navbar is also
   hidden with gr.Navbar(visible=False) on every page; this rule is the backstop. */
.nav-holder, footer { display: none !important; }
html, body { margin: 0; }
.gradio-container { max-width: none !important; padding: 0 !important; margin: 0 !important;
  min-height: 100dvh; font-family: __FONT__ !important; }
.gradio-container > main, .gradio-container .main, .gradio-container .wrap.fillable,
.gradio-container main.fillable, .gradio-container .contain { padding: 0 !important; margin: 0 !important;
  max-width: none !important; gap: 0 !important; }
.bq-page, .bq-page * { box-sizing: border-box; }
.bq-page { font-family: __FONT__; line-height: normal; font-variant-numeric: tabular-nums; -webkit-font-smoothing: antialiased; }

/* Neutralise Gradio wrappers inside our pages */
.bq-page .block, .bq-page .form { background: transparent !important; border: none !important;
  box-shadow: none !important; padding: 0 !important; margin: 0 !important; border-radius: 0 !important;
  min-width: 0 !important; overflow: visible !important; }
.bq-page .html-container { padding: 0 !important; }
.bq-page .prose { font-size: inherit !important; line-height: inherit !important; color: inherit !important;
  max-width: none !important; font-weight: inherit; }
/* Gradio paints every element inside gr.HTML with the body colour; let ours inherit instead. */
.bq-page :where(.prose *) { color: inherit; }
.bq-page .prose :where(h1,h2,h3,p,ul,ol,li) { margin: 0; font-family: inherit; }
.bq-page .row, .bq-page .column { gap: 0; flex-wrap: nowrap; min-width: 0 !important; }
.bq-page .hide-container { padding: 0 !important; }
.bq-page .status-tracker, .bq-page [data-testid="status-tracker"] { display: none !important; }
.bq-page button { font-family: __FONT__ !important; box-shadow: none !important; }
.bq-page button:focus-visible, .bq-page input:focus-visible + span, .bq-page textarea:focus-visible,
.bq-page input:focus-visible { outline: 3px solid var(--bq-focus) !important; outline-offset: 2px; }
.bq-sr-only { position: absolute !important; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }

/* Page backgrounds */
html:has(.bq-kitchen.bq-page), body:has(.bq-kitchen.bq-page),
body:has(.bq-kitchen.bq-page) .gradio-container { background: #0E1415 !important; }
html:has(.bq-guest.bq-page), body:has(.bq-guest.bq-page),
body:has(.bq-guest.bq-page) .gradio-container { background: #FAF8F4 !important; }
.bq-kitchen { --bq-focus: #7FD3C3; color: var(--bq-text); background: var(--bq-bg);
  /* keep Gradio's own components on our palette in light or dark system mode */
  --body-text-color: #F4F1EA; --block-background-fill: transparent; --input-background-fill: #172123;
  --border-color-primary: #3C4D4F; --color-accent: #7FD3C3; }
.bq-guest { --bq-focus: #0A4F4F; color: var(--bq-text); background: var(--bq-bg); color-scheme: light;
  --body-text-color: #1F2328; --block-background-fill: transparent; --input-background-fill: #FFFFFF;
  --input-placeholder-color: #8A8F96; --border-color-primary: #CFC8BA; --color-accent: #0F6E6E;
  --body-text-color-subdued: #5F646B; }

/* Native buttons: shared reset */
.bq-btn { display: flex !important; align-items: center; justify-content: center; gap: 12px;
  min-width: 0 !important; width: auto; font-weight: 700 !important; cursor: pointer;
  transition: none !important; background-image: none !important; line-height: 1.2 !important; }
.bq-btn:disabled { cursor: default; }
"""

# ---- Kitchen board (screen 01). Fixed 1920 x 1080 artboard scaled to fit. ----
KITCHEN_BOARD_CSS = """
.bq-board-viewport { position: fixed; inset: 0; overflow: hidden; background: var(--bq-bg); }
#bq-board { position: absolute !important; left: 0; top: 0; width: 1920px !important; height: 1080px !important;
  transform-origin: 0 0; transform: translate(var(--bq-board-x, 0px), var(--bq-board-y, 0px)) scale(var(--bq-board-scale, 1));
  padding: 32px 40px !important; display: flex !important; flex-direction: column !important; gap: 24px !important;
  background: var(--bq-bg); flex-wrap: nowrap !important; }
#bq-board > * { flex: none; }
#bq-header { height: 96px; }
#bq-main { flex: 1 1 auto !important; min-height: 0; display: flex !important; gap: 24px !important; align-items: stretch !important; }
#bq-dishes { flex: 1 1 auto !important; min-width: 0; height: 100%; }
#bq-rail { flex: none !important; width: 460px !important; display: flex !important; flex-direction: column !important;
  gap: 20px !important; min-height: 0; }
#bq-rail > * { flex: none; }
#bq-alerts { flex: 1 1 auto !important; min-height: 0; }
#bq-dishes > .html-container, #bq-dishes .prose, #bq-alerts > .html-container, #bq-alerts .prose { height: 100%; }
#bq-strip { height: 96px; display: grid !important; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 20px !important; }

.k-header { height: 96px; display: flex; align-items: center; justify-content: space-between; gap: 32px; }
.k-brand { display: flex; flex-direction: column; gap: 8px; }
.k-brand .name { font-size: 32px; font-weight: 800; letter-spacing: -0.01em; color: var(--bq-brand); line-height: 1.2; }
.k-brand .sub { font-size: 20px; color: var(--bq-text-3); line-height: 1.2; }
.k-clock { display: flex; align-items: baseline; gap: 12px; }
.k-clock .time { font-size: 80px; font-weight: 700; line-height: 1; }
.k-clock .now { font-size: 22px; color: var(--bq-text-3); }
.k-pills { display: flex; gap: 16px; }
.k-pill { box-sizing: content-box !important; background: var(--bq-surface); border: 1px solid var(--bq-border); border-radius: 16px; padding: 12px 22px;
  display: flex; flex-direction: column; gap: 4px; min-width: 200px; }
.k-pill.narrow { min-width: 170px; }
.k-pill .label { font-size: 16px; color: var(--bq-text-3); line-height: 1.2; }
.k-pill .value { font-size: 34px; font-weight: 700; line-height: 1.2; }
.k-pill .was { font-size: 18px; font-weight: 500; color: var(--bq-text-3); }
.k-pill.busy { border: 2px solid var(--bq-act); padding: 11px 21px; }
.k-pill.busy .value { color: var(--bq-act); }

.k-dishes { height: 100%; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(0, 1fr)); gap: 20px; }
.k-card { background: var(--bq-surface); border: 2px solid var(--bq-border); border-radius: 18px; padding: 20px;
  display: flex; flex-direction: column; gap: 14px; min-height: 0; }
.k-card.act { border-color: var(--bq-act); }
.k-card.empty { border-color: var(--bq-empty); }
.k-card .top { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.k-card h2 { margin: 0; font-size: 26px !important; font-weight: 700 !important; line-height: 1.15 !important; color: var(--bq-text) !important; }
.k-card .station { font-size: 15px; color: var(--bq-text-3); white-space: nowrap; }
.k-level { display: flex; flex-direction: column; gap: 8px; }
.k-bar { height: 14px; border-radius: 7px; background: var(--bq-border); overflow: hidden; }
.k-bar > span { display: block; height: 14px; border-radius: 7px; }
.k-level .row2 { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.k-level .word { display: flex; align-items: center; gap: 8px; font-size: 22px; font-weight: 700; }
.k-level .amount { font-size: 18px; color: var(--bq-text-2); }
.lv-ok { color: var(--bq-ok); } .lv-ok-bg { background: var(--bq-ok); }
.lv-act { color: var(--bq-act); } .lv-act-bg { background: var(--bq-act); }
.lv-empty { color: var(--bq-empty); } .lv-empty-bg { background: var(--bq-empty); }
.k-action { flex: 1; background: var(--bq-raised); color: var(--bq-text); border-radius: 14px; padding: 16px 18px;
  display: flex; flex-direction: column; justify-content: center; gap: 6px; min-height: 0; }
.k-action.act { background: var(--bq-act); color: var(--bq-act-ink); }
.k-action.empty { background: var(--bq-empty); color: var(--bq-empty-ink); }
.k-action .do { font-size: 40px; font-weight: 800; line-height: 1.05; }
.k-action .why { font-size: 18px; font-weight: 600; line-height: 1.2; }
.k-foot { display: flex; align-items: center; gap: 8px; font-size: 16px; color: var(--bq-text-3); line-height: 1.25; }
.k-foot svg { flex: none; }
.k-foot.warn { color: var(--bq-act); font-weight: 600; }
.k-foot.limit { color: var(--bq-empty); font-weight: 700; }

.k-panel { background: var(--bq-surface); border: 1px solid var(--bq-border); border-radius: 18px; padding: 20px;
  display: flex; flex-direction: column; gap: 14px; }
.k-panel h2 { margin: 0; font-size: 22px !important; font-weight: 700 !important; line-height: 1.2 !important; color: var(--bq-text) !important; }
.k-arr-head { display: flex; justify-content: space-between; align-items: center; }
.k-arr-head .finding { font-size: 17px; font-weight: 600; color: var(--bq-act); }
.k-bars { display: flex; align-items: flex-end; gap: 4px; height: 130px; }
.k-bars .slot { position: relative; flex: 1; height: 130px; }
.k-bars .fc { position: absolute; left: 0; right: 0; bottom: 0; border: 1.5px dashed var(--bq-forecast); border-radius: 4px; }
.k-bars .ac { position: absolute; left: 3px; right: 3px; bottom: 0; background: var(--bq-ok); border-radius: 4px; }
.k-bars .ac.now { background: var(--bq-act); }
.k-axis { display: flex; justify-content: space-between; font-size: 15px; color: var(--bq-text-3); }
.k-axis .now { color: var(--bq-act); font-weight: 600; }
.k-legend { display: flex; gap: 20px; font-size: 15px; color: var(--bq-text-2); }
.k-legend span { display: flex; align-items: center; gap: 8px; }
.k-legend i { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.k-legend i.ac { background: var(--bq-ok); }
.k-legend i.fc { border: 1.5px dashed var(--bq-forecast); }
.k-alerts { height: 100%; overflow: hidden; }
.k-alert { display: flex; gap: 14px; align-items: flex-start; }
.k-alert .dot { flex: none; width: 30px; height: 30px; border-radius: 15px; color: var(--bq-act-ink);
  display: flex; align-items: center; justify-content: center; font-size: 17px; font-weight: 800; }
.k-alert .dot.stop { background: var(--bq-empty); }
.k-alert .dot.info { background: var(--bq-brand); }
.k-alert .dot.suggest { background: var(--bq-act); }
.k-alert .txt { display: flex; flex-direction: column; gap: 2px; }
.k-alert .title { font-size: 18px; font-weight: 700; line-height: 1.25; }
.k-alert .line { font-size: 16px; line-height: 1.4; color: var(--bq-text-2); }
/* hold-to-talk buttons (ui/voice.py) */
.bq-hold-wrap { width: 100%; }
.bq-hold { display: flex; align-items: center; justify-content: center; cursor: pointer; border: none;
  font-family: inherit; background: var(--bq-act); color: var(--bq-act-ink); touch-action: none; user-select: none;
  -webkit-user-select: none; -webkit-touch-callout: none; }
.bq-hold:focus-visible { outline: 3px solid var(--bq-brand); outline-offset: 3px; }
.bq-hold-board { width: 100%; height: 96px; border-radius: 18px; gap: 14px; font-size: 26px; font-weight: 800; }
.bq-hold-phone { width: 132px; height: 132px; border-radius: 66px; border: 6px solid var(--bq-act-ring); flex-direction: column;
  gap: 6px; font-size: 17px; font-weight: 800; margin: 0 auto; }
.bq-hold[data-state="recording"] { background: var(--bq-empty); color: var(--bq-empty-ink); }
.bq-hold[data-state="thinking"] { background: var(--bq-raised); color: var(--bq-text); }
.bq-hold-wrap-phone { display: flex; justify-content: center; }
.bq-hold .lbl { white-space: nowrap; }
.bq-hidden-audio { position: absolute !important; left: -9999px !important; width: 1px !important; height: 1px !important; overflow: hidden !important; }
.k-voice .a.empty { font-size: 18px; font-weight: 600; color: var(--bq-text-3); }
.k-voice .a.problem { font-size: 18px; color: var(--bq-act); }
.r-empty { margin: 0; font-size: 16px; line-height: 1.5; color: var(--bq-text-3); }
.r-problem { margin: 0; font-size: 16px; line-height: 1.45; font-weight: 600; color: var(--bq-act); }
.k-empty { margin: 0; font-size: 16px; line-height: 1.4; color: var(--bq-text-3); }
.k-voice { gap: 10px; }
.k-voice .head { display: flex; align-items: center; gap: 10px; font-size: 16px; color: var(--bq-text-3); }
.k-voice .q { font-size: 18px; color: var(--bq-text-2); }
.k-voice .a { font-size: 22px; font-weight: 700; line-height: 1.3; }

/* touch-backup sheets over the board (override chooser, runner QR code) */
.k-sheet { position: absolute !important; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 820px !important;
  max-height: 900px; z-index: 50; background: var(--bq-surface) !important; border: 2px solid var(--bq-border-strong) !important;
  border-radius: 22px !important; padding: 32px !important; gap: 20px !important; box-shadow: 0 0 0 4000px rgba(5, 8, 9, 0.72) !important; }
.k-sheet-title { margin: 0; font-size: 34px; font-weight: 800; color: var(--bq-text); }
.k-sheet-text { margin: 0; font-size: 20px; line-height: 1.4; color: var(--bq-text-2); }
.k-sheet-qr { width: 280px; height: 280px; border-radius: 14px; background: #FFFFFF; padding: 8px; }
.k-sheet .k-field label > span, .k-sheet .k-field [data-testid="block-info"] { font-size: 20px !important; font-weight: 700 !important;
  color: var(--bq-text-2) !important; }
.k-sheet .k-field input, .k-sheet .k-field .wrap-inner, .k-sheet .k-field .secondary-wrap { font-size: 22px !important; min-height: 56px;
  color: var(--bq-text) !important; background: var(--bq-raised) !important; }
.k-sheet .k-field .wrap { gap: 10px !important; }
.k-sheet .k-choice label { min-height: 56px; font-size: 20px !important; background: var(--bq-raised) !important;
  border: 2px solid var(--bq-border-strong) !important; color: var(--bq-text) !important; border-radius: 14px !important; padding: 0 16px !important; }
.k-sheet .k-choice label { position: relative; }
.k-sheet .k-choice label input { position: absolute; inset: 0; width: 100% !important; height: 100% !important; margin: 0 !important;
  opacity: 0; cursor: pointer; }
.k-sheet .k-choice label span { margin: 0 !important; color: inherit !important; }
.k-sheet .k-choice label:has(input:focus-visible) { outline: 3px solid var(--bq-brand); outline-offset: 2px; }
.k-sheet .k-choice label.selected, .k-sheet .k-choice label:has(input:checked) { border-color: var(--bq-act) !important; }
.k-sheet-buttons { display: grid !important; grid-template-columns: 1fr 1fr; gap: 16px !important; }
.bq-kitchen .bq-btn.k-sheet-primary, .bq-kitchen .bq-btn.k-sheet-secondary { min-height: 72px; border-radius: 16px !important;
  font-size: 24px !important; font-weight: 800 !important; }
.bq-kitchen .bq-btn.k-sheet-primary { background: var(--bq-act) !important; color: var(--bq-act-ink) !important; border: none !important; }
.bq-kitchen .bq-btn.k-sheet-secondary { background: var(--bq-raised) !important; color: var(--bq-text) !important;
  border: 2px solid var(--bq-border-strong) !important; }
#bq-strip .bq-btn { height: 96px !important; min-height: 96px; border-radius: 18px !important; border: 2px solid var(--bq-border-strong) !important;
  background: var(--bq-raised) !important; color: var(--bq-text) !important; font-size: 26px !important; font-weight: 700 !important;
  gap: 14px; --bq-ico: 30px; padding: 0 16px !important; }
#bq-strip .bq-btn.bq-primary { background: var(--bq-act) !important; border-color: var(--bq-act) !important;
  color: var(--bq-act-ink) !important; font-weight: 800 !important; }
#bq-strip .bq-btn:hover { border-color: var(--bq-text-3) !important; }
#bq-strip .bq-btn.bq-primary:hover { filter: brightness(1.05); }
"""

# ---- Phone pages: runner (dark) and guest (light). 390 x 844 design frame. ----
PHONE_CSS = """
.bq-phone { width: 100%; max-width: 480px; margin: 0 auto !important; min-height: 100dvh;
  padding: 24px 20px 28px !important; display: flex !important; flex-direction: column !important; flex-wrap: nowrap !important; }
.bq-phone > .bq-view { flex: 1 1 auto !important; display: flex !important; flex-direction: column !important; min-height: 0; }
.bq-phone > .bq-view.hidden, .bq-phone .hidden { display: none !important; }
.bq-gap-18 { gap: 18px !important; } .bq-gap-16 { gap: 16px !important; } .bq-gap-14 { gap: 14px !important; }
.bq-gap-10 { gap: 10px !important; } .bq-gap-8 { gap: 8px !important; }
.bq-spacer { flex: 1 1 auto !important; min-height: 8px; }
.bq-between { display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 12px !important; }
.bq-between > * { flex: none !important; width: auto !important; }
.bq-link-btn { background: transparent !important; border: none !important; min-height: 44px; padding: 0 !important;
  font-size: 16px !important; font-weight: 600 !important; text-decoration: underline; text-underline-offset: 3px; }

/* runner, dark */
.r-head h1 { margin: 0; font-size: 26px !important; font-weight: 800 !important; line-height: 1.2 !important; color: var(--bq-text) !important; }
.r-head { display: flex; flex-direction: column; gap: 4px; }
.r-head .sub { font-size: 14px; color: var(--bq-text-3); }
.r-pill { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: var(--bq-brand);
  background: var(--bq-surface); border: 1px solid var(--bq-border); border-radius: 999px; padding: 8px 12px; white-space: nowrap; }
.r-pill i { width: 8px; height: 8px; border-radius: 4px; background: var(--bq-ok); display: inline-block; }
.r-pill.basic { color: var(--bq-act); } .r-pill.basic i { background: var(--bq-act); }
.r-pill.offline { color: var(--bq-empty); } .r-pill.offline i { background: var(--bq-empty); }
.bq-kitchen .bq-link-btn { color: var(--bq-brand) !important; }
.bq-kitchen .bq-link-btn:hover { color: var(--bq-brand-hover) !important; }
.bq-kitchen .bq-btn.r-secondary { min-height: 44px; background: var(--bq-surface) !important; color: var(--bq-text) !important;
  border: 1px solid var(--bq-border-strong) !important; border-radius: 12px !important; padding: 0 14px !important;
  font-size: 15px !important; font-weight: 600 !important; }
.bq-kitchen .bq-btn.r-primary { min-height: 64px; border-radius: 16px !important; background: var(--bq-act) !important;
  color: var(--bq-act-ink) !important; border: none !important; font-size: 20px !important; font-weight: 800 !important; width: 100%; }
.bq-kitchen .bq-btn.r-raised { min-height: 52px; border-radius: 14px !important; border: 2px solid var(--bq-border-strong) !important;
  background: var(--bq-raised) !important; color: var(--bq-text) !important; font-size: 16px !important; font-weight: 700 !important; width: 100%; padding: 0 8px !important; white-space: nowrap; }
.bq-kitchen .bq-btn.r-back { min-height: 44px; background: transparent !important; border: none !important; padding: 0 !important;
  color: var(--bq-brand) !important; font-size: 16px !important; font-weight: 600 !important; gap: 6px; --bq-ico: 20px; justify-content: flex-start; }
.r-label { font-size: 14px; color: var(--bq-text-3); }

/* chips: real radio inputs styled as buttons */
.r-chips .wrap { display: grid !important; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px !important; }
.r-chips label { position: relative; min-height: 56px; margin: 0 !important; border-radius: 14px !important;
  border: 2px solid var(--bq-border-strong) !important; background: var(--bq-surface) !important; color: var(--bq-text) !important;
  display: flex !important; align-items: center; justify-content: center; text-align: center; padding: 6px 8px !important;
  font-size: 15px !important; font-weight: 700 !important; line-height: 1.2; cursor: pointer; box-shadow: none !important; }
.r-chips label input { position: absolute; inset: 0; width: 100% !important; height: 100% !important; margin: 0 !important; opacity: 0; cursor: pointer; }
.r-chips label span { margin: 0 !important; color: inherit !important; }
.r-chips label.selected, .r-chips label:has(input:checked) { background: var(--bq-brand) !important; border-color: var(--bq-brand) !important;
  color: var(--bq-brand-ink) !important; }
.r-chips label:has(input:focus-visible) { outline: 3px solid var(--bq-text); outline-offset: 2px; }

.r-viewfinder { position: relative; height: 360px; border-radius: 22px; background: var(--bq-viewfinder); border: 1px solid var(--bq-border);
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; overflow: hidden; }
.r-viewfinder .c { position: absolute; width: 34px; height: 34px; border: 0 solid var(--bq-brand); }
.r-viewfinder .tl { top: 18px; left: 18px; border-top-width: 4px; border-left-width: 4px; border-radius: 6px 0 0 0; }
.r-viewfinder .tr { top: 18px; right: 18px; border-top-width: 4px; border-right-width: 4px; border-radius: 0 6px 0 0; }
.r-viewfinder .bl { bottom: 18px; left: 18px; border-bottom-width: 4px; border-left-width: 4px; border-radius: 0 0 0 6px; }
.r-viewfinder .br { bottom: 18px; right: 18px; border-bottom-width: 4px; border-right-width: 4px; border-radius: 0 0 6px 0; }
.r-viewfinder .tray { width: 240px; max-width: 70%; height: 150px; border: 2px dashed var(--bq-forecast); border-radius: 14px;
  display: flex; align-items: center; justify-content: center; font-size: 15px; color: var(--bq-text-3); text-align: center; padding: 8px; }
.r-viewfinder .hint { font-size: 17px; font-weight: 600; }
.r-viewfinder .hint2 { font-size: 14px; color: var(--bq-text-3); }

.r-photo { height: 170px; border-radius: 18px; background: var(--bq-viewfinder); border: 1px solid var(--bq-border);
  display: flex; align-items: center; justify-content: center; font-size: 15px; color: var(--bq-text-3); overflow: hidden; }
.r-photo img { width: 100%; height: 100%; object-fit: cover; }
.r-result { background: var(--bq-surface); border: 2px solid var(--bq-border); border-radius: 20px; padding: 18px;
  display: flex; flex-direction: column; gap: 14px; }
.r-result.act { border-color: var(--bq-act); } .r-result.empty { border-color: var(--bq-empty); } .r-result.ok { border-color: var(--bq-ok); }
.r-result .lvl { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.r-result .word { display: flex; align-items: center; gap: 10px; font-size: 48px; font-weight: 800; line-height: 1; }
.r-result .sure { font-size: 15px; font-weight: 700; color: var(--bq-bg); background: var(--bq-text-2); border-radius: 999px; padding: 6px 12px; white-space: nowrap; }
.r-result .est { font-size: 18px; color: var(--bq-text-2); }
.r-scale { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }
.r-scale > div { display: flex; flex-direction: column; gap: 6px; align-items: center; }
.r-scale i { width: 100%; height: 10px; border-radius: 5px; background: var(--bq-border); display: block; }
.r-scale span { font-size: 14px; color: var(--bq-text-3); }
.r-scale .on span { font-weight: 800; }
.r-scale .on i.lv-act-bg { background: var(--bq-act); } .r-scale .on i.lv-ok-bg { background: var(--bq-ok); } .r-scale .on i.lv-empty-bg { background: var(--bq-empty); }
.r-scale .on span.lv-act { color: var(--bq-act); } .r-scale .on span.lv-ok { color: var(--bq-ok); } .r-scale .on span.lv-empty { color: var(--bq-empty); }
.r-unsure .title { font-size: 28px; font-weight: 800; color: var(--bq-act); display: flex; align-items: center; gap: 10px; }
.r-done { background: var(--bq-surface); border: 1px solid var(--bq-border); border-radius: 18px; padding: 16px 18px;
  display: flex; align-items: center; gap: 14px; }
.r-done .tick { flex: none; width: 40px; height: 40px; border-radius: 20px; background: var(--bq-ok); color: var(--bq-brand-ink);
  display: flex; align-items: center; justify-content: center; }
.r-done .txt { display: flex; flex-direction: column; gap: 2px; }
.r-done .small { font-size: 15px; color: var(--bq-text-3); }
.r-done .big { font-size: 19px; font-weight: 700; line-height: 1.25; }
/* the photo input is opened by "Check tray"; it stays in the page but out of sight */
.r-photo-input { position: absolute !important; left: -9999px !important; width: 1px !important; height: 1px !important;
  overflow: hidden !important; opacity: 0 !important; }
.bq-kitchen .bq-btn.r-small-link { font-size: 15px !important; min-height: 44px; margin-top: -8px; }
.bq-kitchen .bq-btn.r-level { min-height: 64px; width: 100%; border-radius: 16px !important; background: var(--bq-surface) !important;
  border: 2px solid var(--bq-border-strong) !important; font-size: 22px !important; font-weight: 800 !important;
  justify-content: flex-start; padding: 0 20px !important; gap: 14px; --bq-ico: 28px; }
.bq-kitchen .bq-btn.r-level-full, .bq-kitchen .bq-btn.r-level-half { color: var(--bq-ok) !important; }
.bq-kitchen .bq-btn.r-level-low { color: var(--bq-act) !important; }
.bq-kitchen .bq-btn.r-level-empty { color: var(--bq-empty) !important; }
.bq-kitchen .bq-btn.r-level:hover { border-color: var(--bq-text-3) !important; }
.r-unsure { gap: 10px !important; }
.r-unsure .est { font-size: 16px; line-height: 1.45; }
.r-model-note { margin-top: -4px !important; }
.r-two { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px !important; }

.r-said { align-self: flex-end; max-width: 88%; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; margin-left: auto; }
.r-said .meta { font-size: 13px; color: var(--bq-text-3); }
.r-said .bubble { background: var(--bq-raised); border: 1px solid var(--bq-border-strong); border-radius: 18px 18px 4px 18px;
  padding: 12px 16px; font-size: 17px; line-height: 1.4; }
.r-answer { background: var(--bq-surface) !important; border: 2px solid var(--bq-act) !important; border-radius: 20px !important;
  padding: 18px !important; display: flex !important; flex-direction: column !important; gap: 12px !important; }
.r-answer .kicker { font-size: 13px; font-weight: 600; color: var(--bq-act); }
.r-answer .main { font-size: 28px; font-weight: 800; line-height: 1.15; }
.r-answer .more { font-size: 17px; line-height: 1.45; color: var(--bq-text-2); }
.r-answer .same { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--bq-brand); }
.r-answer .same svg { flex: none; }
.r-answer-foot { padding-top: 4px; }
.r-answer-foot > :first-child { flex: 1 1 auto !important; }
.bq-kitchen .bq-btn.r-replay { min-height: 44px; background: var(--bq-raised) !important; color: var(--bq-text) !important;
  border: 1px solid var(--bq-border-strong) !important; border-radius: 12px !important; padding: 0 14px !important;
  font-size: 15px !important; font-weight: 600 !important; gap: 8px; --bq-ico: 18px; }
.r-try { display: flex !important; flex-wrap: nowrap !important; gap: 8px !important; overflow-x: auto !important;
  padding-bottom: 2px; scrollbar-width: none; margin-right: -20px; padding-right: 20px; }
.r-try::-webkit-scrollbar { display: none; }
.bq-kitchen .r-try .bq-btn { flex: none !important; min-height: 44px; background: var(--bq-surface) !important; color: var(--bq-text) !important;
  border: 1px solid var(--bq-border-strong) !important; border-radius: 999px !important; padding: 0 16px !important;
  font-size: 15px !important; font-weight: 400 !important; white-space: nowrap; width: auto !important; }
.r-mic-wrap { display: flex !important; flex-direction: column !important; align-items: center !important; gap: 8px !important; }
.bq-kitchen .bq-btn.r-mic { width: 132px !important; height: 132px !important; border-radius: 66px !important; border: 6px solid var(--bq-act-ring) !important;
  background: var(--bq-act) !important; color: var(--bq-act-ink) !important; flex-direction: column; gap: 6px; font-size: 17px !important;
  font-weight: 800 !important; --bq-ico: 32px; padding: 0 !important; flex: none !important; }

/* bottom switch between Tray check and Ask BuffetIQ (the one addition to the designs) */
.r-switch { margin-top: 16px !important; flex: none !important; }
.r-switch .wrap { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px !important;
  background: var(--bq-surface); border: 1px solid var(--bq-border); border-radius: 16px; padding: 4px; }
.r-switch label { position: relative; min-height: 48px; margin: 0 !important; border-radius: 12px !important; border: none !important;
  background: transparent !important; color: var(--bq-text-2) !important; display: flex !important; align-items: center; justify-content: center;
  font-size: 15px !important; font-weight: 700 !important; cursor: pointer; box-shadow: none !important; padding: 0 8px !important; }
.r-switch label input { position: absolute; inset: 0; width: 100% !important; height: 100% !important; margin: 0 !important; opacity: 0; cursor: pointer; }
.r-switch label span { margin: 0 !important; color: inherit !important; }
.r-switch label.selected, .r-switch label:has(input:checked) { background: var(--bq-raised) !important; color: var(--bq-text) !important;
  box-shadow: inset 0 0 0 1px var(--bq-border-strong) !important; }
.r-switch label:has(input:focus-visible) { outline: 3px solid var(--bq-brand); outline-offset: 1px; }
.bq-note { font-size: 13px; line-height: 1.2; color: var(--bq-text-3); text-align: center; margin-top: 6px !important; }
.bq-guest .bq-note { color: var(--bq-muted); }

/* guest, light */
.g-head { display: flex; align-items: center; justify-content: space-between; }
.g-hotel { font-family: __SERIF__; font-size: 22px; font-weight: 600; color: var(--bq-teal); }
.g-step { font-size: 13px; font-weight: 600; color: var(--bq-teal); background: var(--bq-teal-tint); border-radius: 999px; padding: 6px 12px; white-space: nowrap; }
.g-title { display: flex; flex-direction: column; gap: 6px; }
.g-title h1 { margin: 0; font-family: __SERIF__ !important; font-size: 32px !important; font-weight: 600 !important; line-height: 1.1 !important; color: var(--bq-text) !important; }
.g-title h1.t30 { font-size: 30px !important; }
.g-title p { margin: 0; font-size: 15px; line-height: 1.5; color: var(--bq-muted); }
.g-title p.small { font-size: 14px; line-height: 1.3; }
.g-card { background: var(--bq-surface) !important; border: 1px solid var(--bq-border) !important; border-radius: 20px !important;
  padding: 18px !important; display: flex !important; flex-direction: column !important; gap: 18px !important; }
.g-q { font-size: 16px; font-weight: 700; color: var(--bq-text); }
.g-q .opt { font-weight: 400; color: var(--bq-muted); }
.g-toggle .wrap { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px !important; margin-top: 10px; }
.g-toggle label { position: relative; min-height: 48px; margin: 0 !important; border-radius: 12px !important; border: 2px solid var(--bq-border-strong) !important;
  background: var(--bq-surface) !important; color: var(--bq-text) !important; display: flex !important; align-items: center; justify-content: center;
  font-size: 16px !important; font-weight: 700 !important; cursor: pointer; box-shadow: none !important; padding: 0 8px !important; }
.g-toggle label input { position: absolute; inset: 0; width: 100% !important; height: 100% !important; margin: 0 !important; opacity: 0; cursor: pointer; }
.g-toggle label span { margin: 0 !important; color: inherit !important; }
.g-toggle label.selected, .g-toggle label:has(input:checked) { background: var(--bq-teal) !important; border-color: var(--bq-teal) !important; color: #FFFFFF !important; }
.g-toggle label:has(input:focus-visible), .g-slots label:has(input:focus-visible) { outline: 3px solid var(--bq-teal-dark); outline-offset: 2px; }
.g-room label { display: flex; flex-direction: column; gap: 8px; }
.g-room [data-testid="block-info"] { position: static !important; width: auto !important; height: auto !important; clip: auto !important;
  margin: 0 !important; overflow: visible !important; font-size: 16px !important; font-weight: 700 !important; color: var(--bq-text) !important; white-space: normal; }
.g-room input, .g-room textarea { min-height: 48px !important; height: 48px !important; border-radius: 12px !important; border: 1.5px solid var(--bq-border-strong) !important;
  background: var(--bq-surface) !important; padding: 0 14px !important; font-size: 17px !important; color: var(--bq-text) !important; box-shadow: none !important;
  font-family: __FONT__ !important; line-height: 46px !important; resize: none; }
.g-room .input-container { background: transparent !important; }
.g-stepper { display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 12px !important; }
.g-stepper > :first-child { flex: 1 1 auto !important; }
.g-stepper > * { flex: none !important; width: auto !important; }
.g-stepper .lbl { font-size: 16px; font-weight: 700; }
.g-stepper.diet .lbl { font-size: 15px; font-weight: 400; }
.g-stepper .count { min-width: 28px; text-align: center; font-size: 22px; font-weight: 700; margin: 0 10px; }
.g-stepper.diet .count { min-width: 24px; font-size: 18px; }
.bq-guest .bq-btn.g-step-btn { width: 44px !important; height: 44px !important; min-height: 44px; border-radius: 22px !important; padding: 0 !important;
  border: 1.5px solid var(--bq-border-strong) !important; background: var(--bq-surface) !important; color: var(--bq-teal) !important;
  font-size: 22px !important; font-weight: 700 !important; flex: none !important; }
.g-stepper.diet .bq-btn.g-step-btn { font-size: 20px !important; }
.bq-guest .bq-btn.g-step-btn.on { background: var(--bq-teal) !important; border-color: var(--bq-teal) !important; color: #FFFFFF !important; }
.g-diet { border-top: 1px solid var(--bq-divider) !important; padding-top: 16px !important; gap: 10px !important; }
.bq-guest .bq-btn.g-primary { min-height: 56px; border-radius: 16px !important; background: var(--bq-teal) !important; color: #FFFFFF !important;
  border: none !important; font-size: 18px !important; font-weight: 700 !important; width: 100%; }
.bq-guest .bq-btn.g-primary:hover { background: var(--bq-teal-dark) !important; }
.bq-guest .bq-btn.g-secondary { min-height: 52px; border-radius: 16px !important; background: var(--bq-surface) !important; color: var(--bq-teal) !important;
  border: 2px solid var(--bq-teal) !important; font-size: 17px !important; font-weight: 700 !important; width: 100%; }
.bq-guest .bq-btn.g-back { min-height: 44px; background: transparent !important; border: none !important; padding: 0 !important;
  color: var(--bq-teal) !important; font-size: 15px !important; font-weight: 600 !important; gap: 6px; --bq-ico: 20px; justify-content: flex-start; }
.g-error { margin: 0; font-size: 14px; line-height: 1.4; font-weight: 600; color: var(--bq-error); }
.g-privacy { margin: 0; font-size: 13px; line-height: 1.5; color: var(--bq-muted); text-align: center; }

/* time slots: a real radio group; bar and crowd word come from CSS variables per row */
.g-slots .wrap { display: flex !important; flex-direction: column !important; gap: 4px !important; }
.g-slots label { position: relative; min-height: 46px; margin: 0 !important; display: grid !important;
  grid-template-columns: 64px minmax(0, 1fr) 84px; align-items: center; gap: 12px; padding: 0 12px !important; border-radius: 12px !important;
  border: 2px solid var(--bq-border) !important; background: var(--bq-surface) !important; color: var(--bq-text) !important;
  cursor: pointer; box-shadow: none !important; }
.g-slots label input { position: absolute; inset: 0; width: 100% !important; height: 100% !important; margin: 0 !important; opacity: 0; cursor: pointer; }
.g-slots label span { margin: 0 !important; grid-column: 1; grid-row: 1; font-size: 16px !important; font-weight: 700 !important; color: var(--bq-text) !important; }
.g-slots label::before { content: ''; grid-column: 2; grid-row: 1; height: 10px; border-radius: 5px;
  background-color: var(--bq-divider); background-image: linear-gradient(var(--c, #7FC4BA), var(--c, #7FC4BA));
  background-size: var(--w, 30%) 100%; background-repeat: no-repeat; background-position: left center; }
.g-slots label::after { content: var(--word, ''); grid-column: 3; grid-row: 1; text-align: right; font-size: 14px; font-weight: 600; color: var(--wc, #2E6E65); }
.g-slots label.selected, .g-slots label:has(input:checked) { border-color: var(--bq-teal) !important; background: var(--bq-teal-tint) !important; }
.g-tip { background: var(--bq-tip-bg) !important; border: 1.5px solid var(--bq-saffron) !important; border-radius: 16px !important;
  padding: 14px 16px !important; display: flex !important; flex-direction: column !important; gap: 10px !important; }
.g-tip .t { font-size: 16px; font-weight: 700; color: var(--bq-tip-title); }
.g-tip .b { font-size: 14px; line-height: 1.45; color: var(--bq-tip-body); }
.g-tip .txt { display: flex; flex-direction: column; gap: 2px; }
.g-tip.big .b { font-size: 15px; line-height: 1.5; }
.g-tip.big .txt { gap: 6px; }
.bq-guest .bq-btn.g-tip-btn { min-height: 44px; align-self: flex-start; width: auto !important; border-radius: 12px !important;
  border: 1.5px solid var(--bq-tip-button-border) !important; background: #FFFFFF !important; color: var(--bq-tip-title) !important;
  padding: 0 16px !important; font-size: 15px !important; font-weight: 700 !important; }
.g-done { display: flex; flex-direction: column; align-items: center; gap: 12px; padding-top: 8px; text-align: center; }
.g-done .circle { width: 72px; height: 72px; border-radius: 36px; background: var(--bq-teal); color: #FFFFFF; display: flex; align-items: center; justify-content: center; }
.g-done h1 { margin: 0; font-family: __SERIF__ !important; font-size: 32px !important; font-weight: 600 !important; color: var(--bq-text) !important; line-height: 1.2 !important; }
.g-done p { margin: 0; font-size: 15px; color: var(--bq-muted); }
.g-details { background: var(--bq-surface); border: 1px solid var(--bq-border); border-radius: 20px; padding: 6px 18px; }
.g-details .item { display: flex; align-items: center; gap: 14px; padding: 14px 0; border-bottom: 1px solid var(--bq-divider); }
.g-details .item:last-child { border-bottom: none; }
.g-details svg { flex: none; }
.g-details .txt { display: flex; flex-direction: column; gap: 2px; }
.g-details .k { font-size: 13px; color: var(--bq-muted); }
.g-details .v { font-size: 17px; font-weight: 700; }
.g-quiet { margin: 0; font-size: 13px; line-height: 1.5; color: var(--bq-muted); text-align: center; }
"""

# ---- Day-end report (screen 08) and About page: light, fluid laptop layout. ----
REPORT_CSS = """
.bq-wide { padding: 32px 24px 28px !important; min-height: 100dvh; }
.bq-wide-inner { max-width: 1280px; width: 100%; margin: 0 auto !important; display: flex !important; flex-direction: column !important; gap: 24px !important; }
.rp-header { display: flex !important; flex-wrap: wrap !important; align-items: flex-end !important; justify-content: space-between !important; gap: 16px !important; }
.rp-header > :first-child { flex: 1 1 auto !important; width: auto !important; }
.rp-title { display: flex; flex-direction: column; gap: 6px; }
.rp-title .brand { font-size: 15px; font-weight: 800; color: var(--bq-teal); }
.rp-title h1 { margin: 0; font-size: 34px !important; font-weight: 800 !important; letter-spacing: -0.01em; line-height: 1.2 !important; color: var(--bq-text) !important; }
.rp-title .sub { font-size: 15px; color: var(--bq-muted); }
.rp-actions { display: flex !important; flex-wrap: wrap !important; gap: 10px !important; flex: 0 1 auto !important; width: auto !important; max-width: 100%; }
.rp-actions > * { flex: none !important; width: auto !important; }
.bq-guest .bq-btn.rp-secondary, .bq-guest .rp-secondary button, .bq-guest a.rp-secondary { min-height: 48px; border-radius: 12px !important; border: 1.5px solid var(--bq-border-strong) !important;
  background: #FFFFFF !important; color: var(--bq-text) !important; padding: 0 18px !important; font-size: 15px !important; font-weight: 700 !important; gap: 8px; --bq-ico: 18px; }
.bq-guest .bq-btn.rp-primary { min-height: 48px; border-radius: 12px !important; border: 1.5px solid var(--bq-teal) !important;
  background: var(--bq-teal) !important; color: #FFFFFF !important; padding: 0 18px !important; font-size: 15px !important; font-weight: 700 !important; gap: 8px; --bq-ico: 18px; }
.bq-guest .bq-btn.rp-primary:hover { background: var(--bq-teal-dark) !important; }
.rp-body { display: flex; flex-direction: column; gap: 24px; }
.rp-figures { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
.rp-card { background: var(--bq-surface); border: 1px solid var(--bq-border); border-radius: 18px; padding: 18px 20px; display: flex; flex-direction: column; gap: 6px; }
.rp-card .k { font-size: 14px; color: var(--bq-muted); }
.rp-card .v { font-size: 36px; font-weight: 800; line-height: 1.2; }
.rp-card .c { font-size: 14px; color: var(--bq-muted); line-height: 1.4; }
.rp-card .c.good { color: var(--bq-teal); font-weight: 600; }
.rp-split { display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start; }
.rp-left { flex: 999 1 640px; min-width: 0; }
.rp-right { flex: 1 1 320px; min-width: 0; display: flex; flex-direction: column; gap: 20px; }
.rp-panel { background: var(--bq-surface); border: 1px solid var(--bq-border); border-radius: 18px; padding: 20px 22px; display: flex; flex-direction: column; gap: 14px; }
.rp-panel h2 { margin: 0; font-size: 20px !important; font-weight: 800 !important; line-height: 1.25 !important; color: var(--bq-text) !important; }
.rp-panel .ph { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 10px; }
.rp-legend { display: flex; gap: 16px; font-size: 13px; color: var(--bq-muted); }
.rp-legend span { display: flex; align-items: center; gap: 6px; }
.rp-legend i { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
.rp-scroll { overflow-x: auto; }
.rp-table { min-width: 620px; display: flex; flex-direction: column; font-size: 15px; }
.rp-row { display: grid; grid-template-columns: minmax(150px, 1.4fr) 90px 90px 80px minmax(200px, 2fr); gap: 0 8px; align-items: center; border-bottom: 1px solid var(--bq-divider); }
.rp-row > span { padding: 10px 0; }
.rp-row .num { text-align: right; }
.rp-row.head { color: var(--bq-muted); font-size: 13px; font-weight: 600; border-bottom: 1px solid var(--bq-border); }
.rp-row.total { font-weight: 800; border-bottom: none; }
.rp-row.total > span { padding: 12px 0; }
.rp-row .bars { padding: 8px 0 8px 12px !important; display: flex; flex-direction: column; gap: 4px; }
.rp-row .bars > span { display: flex; align-items: center; gap: 8px; }
.rp-row .bars i { height: 10px; border-radius: 5px; display: block; }
.rp-row .bars b { font-size: 13px; font-weight: 400; }
.rp-events { display: flex; flex-direction: column; gap: 14px; }
.rp-event { display: flex; flex-direction: column; gap: 2px; }
.rp-event .t { font-size: 15px; font-weight: 700; }
.rp-event .d { font-size: 14px; line-height: 1.45; color: var(--bq-muted); }
.rp-learn .sub { font-size: 14px; color: var(--bq-muted); }
.rp-learn-bars { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; align-items: end; height: 130px; }
.rp-learn-bars > div { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 6px; height: 130px; }
.rp-learn-bars b { font-size: 13px; font-weight: 700; }
.rp-learn-bars i { width: 100%; border-radius: 6px 6px 0 0; display: block; }
.rp-learn-axis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; font-size: 13px; color: var(--bq-muted); text-align: center; }
.rp-status { margin: 0; font-size: 15px; font-weight: 600; color: var(--bq-teal); background: var(--bq-teal-tint);
  border-radius: 12px; padding: 12px 16px; }
.rp-foot { margin: 0; font-size: 13px; line-height: 1.5; color: var(--bq-muted); }

.ab-section { background: var(--bq-surface); border: 1px solid var(--bq-border); border-radius: 18px; padding: 20px 22px; display: flex; flex-direction: column; gap: 12px; }
.ab-section h2 { margin: 0; font-size: 20px !important; font-weight: 800 !important; color: var(--bq-text) !important; line-height: 1.25 !important; }
.ab-section p { margin: 0; font-size: 15px; line-height: 1.55; color: var(--bq-text); }
.ab-section p.muted { color: var(--bq-muted); }
.ab-links { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.ab-link { display: flex; flex-direction: column; align-items: flex-start; text-align: left; gap: 4px; border: 1px solid var(--bq-border); border-radius: 14px; padding: 14px 16px; min-height: 44px;
  text-decoration: none !important; color: var(--bq-text) !important; background: var(--bq-bg); }
.ab-link:hover { border-color: var(--bq-teal); }
.ab-link .n { font-size: 16px; font-weight: 700; color: var(--bq-teal); }
.ab-link .p { font-size: 13px; color: var(--bq-muted); }
.ab-link .d { font-size: 14px; line-height: 1.45; color: var(--bq-muted); }
.ab-qr { gap: 14px !important; }
.ab-presenter { gap: 14px !important; }
.ab-status { margin: 0; font-size: 15px; line-height: 1.5; color: var(--bq-text); background: var(--bq-teal-tint);
  border-radius: 12px; padding: 12px 16px; }
.ab-pass { min-width: 260px !important; }
.ab-pass input { min-height: 48px !important; height: 48px !important; border-radius: 12px !important;
  border: 1.5px solid var(--bq-border-strong) !important; background-color: var(--bq-surface) !important; padding: 0 14px !important;
  font-size: 17px !important; color: var(--bq-text) !important; box-shadow: none !important; }
.ab-pass .input-container { background-color: transparent !important; }
.ab-lock-note { margin: 4px 0 0; font-size: 15px; line-height: 1.5; color: var(--bq-text); }
.ab-controls { align-items: flex-end !important; }
.ab-field { min-width: 180px !important; }
.ab-speed .wrap { gap: 8px !important; }
.ab-speed label { min-height: 44px; border-radius: 12px !important; }
.ab-qr-link { margin: 0; font-size: 15px; color: var(--bq-text); word-break: break-all; }
.ab-qr-image { max-width: 320px; background: #FFFFFF !important; border: 1px solid var(--bq-border) !important; border-radius: 14px !important; }
.bq-guest code { font-size: 14px; background: var(--bq-divider); padding: 1px 6px; border-radius: 6px; }
.bq-guest a { color: var(--bq-teal); } .bq-guest a:hover { color: var(--bq-teal-dark); }
"""


def build_css() -> str:
    css = "\n".join(
        [
            _vars(".bq-kitchen", KITCHEN),
            _vars(".bq-guest", GUEST),
            BASE_CSS,
            KITCHEN_BOARD_CSS,
            PHONE_CSS,
            REPORT_CSS,
            _icon_button_css(),
        ]
    )
    return css.replace("__FONT__", FONT_STACK).replace("__SERIF__", SERIF_STACK)


CSS = build_css()

# ---------------------------------------------------------------------------
# Page JavaScript: board scaling and accessible names for icon-only buttons
# ---------------------------------------------------------------------------

# Gradio buttons cannot take an aria-label argument, so these are applied in the
# browser by element id. Every icon-only or symbol-only button must be listed.
ARIA_LABELS = {
    "g-party-minus": "One fewer guest",
    "g-party-plus": "One more guest",
    "g-halal-minus": "One fewer halal meal",
    "g-halal-plus": "One more halal meal",
    "g-veg-minus": "One fewer vegetarian meal",
    "g-veg-plus": "One more vegetarian meal",
    "r-replay": "Replay spoken answer",
}


HF_BADGE_BAND = 56   # px kept clear above the kitchen board for the Hugging Face badge


def build_js() -> str:
    import json

    labels = json.dumps(ARIA_LABELS)
    return f"""
() => {{
  const labels = {labels};
  const fit = () => {{
    const board = document.getElementById('bq-board');
    if (!board) return;
    // On a Hugging Face Space opened directly, the Hub's badge sits over the top right corner,
    // so keep a band clear for it (not inside the Space page's own frame, which has no badge).
    const top = (location.hostname.endsWith('.hf.space') && window.self === window.top) ? {HF_BADGE_BAND} : 0;
    const h = window.innerHeight - top;
    const s = Math.min(window.innerWidth / {BOARD_W}, h / {BOARD_H});
    const x = (window.innerWidth - {BOARD_W} * s) / 2, y = top + (h - {BOARD_H} * s) / 2;
    board.style.setProperty('--bq-board-scale', s);
    board.style.setProperty('--bq-board-x', x + 'px');
    board.style.setProperty('--bq-board-y', y + 'px');
  }};
  const label = () => {{
    for (const [id, text] of Object.entries(labels)) {{
      const el = document.getElementById(id);
      if (el && el.getAttribute('aria-label') !== text) el.setAttribute('aria-label', text);
    }}
  }};
  const tick = () => {{ fit(); label(); }};
  window.addEventListener('resize', fit);
  new MutationObserver(tick).observe(document.body, {{ childList: true, subtree: true }});
  tick();
}}
"""


JS = build_js()
