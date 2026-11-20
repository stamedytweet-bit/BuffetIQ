"""Phase 0 checks: configuration, style tokens, copy rules and that every page builds."""

import re
from pathlib import Path

import pytest

from buffetiq import state, style
from buffetiq.ui import about, guest, kitchen, report, runner, sample

ROOT = Path(__file__).resolve().parents[1]

DISH_ORDER = ["Scrambled eggs", "Chicken sausages", "Hash browns", "Pancakes",
              "Mee goreng", "Nasi lemak rice", "Croissants", "Cut fruit"]
STATIONS = {"Scrambled eggs": "Hot station 1", "Chicken sausages": "Hot station 1",
            "Hash browns": "Hot station 1", "Mee goreng": "Hot station 2",
            "Nasi lemak rice": "Hot station 2", "Pancakes": "Live station",
            "Croissants": "Bakery", "Cut fruit": "Cold station"}


# ---- configuration ----

def test_config_has_eight_dishes_in_board_order():
    assert state.dish_names() == DISH_ORDER


@pytest.mark.parametrize("dish", state.load_config()["dishes"], ids=lambda d: d["id"])
def test_every_dish_has_the_required_fields(dish):
    for key in ("lead_minutes", "batch", "pan_capacity", "last_cook", "cost_per_kg",
                "halal", "vegetarian", "synonyms", "unit", "station"):
        assert key in dish, key
    assert dish["station"] == STATIONS[dish["name"]]
    assert dish["lead_minutes"] > 0 and dish["batch"] > 0 and dish["pan_capacity"] > 0
    assert re.fullmatch(r"\d\d:\d\d", dish["last_cook"])
    assert dish["synonyms"], "spoken synonyms are needed for Ask BuffetIQ"


def test_croissants_are_counted_in_pieces_with_a_weight():
    croissant = next(d for d in state.load_config()["dishes"] if d["name"] == "Croissants")
    assert croissant["unit"] == "pieces" and croissant["piece_kg"] > 0


def test_synonyms_do_not_point_to_two_dishes():
    seen = {}
    for d in state.load_config()["dishes"]:
        for s in d["synonyms"]:
            assert s not in seen, f"'{s}' is used by {seen.get(s)} and {d['name']}"
            seen[s] = d["name"]


# ---- style tokens ----

@pytest.mark.parametrize("token,value", [
    ("bg", "#0E1415"), ("surface", "#172123"), ("raised", "#1F2B2D"), ("border", "#2C3A3C"),
    ("border-strong", "#3C4D4F"), ("text", "#F4F1EA"), ("text-2", "#C9D1D0"), ("text-3", "#A9B4B3"),
    ("brand", "#7FD3C3"), ("ok", "#5BC0A8"), ("act", "#F2B33D"), ("act-ink", "#1A1300"),
    ("empty", "#FF6B5E"), ("forecast", "#6F8584"),
])
def test_kitchen_tokens_match_claude_md(token, value):
    assert style.KITCHEN[token] == value
    assert f"--bq-{token}:{value}" in style.CSS


@pytest.mark.parametrize("token,value", [
    ("bg", "#FAF8F4"), ("surface", "#FFFFFF"), ("border", "#E7E2D8"), ("border-strong", "#CFC8BA"),
    ("divider", "#EFEAE0"), ("text", "#1F2328"), ("muted", "#5F646B"), ("teal", "#0F6E6E"),
    ("teal-dark", "#0A4F4F"), ("teal-tint", "#E3F1EF"), ("crowd-quiet", "#7FC4BA"),
    ("crowd-moderate", "#3E938A"), ("crowd-busy", "#0F6E6E"), ("saffron", "#E0A030"),
    ("tip-bg", "#FFF4DD"), ("tip-title", "#3A2A00"), ("tip-body", "#5A4512"),
    ("chart-today", "#0F6E6E"), ("chart-usual", "#D9D3C7"), ("chart-earlier", "#9FC9C3"),
])
def test_guest_tokens_match_claude_md(token, value):
    assert style.GUEST[token] == value


def _luminance(hex_colour):
    rgb = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("fg,bg", [
    ("text", "bg"), ("text", "surface"), ("text-2", "surface"), ("text-3", "surface"), ("text-3", "bg"),
    ("brand", "surface"), ("ok", "surface"), ("act", "surface"), ("empty", "surface"),
    ("act-ink", "act"), ("empty-ink", "empty"), ("brand-ink", "brand"),
])
def test_kitchen_text_contrast_is_at_least_4_5(fg, bg):
    assert contrast(style.KITCHEN[fg], style.KITCHEN[bg]) >= 4.5


