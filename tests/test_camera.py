"""Phase 4 tests: levels to amounts, the confidence rule, the manual fallback,
corrections, the photo split and the tray records on shared state."""

import csv
import random

import pytest
from PIL import Image

from buffetiq import camera, state
from buffetiq.ui import kitchen, runner


def dish(dish_id):
    return next(d for d in state.load_config()["dishes"] if d["id"] == dish_id)


@pytest.fixture(scope="module")
def model():
    s = state.Service(checkins_path=state.ROOT / "data" / "_test_cam.csv")
    (state.ROOT / "data" / "_test_cam.csv").unlink(missing_ok=True)
    return s.model


@pytest.fixture
def svc(tmp_path, model, monkeypatch):
    s = state.Service(checkins_path=tmp_path / "c.csv", model=model, log_path=tmp_path / "log.csv")
    monkeypatch.setattr(state, "_SERVICE", s)
    return s


@pytest.mark.parametrize("level,amount", [("empty", 0.0), ("low", 0.375), ("half", 1.25), ("full", 2.25)])
def test_amount_is_pan_capacity_times_fraction(level, amount):
    assert camera.estimate(level, dish("scrambled_eggs"))["amount"] == pytest.approx(amount)


def test_estimate_text_matches_the_design():
    assert camera.estimate_text("low", dish("scrambled_eggs")) == "About 0.4 kg left of 2.5 kg"
    assert camera.estimate_text("low", dish("croissants")) == "About 6 left of 40 pieces"
    assert camera.estimate_text("empty", dish("pancakes")) == "Nothing left of 1.5 kg"


def test_below_60_percent_is_not_sure(monkeypatch):
    class FakeProbs:
        def __init__(self, p):
            self.data = __import__("torch").tensor(p)
            self.top1 = int(max(range(4), key=lambda i: p[i]))
            self.top1conf = max(p)

    class FakeModel:
        def __init__(self, p):
            self.p = p

        def predict(self, *a, **k):
            r = type("R", (), {})()
            r.names = {0: "empty", 1: "full", 2: "half", 3: "low"}
            r.probs = FakeProbs(self.p)
            return [r]

    monkeypatch.setattr(camera, "model_kind", lambda: "trained")
    img = Image.new("RGB", (64, 64))
    monkeypatch.setattr(camera, "_load", lambda kind: FakeModel([0.05, 0.05, 0.35, 0.55]))
    r = camera.classify(img)
    assert r.level == "low" and not r.sure
    monkeypatch.setattr(camera, "_load", lambda kind: FakeModel([0.02, 0.02, 0.06, 0.90]))
    r = camera.classify(img)
    assert r.level == "low" and r.sure and r.confidence == pytest.approx(0.90)


def test_no_model_means_manual_buttons(monkeypatch):
    monkeypatch.setattr(camera, "model_kind", lambda: None)
    assert camera.classify(Image.new("RGB", (64, 64))) is None
    m = camera.manual("half")
    assert m.model_kind == "manual" and m.sure


def test_unsure_card_sends_nothing_and_says_so():
    html = runner.render_unsure("low", 0.52)
    assert "Not sure about this one" in html and "Nothing was sent" in html and "52% sure" in html


def test_sure_result_updates_the_board_and_the_log(svc):
    out = runner.outcome("Scrambled eggs", "low", 0.91, "camera", leftover=False)
    assert "Kitchen board updated" in out["done"] and "91% sure" in out["card"]
    assert svc.trays["scrambled_eggs"]["level"] == "low"
    card = next(c for c in kitchen.live_dishes() if c["name"] == "Scrambled eggs")
    assert card["level"] == "Low" and card["amount"] == "0.4 of 2.5 kg" and card["fill_pct"] == 15
    rows = list(csv.DictReader(open(svc.log_path)))
    assert rows[-1]["action"] == "tray_check" and rows[-1]["source"] == "camera" and rows[-1]["level"] == "low"


def test_manual_result_is_labelled_set_by_hand(svc):
    out = runner.outcome("Croissants", "half", None, "manual", leftover=False)
    assert "Set by hand" in out["card"]
    assert svc.trays["croissants"]["amount"] == 20


def test_record_leftovers_writes_history_not_the_board(svc):
    out = runner.outcome("Cut fruit", "low", None, "manual", leftover=True)
    assert "Recorded as leftover" in out["done"]
    assert "cut_fruit" not in svc.trays
    row = list(csv.DictReader(open(svc.log_path)))[-1]
    assert row["action"] == "leftover" and float(row["amount"]) == pytest.approx(0.75)


