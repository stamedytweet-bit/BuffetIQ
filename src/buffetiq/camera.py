"""Camera tray check (Phase 4): photo in, fill level and amount out.

A YOLO classification model (the smallest current Ultralytics one, YOLO26n-cls)
sorts a photo of a buffet tray into empty, low, half or full, with a confidence
score. The amount left is the dish's pan capacity multiplied by 0, 0.15, 0.5 or
0.9. Below 0.6 confidence the result is shown as "Not sure about this one" and
nothing is sent to the kitchen board.

Models, in order of preference:
  models/tray_cls.pt           trained on the group's own photos (the real one)
  models/tray_cls_standin.pt   trained on computer-drawn stand-in images, only so
                               the pipeline can be tested before photos exist;
                               its accuracy is never reported
With neither, the runner page offers only the manual level buttons.

Training images are AI-generated in the Gemini app as 2 by 2 grids of four
photos each (docs/GENERATED_PHOTOS.md), saved in tray_photos/grids/ as
grid_<level>_<n>.png, then cut into single photos in tray_photos/<level>/.
Four extra single images in tray_photos/demo_cards/ are never trained on and
are scored separately, as the photos the camera has truly never seen.

Command line (from the src folder):
  python -m buffetiq.camera grids            cut tray_photos/grids/ into single photos
  python -m buffetiq.camera check            count and check tray_photos/
  python -m buffetiq.camera standin          draw stand-in images and train the stand-in model
  python -m buffetiq.camera train            train on tray_photos/ and write the test results
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from buffetiq.state import ROOT, load_config

try:  # iPhone photos are HEIC; this lets Pillow open them
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover
    pass

LEVELS = ["empty", "low", "half", "full"]
WORDS = {"empty": "Empty", "low": "Low", "half": "Half", "full": "Full"}
PHOTOS_DIR = ROOT / "tray_photos"
GRIDS_DIR = PHOTOS_DIR / "grids"
DEMO_CARDS_DIR = PHOTOS_DIR / "demo_cards"
STANDIN_DIR = ROOT / "data" / "standin_trays"
SPLIT_DIR = ROOT / "data" / "tray_split"
MODEL_PATH = ROOT / "models" / "tray_cls.pt"
STANDIN_MODEL_PATH = ROOT / "models" / "tray_cls_standin.pt"
RESULTS_PATH = ROOT / "docs" / "phase4_camera_results.json"
CONFUSION_PATH = ROOT / "docs" / "charts" / "phase4_confusion_matrix.png"
BASE_WEIGHTS = "yolo26n-cls.pt"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
MIN_PER_LEVEL = 8      # two Gemini grids of four photos per level


# ---------------------------------------------------------------------------
# Levels to amounts
# ---------------------------------------------------------------------------

def fraction(level: str) -> float:
    return float(load_config()["rules"]["fill_fraction"][level])


def estimate(level: str, dish: dict) -> dict:
    """Amount left = pan capacity x the level's fraction (0, 0.15, 0.5 or 0.9)."""
    cap = float(dish["pan_capacity"])
    amount = cap * fraction(level)
    if dish["unit"] == "pieces":
        amount = float(round(amount))
    return {"amount": amount, "capacity": cap, "unit": dish["unit"], "fraction": fraction(level)}


def estimate_text(level: str, dish: dict) -> str:
    """'About 0.4 kg left of 2.5 kg' or 'About 6 left of 40 pieces'."""
    e = estimate(level, dish)
    if e["unit"] == "pieces":
        return f"About {int(e['amount'])} left of {int(e['capacity'])} pieces"
    if e["amount"] == 0:
        return f"Nothing left of {e['capacity']:.1f} kg"
    return f"About {e['amount']:.1f} kg left of {e['capacity']:.1f} kg"


# ---------------------------------------------------------------------------
# Classifying a photo
# ---------------------------------------------------------------------------

@dataclass
class Result:
    level: str            # empty, low, half or full (the closest guess, even when unsure)
    confidence: float
    sure: bool            # confidence at or above the threshold; only sure results reach the board
    model_kind: str       # "trained", "stand-in" or "manual"
    probs: dict


_MODELS: dict = {}


def model_kind() -> str | None:
    if MODEL_PATH.exists():
        return "trained"
    if STANDIN_MODEL_PATH.exists():
        return "stand-in"
    return None


def _load(kind: str):
    if kind not in _MODELS:
        from ultralytics import YOLO

        _MODELS[kind] = YOLO(str(MODEL_PATH if kind == "trained" else STANDIN_MODEL_PATH))
    return _MODELS[kind]