@pytest.mark.parametrize("fg,bg", [
    ("text", "bg"), ("muted", "bg"), ("muted", "surface"), ("teal", "surface"), ("teal", "teal-tint"),
    ("crowd-word", "surface"), ("crowd-word", "teal-tint"), ("teal-dark", "teal-tint"),
    ("tip-title", "tip-bg"), ("tip-body", "tip-bg"),
])
def test_guest_text_contrast_is_at_least_4_5(fg, bg):
    assert contrast(style.GUEST[fg], style.GUEST[bg]) >= 4.5


def test_white_on_teal_buttons_contrast():
    assert contrast("#FFFFFF", style.GUEST["teal"]) >= 4.5


# ---- copy rules ----

def all_rendered_html():
    return [
        kitchen.render_header(sample.KITCHEN_HEADER),
        kitchen.render_dishes(sample.KITCHEN_DISHES),
        kitchen.render_arrivals(sample.KITCHEN_ARRIVALS),
        kitchen.render_alerts(sample.KITCHEN_ALERTS),
        kitchen.render_voice(sample.KITCHEN_VOICE),
        runner.render_viewfinder("Scrambled eggs"),
        runner.render_result(sample.TRAY_RESULT),
        runner.render_board_updated(sample.TRAY_RESULT["board_call"]),
        runner.render_ask_head("08:40", "basic"),
        guest.render_intro("Wednesday 25 November", "06:30 to 10:30"),
        guest.render_confirmed("Wednesday 25 November", "09:30", 2, "1204"),
        report.render_body(sample.REPORT),
        about.render_about({"kitchen": "/", "runner": "/runner", "guest": "/guest", "report": "/report", "about": "/about"}),
    ]


def test_no_em_dashes_in_rendered_screens():
    for html in all_rendered_html():
        assert style.EM_DASH not in html


def test_check_copy_rejects_em_dashes():
    with pytest.raises(ValueError):
        style.check_copy("Cook now \u2014 quickly")


def test_no_em_dashes_in_project_text_files():
    for path in list(ROOT.glob("src/**/*.py")) + list(ROOT.glob("*.md")) + list(ROOT.glob("docs/*.md")) \
            + [ROOT / "config.yaml", ROOT / "app.py"]:
        assert style.EM_DASH not in path.read_text(encoding="utf-8"), path


def test_fictional_data_labels_present():
    assert "Fictional data" in sample.KITCHEN_HEADER["date_line"]
    assert "Simulated on fictional data" in sample.REPORT["date_line"]


def test_status_never_shown_by_colour_alone():
    html = kitchen.render_dishes(sample.KITCHEN_DISHES)
    for d in sample.KITCHEN_DISHES:
        assert f"</svg> {d['level']}</span>" in html  # an icon and the word, always together
    assert "Basic answers" in runner.render_ask_head("08:40", "basic")


# ---- helpers ----

def test_amount_formats():
    assert style.fmt_amount(0.4, 2.5, "kg") == "0.4 of 2.5 kg"
    assert style.fmt_amount(0, 1.5, "kg") == "0 of 1.5 kg"
    assert style.fmt_amount(18, 40, "pieces") == "18 of 40 pieces"
    assert style.fmt_cook_amount(4.0, "kg") == "4 kg"
    assert style.fmt_cook_amount(1.5, "kg") == "1.5 kg"
    assert style.fmt_cook_amount(24, "pieces") == "24"


def test_nearest_quiet_slot_and_confirm_label():
    slots = sample.GUEST["slots"]
    assert guest.nearest_quiet(slots, "09:00") == "09:30"
    assert guest.nearest_quiet(slots, "07:30") == "06:30"
    assert guest.confirm_label("09:00", 2) == "Confirm 09:00 for 2 guests"
    assert guest.confirm_label("09:30", 1) == "Confirm 09:30 for 1 guest"


def test_icon_buttons_have_accessible_names():
    for elem_id in ("g-party-minus", "g-party-plus", "g-halal-minus", "g-halal-plus", "g-veg-minus", "g-veg-plus"):
        assert elem_id in style.ARIA_LABELS


# ---- app ----

def test_app_builds_with_all_pages():
    import app

    demo = app.build_app()
    paths = {p[0] for p in demo.pages}
    assert {"", "runner", "guest", "report", "about"} <= paths
    assert all(show is False for path, _name, show in demo.pages if path), "navbar entries must be hidden"


# ---- secrets ----

def test_no_api_keys_committed():
    pattern = re.compile(r"AIza[0-9A-Za-z_\-]{30,}")
    for path in ROOT.rglob("*"):
        if path.is_file() and ".git" not in path.parts and path.suffix in {".py", ".md", ".yaml", ".txt", ".ipynb", ".toml", ".cfg"}:
            assert not pattern.search(path.read_text(encoding="utf-8", errors="ignore")), path


def test_env_file_is_ignored():
    assert ".env" in (ROOT / ".gitignore").read_text().splitlines()