def test_log_has_no_guest_fields(svc):
    svc.log_event("tray_check", dish="pancakes", room="1204")
    header = open(svc.log_path).readline()
    assert "room" not in header and "1204" not in open(svc.log_path).read()


def test_corrections_are_saved_in_the_right_level(tmp_path):
    path = camera.save_correction(Image.new("RGB", (300, 300), "red"), "half", root=tmp_path)
    assert path.parent.name == "half" and path.name.startswith("correction_")


def test_split_keeps_every_level_in_train_val_and_test(tmp_path):
    rng = random.Random(1)
    for lv in camera.LEVELS:
        (tmp_path / "src" / lv).mkdir(parents=True)
        for i in range(20):
            camera.draw_standin(lv, rng, 200).save(tmp_path / "src" / lv / f"s1_{i:03d}.jpg")
    counts = camera.make_split(tmp_path / "src", tmp_path / "out", seed=5)
    for lv in camera.LEVELS:
        assert counts["test"][lv] == 3 and counts["val"][lv] == 3 and counts["train"][lv] == 14
    train = {(p.parent.name, p.name) for p in (tmp_path / "out" / "train").rglob("*.jpg")}
    test = {(p.parent.name, p.name) for p in (tmp_path / "out" / "test").rglob("*.jpg")}
    assert not train & test


def test_photo_check_reports_shortfalls_and_copies(tmp_path):
    for lv in camera.LEVELS:
        (tmp_path / lv).mkdir()
    img = Image.new("RGB", (400, 300), "white")
    img.save(tmp_path / "low" / "a.jpg")
    (tmp_path / "low" / "b.jpg").write_bytes((tmp_path / "low" / "a.jpg").read_bytes())
    r = camera.check_photos(tmp_path)
    assert r["counts"]["low"] == 2 and not r["ready"]
    assert any("copy of" in p for p in r["problems"])
    assert any(f"at least {camera.MIN_PER_LEVEL}" in p for p in r["problems"])


def test_photos_are_ignored_by_git():
    ignore = (state.ROOT / ".gitignore").read_text()
    assert "tray_photos/**/*.jpg" in ignore and "*.pt" in ignore


# ---- Gemini grids ----

def make_grid(rng, gutter=12, border=8, size=300):
    """Four stand-in trays in a 2 by 2 grid with white lines between them, like a Gemini grid."""
    side = 2 * size + gutter + 2 * border
    grid = Image.new("RGB", (side, side), "white")
    tiles = [camera.draw_standin(lv, rng, size) for lv in camera.LEVELS]
    spots = [(border, border), (border + size + gutter, border),
             (border, border + size + gutter), (border + size + gutter, border + size + gutter)]
    for tile, spot in zip(tiles, spots):
        grid.paste(tile, spot)
    return grid


def test_grid_is_cut_into_four_photos_without_the_white_lines():
    import numpy as np

    tiles = camera.cut_grid(make_grid(random.Random(3)))
    assert len(tiles) == 4
    for t in tiles:
        assert abs(t.width - 300) <= 6 and abs(t.height - 300) <= 6
        g = np.asarray(t.convert("L"), dtype=float)
        for edge in (g[0], g[-1], g[:, 0], g[:, -1]):
            assert edge.mean() < 215, "a white border was left on the photo"


def test_grid_without_lines_is_cut_at_the_middle():
    im = Image.effect_noise((600, 400), 60).convert("RGB")
    tiles = camera.cut_grid(im)
    assert [t.size for t in tiles] == [(300, 200)] * 4


def test_grids_are_filed_by_the_level_in_their_name(tmp_path):
    src = tmp_path / "grids"
    src.mkdir()
    make_grid(random.Random(4)).save(src / "grid_low_1.png")
    make_grid(random.Random(5)).save(src / "grid_half_2.png")
    make_grid(random.Random(6)).save(src / "my_picture.png")
    r = camera.split_grids(src, tmp_path)
    assert r["grids"] == 2 and r["photos"]["low"] == 4 and r["photos"]["half"] == 4
    assert sorted(p.name for p in (tmp_path / "low").iterdir()) == [f"g_low_1_{k}.jpg" for k in range(1, 5)]
    assert any("my_picture.png" in s for s in r["skipped"])


@pytest.mark.parametrize("name,level", [("grid_low_1", "low"), ("demo_pancakes_half", "half"),
                                        ("g_full_03", "full"), ("grid_1", None), ("low_full", None)])
def test_level_from_name(name, level):
    assert camera.level_from_name(name) == level