def threshold() -> float:
    return float(load_config()["rules"]["low_confidence"])


def to_rgb(image) -> Image.Image:
    if isinstance(image, (str, Path)):
        image = Image.open(image)
    elif isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    return ImageOps.exif_transpose(image).convert("RGB")


def classify(image) -> Result | None:
    """Classify a tray photo, or return None when no model is available (use the manual buttons)."""
    kind = model_kind()
    if kind is None:
        return None
    model = _load(kind)
    r = model.predict(to_rgb(image), imgsz=224, verbose=False)[0]
    names = r.names
    probs = {names[i]: float(p) for i, p in enumerate(r.probs.data.tolist())}
    level = names[int(r.probs.top1)]
    conf = float(r.probs.top1conf)
    return Result(level=level, confidence=conf, sure=conf >= threshold(), model_kind=kind, probs=probs)


def manual(level: str) -> Result:
    return Result(level=level, confidence=1.0, sure=True, model_kind="manual", probs={level: 1.0})


def save_correction(image, level: str, root: Path = PHOTOS_DIR) -> Path:
    """Keep a photo the runner corrected, in its right level folder, for the next training run."""
    folder = root / level
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"correction_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    to_rgb(image).save(path, quality=90)
    return path


# ---------------------------------------------------------------------------
# Checking the group's photos
# ---------------------------------------------------------------------------

def list_images(folder: Path) -> list[Path]:
    return sorted(p for p in folder.glob("*") if p.suffix.lower() in IMAGE_SUFFIXES)


def check_photos(root: Path = PHOTOS_DIR) -> dict:
    """Count photos per level and list problems: unreadable, tiny, duplicated or unbalanced."""
    report = {"counts": {}, "problems": []}
    seen: dict[str, Path] = {}
    for level in LEVELS:
        files = list_images(root / level)
        report["counts"][level] = len(files)
        for f in files:
            try:
                with Image.open(f) as im:
                    w, h = im.size
            except Exception:
                report["problems"].append(f"{f.relative_to(root)} cannot be opened")
                continue
            if min(w, h) < 224:
                report["problems"].append(f"{f.relative_to(root)} is very small ({w} x {h})")
            digest = hashlib.md5(f.read_bytes()).hexdigest()
            if digest in seen:
                report["problems"].append(f"{f.relative_to(root)} is a copy of {seen[digest].relative_to(root)}")
            seen[digest] = f
    counts = report["counts"].values()
    for level, n in report["counts"].items():
        if n < MIN_PER_LEVEL:
            report["problems"].append(f"{level} has {n} photos; at least {MIN_PER_LEVEL} are needed")
    if counts and max(counts) > 1.5 * min(counts) and min(counts) >= MIN_PER_LEVEL:
        report["problems"].append("one level has more than one and a half times the photos of another; try to balance them")
    report["ready"] = all(n >= MIN_PER_LEVEL for n in counts)
    return report


# ---------------------------------------------------------------------------
# Cutting Gemini grids into single photos
# ---------------------------------------------------------------------------

def level_from_name(name: str) -> str | None:
    """The level named in a file name, such as grid_low_2.png or demo_pancakes_half.png."""
    parts = name.lower().replace("-", "_").split("_")
    found = [lv for lv in LEVELS if lv in parts]
    return found[0] if len(found) == 1 else None


def _gutter(std: np.ndarray, limit: float = 10.0) -> tuple[int, int]:
    """Where to cut along one axis: the plain band nearest the middle, or the exact middle if there is none.

    std holds how much the pixels vary along each column (or row). A white line
    between photos varies very little, so it shows as a run of low values.
    """
    n = len(std)
    lo, hi = int(n * 0.35), int(n * 0.65)
    mid = n // 2
    flat = std[lo:hi] < limit
    if not flat.any():
        return mid, mid
    idx = np.flatnonzero(flat) + lo
    centre = int(idx[np.argmin(np.abs(idx - mid))])
    a = b = centre
    while a > lo and std[a - 1] < limit:
        a -= 1
    while b < hi - 1 and std[b + 1] < limit:
        b += 1
    return a, b + 1


def _is_line(pixels: np.ndarray, limit: float) -> bool:
    """A plain white or black strip, the colours Gemini uses between photos (not a plain table top)."""
    return pixels.std() < limit and (pixels.mean() > 215 or pixels.mean() < 40)


def _trim(gray: np.ndarray, limit: float = 10.0, most: float = 0.12) -> tuple[int, int, int, int]:
    """Trim white or black borders left over from the grid lines, never more than 12% a side."""
    h, w = gray.shape
    top, bottom, left, right = 0, h, 0, w
    while top < h * most and _is_line(gray[top], limit):
        top += 1
    while h - bottom < h * most and _is_line(gray[bottom - 1], limit):
        bottom -= 1
    while left < w * most and _is_line(gray[:, left], limit):
        left += 1
    while w - right < w * most and _is_line(gray[:, right - 1], limit):
        right -= 1
    return top, bottom, left, right


def cut_grid(image: Image.Image) -> list[Image.Image]:
    """Cut a 2 by 2 grid into its four photos: top left, top right, bottom left, bottom right."""
    im = ImageOps.exif_transpose(image).convert("RGB")
    gray = np.asarray(im.convert("L"), dtype=float)
    x0, x1 = _gutter(gray.std(axis=0))
    y0, y1 = _gutter(gray.std(axis=1))
    h, w = gray.shape
    boxes = [(0, 0, x0, y0), (x1, 0, w, y0), (0, y1, x0, h), (x1, y1, w, h)]
    tiles = []
    for left, top, right, bottom in boxes:
        t, b, l, r = _trim(gray[top:bottom, left:right])
        tiles.append(im.crop((left + l, top + t, left + r, top + b)))
    return tiles


def split_grids(src: Path = GRIDS_DIR, dest: Path = PHOTOS_DIR) -> dict:
    """Cut every grid in src into four photos in dest/<level>/, named g_<level>_<n>_<1 to 4>.jpg."""
    report = {"grids": 0, "photos": {lv: 0 for lv in LEVELS}, "skipped": []}
    for f in list_images(src):
        level = level_from_name(f.stem)
        if level is None:
            report["skipped"].append(f"{f.name}: the name must contain one level, such as grid_low_1.png")
            continue
        try:
            with Image.open(f) as im:
                tiles = cut_grid(im)
        except Exception:
            report["skipped"].append(f"{f.name}: cannot be opened")
            continue
        out = dest / level
        out.mkdir(parents=True, exist_ok=True)
        stem = f.stem.lower().replace("grid_", "g_", 1)
        for k, tile in enumerate(tiles, start=1):
            tile.save(out / f"{stem}_{k}.jpg", quality=92)
        report["grids"] += 1
        report["photos"][level] += len(tiles)
    return report


# ---------------------------------------------------------------------------
# Train, validation and test split
# ---------------------------------------------------------------------------

def make_split(src: Path, out: Path, seed: int, fractions=(0.70, 0.15, 0.15)) -> dict:
    """Copy photos into out/train, out/val and out/test, keeping each level's share in every part.

    The test part is never seen in training, so its accuracy is an honest estimate.
    """
    if out.exists():
        shutil.rmtree(out)
    rng = random.Random(seed)
    counts = {"train": {}, "val": {}, "test": {}}
    for level in LEVELS:
        files = list_images(src / level)
        rng.shuffle(files)
        n = len(files)
        n_test = max(1, round(n * fractions[2]))
        n_val = max(1, round(n * fractions[1]))
        parts = {"test": files[:n_test], "val": files[n_test:n_test + n_val], "train": files[n_test + n_val:]}
        for part, chosen in parts.items():
            dest = out / part / level
            dest.mkdir(parents=True, exist_ok=True)
            for f in chosen:
                to_rgb(f).save(dest / (f.stem + ".jpg"), quality=92)
            counts[part][level] = len(chosen)
    return counts


# ---------------------------------------------------------------------------
# Training and the held-out test
# ---------------------------------------------------------------------------

def device() -> str:
    import torch

    if torch.cuda.is_available():
        return "0"
    return "cpu"   # Apple's MPS is skipped: classification training on it is less reliable


def train(src: Path = PHOTOS_DIR, weights_out: Path = MODEL_PATH, epochs: int = 30, standin: bool = False,
          write_results: bool = True) -> dict:
    from ultralytics import YOLO

    seed = load_config()["simulation"]["seed"]
    split_dir = SPLIT_DIR.with_name(SPLIT_DIR.name + ("_standin" if standin else ""))
    counts = make_split(src, split_dir, seed)
    model = YOLO(BASE_WEIGHTS)
    model.train(data=str(split_dir), epochs=epochs, imgsz=224, batch=16, device=device(), seed=seed,
                deterministic=True, patience=10, project=str(ROOT / "runs"), name="standin" if standin else "tray",
                exist_ok=True, verbose=False, plots=False)
    best = Path(model.trainer.best)
    weights_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(best, weights_out)
    _MODELS.clear()
    results = evaluate(weights_out, split_dir / "test")
    if not standin:
        results["demo_cards"] = evaluate_cards(weights_out)
    results["counts"] = counts
    results["epochs"] = epochs
    results["base_weights"] = BASE_WEIGHTS
    results["standin"] = standin
    if write_results and not standin:
        RESULTS_PATH.write_text(json.dumps(results, indent=2))
        plot_confusion(results, CONFUSION_PATH)
    return results


def evaluate(weights: Path, test_dir: Path) -> dict:
    """Accuracy and confusion matrix on the held-out test photos."""
    from ultralytics import YOLO

    model = YOLO(str(weights))
    truth, pred, confs = [], [], []
    for level in LEVELS:
        for f in list_images(test_dir / level):
            r = model.predict(to_rgb(f), imgsz=224, verbose=False)[0]
            truth.append(level)
            pred.append(r.names[int(r.probs.top1)])
            confs.append(float(r.probs.top1conf))
    truth, pred, confs = np.array(truth), np.array(pred), np.array(confs)
    matrix = [[int(((truth == t) & (pred == p)).sum()) for p in LEVELS] for t in LEVELS]
    sure = confs >= threshold()
    return {
        "test_photos": int(len(truth)),
        "accuracy": float((truth == pred).mean()) if len(truth) else 0.0,
        "per_level_accuracy": {lv: float((pred[truth == lv] == lv).mean()) if (truth == lv).any() else 0.0
                               for lv in LEVELS},
        "confusion": {"levels": LEVELS, "matrix": matrix},
        "share_sure": float(sure.mean()) if len(truth) else 0.0,
        "accuracy_when_sure": float((truth[sure] == pred[sure]).mean()) if sure.any() else 0.0,
        "off_by_more_than_one_level": int(sum(abs(LEVELS.index(t) - LEVELS.index(p)) > 1 for t, p in zip(truth, pred))),
    }


def evaluate_cards(weights: Path, folder: Path = DEMO_CARDS_DIR) -> list[dict]:
    """Score the demo cards, which are never trained on. The level comes from each file name."""
    from ultralytics import YOLO

    files = [f for f in list_images(folder) if level_from_name(f.stem)] if folder.exists() else []
    if not files:
        return []
    model = YOLO(str(weights))
    rows = []
    for f in files:
        r = model.predict(to_rgb(f), imgsz=224, verbose=False)[0]
        conf = float(r.probs.top1conf)
        rows.append({"card": f.name, "expected": level_from_name(f.stem), "predicted": r.names[int(r.probs.top1)],
                     "confidence": round(conf, 2), "sure": conf >= threshold()})
    return rows


def plot_confusion(results: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m = np.array(results["confusion"]["matrix"])
    words = [WORDS[lv] for lv in LEVELS]
    fig, ax = plt.subplots(figsize=(6.4, 5.6), dpi=150)
    fig.patch.set_facecolor("#FAF8F4")
    ax.imshow(m, cmap="Greens", vmin=0)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, str(m[i, j]), ha="center", va="center", fontsize=13, fontweight="bold",
                    color="#FFFFFF" if m[i, j] > m.max() * 0.6 else "#1F2328")
    ax.set_xticks(range(4), words)
    ax.set_yticks(range(4), words)
    ax.set_xlabel("Model's answer", color="#5F646B")
    ax.set_ylabel("True level", color="#5F646B")
    acc = results["accuracy"] * 100
    fig.suptitle(f"The camera model is right on {acc:.0f}% of {results['test_photos']} unseen photos",
                 x=0.04, ha="left", fontsize=12, fontweight="bold", color="#1F2328")
    ax.set_title("Held-out test photos the model never saw in training.", loc="left", fontsize=9, color="#5F646B")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)


# ---------------------------------------------------------------------------
# Stand-in images (computer-drawn), only to test the pipeline before photos exist
# ---------------------------------------------------------------------------

FOOD_COLOURS = [(242, 200, 80), (176, 98, 52), (238, 226, 200), (196, 132, 60), (120, 160, 70), (210, 90, 70)]
BACKGROUNDS = [(150, 150, 150), (120, 90, 60), (210, 205, 195), (60, 60, 65), (180, 170, 150)]
LEVEL_COVER = {"empty": (0.0, 0.04), "low": (0.06, 0.22), "half": (0.32, 0.68), "full": (0.80, 1.0)}


def draw_standin(level: str, rng: random.Random, size: int = 320) -> Image.Image:
    """A top-down tray with food covering roughly the level's share of it."""
    bg = tuple(min(255, max(0, c + rng.randint(-25, 25))) for c in rng.choice(BACKGROUNDS))
    img = Image.new("RGB", (size, size), bg)
    d = ImageDraw.Draw(img)
    m = rng.randint(28, 60)
    x0, y0, x1, y1 = m, m + rng.randint(-10, 10), size - m, size - m + rng.randint(-10, 10)
    metal = rng.randint(160, 215)
    d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=(metal, metal, metal + 5),
                        outline=(metal - 60,) * 3, width=6)
    inner = (x0 + 12, y0 + 12, x1 - 12, y1 - 12)
    lo, hi = LEVEL_COVER[level]
    cover = rng.uniform(lo, hi)
    food = rng.choice(FOOD_COLOURS)
    w = inner[2] - inner[0]
    if cover > 0:
        # food fills a share of the tray from one side, with a ragged edge and lumps
        edge = inner[0] + int(w * cover)
        pts = [(inner[0], inner[1])]
        for yy in range(inner[1], inner[3] + 1, 12):
            pts.append((min(inner[2], edge + rng.randint(-14, 14)), yy))
        pts.append((inner[0], inner[3]))
        d.polygon(pts, fill=food)
        for _ in range(int(60 * cover) + 4):
            cx = rng.randint(inner[0], max(inner[0] + 1, min(inner[2], edge)))
            cy = rng.randint(inner[1], inner[3])
            r = rng.randint(4, 12)
            shade = tuple(max(0, min(255, c + rng.randint(-35, 25))) for c in food)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=shade)
    else:
        for _ in range(rng.randint(0, 6)):   # crumbs
            cx, cy, r = rng.randint(inner[0], inner[2]), rng.randint(inner[1], inner[3]), rng.randint(2, 5)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=food)
    img = img.rotate(rng.uniform(-25, 25), resample=Image.BILINEAR, fillcolor=bg)
    if rng.random() < 0.5:
        img = ImageOps.mirror(img)
    light = rng.uniform(0.65, 1.25)
    img = Image.eval(img, lambda v: max(0, min(255, int(v * light))))
    if rng.random() < 0.4:
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.5, 1.5)))
    return img


def make_standins(out: Path = STANDIN_DIR, per_level: int = 60, seed: int = 7) -> dict:
    if out.exists():
        shutil.rmtree(out)
    rng = random.Random(seed)
    for level in LEVELS:
        (out / level).mkdir(parents=True, exist_ok=True)
        for i in range(per_level):
            draw_standin(level, rng).save(out / level / f"standin_{i:03d}.jpg", quality=90)
    return {lv: per_level for lv in LEVELS}


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="BuffetIQ camera model")
    parser.add_argument("command", choices=["grids", "check", "standin", "train"])
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()
    if args.command == "grids":
        r = split_grids()
        print(f"Cut {r['grids']} grids into photos: " + ", ".join(f"{WORDS[lv]} {n}" for lv, n in r["photos"].items()))
        for problem in r["skipped"]:
            print(f"  - skipped {problem}")
        print("Look through each level folder and move or delete any photo that does not match its level.")
    elif args.command == "check":
        r = check_photos()
        for level in LEVELS:
            print(f"{WORDS[level]:<6} {r['counts'][level]:>4} photos")
        for p in r["problems"]:
            print(f"  - {p}")
        print("Ready to train." if r["ready"] else f"Not ready yet: each level needs at least {MIN_PER_LEVEL} photos.")
    elif args.command == "standin":
        make_standins()
        r = train(STANDIN_DIR, STANDIN_MODEL_PATH, epochs=min(args.epochs, 15), standin=True)
        print(f"Stand-in model saved to {STANDIN_MODEL_PATH}. Its accuracy is not reported: the images are computer-drawn.")
        print(f"(Pipeline check only: {r['test_photos']} stand-in test images.)")
    else:
        r = check_photos()
        if not r["ready"]:
            raise SystemExit("Not enough photos yet; run 'python -m buffetiq.camera check'.")
        r = train(epochs=args.epochs)
        print(f"Test accuracy {r['accuracy']:.1%} on {r['test_photos']} unseen photos. Saved {MODEL_PATH}.")
        for c in r.get("demo_cards", []):
            mark = "right" if c["predicted"] == c["expected"] else "WRONG"
            print(f"  demo card {c['card']}: {c['predicted']} ({c['confidence']:.0%} sure), {mark}")


if __name__ == "__main__":
    main()
