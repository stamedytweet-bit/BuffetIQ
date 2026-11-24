"""Tough checks for the camera model, on images it was not trained on.

  stress   the printed demo cards (never trained on), each changed 13 ways a hurried
           phone photo might be: rotated, tilted, dark, glare, warm light, blurred,
           zoomed, cut off, heavily compressed or tiny. Compares two models.
  unseen   retrains four times, each time hiding one dish's messy photos (one per
           level), and tests on the hidden dish, so the score shows whether the model
           learned messy trays or memorised these pictures.

Run from the src folder:
  python -m buffetiq.camera_stress stress OLD.pt NEW.pt results.json
  python -m buffetiq.camera_stress unseen
"""
import glob, io, json, os, shutil, sys, tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from buffetiq import camera
from buffetiq.camera import level_from_name

def crop(im, fx0, fy0, fx1, fy1):
    w, h = im.size; return im.crop((int(w*fx0), int(h*fy0), int(w*fx1), int(h*fy1)))
def jpeg(im, q):
    b = io.BytesIO(); im.save(b, "JPEG", quality=q); return Image.open(io.BytesIO(b.getvalue()))
def tilt(im):
    w, h = im.size; d = 0.18
    return im.transform((w, h), Image.QUAD, (w*d, 0, 0, h, w, h, w*(1-d), 0), Image.BICUBIC)
def warm(im):
    r, g, b = im.split(); return Image.merge("RGB", (r.point(lambda v: min(255, v*1.15)), g, b.point(lambda v: v*0.8)))
VARIANTS = {
    "original": lambda im: im,
    "rotated 90": lambda im: im.rotate(90, expand=True),
    "upside down": lambda im: im.rotate(180),
    "tilted 15 degrees": lambda im: crop(im.rotate(15, expand=False), .08, .08, .92, .92),
    "angled shot": tilt,
    "dark room": lambda im: ImageEnhance.Brightness(im).enhance(0.5),
    "glare, too bright": lambda im: ImageEnhance.Brightness(im).enhance(1.5),
    "warm lamp light": warm,
    "blurry (moved)": lambda im: im.filter(ImageFilter.GaussianBlur(4)),
    "zoomed in": lambda im: crop(im, .15, .15, .85, .85),
    "tray cut off at side": lambda im: crop(im, .25, 0, 1, 1),
    "low quality jpeg": lambda im: jpeg(im, 15),
    "tiny photo": lambda im: im.resize((160, int(160*im.size[1]/im.size[0]))),
}
def run(weights):
    from ultralytics import YOLO

    m = YOLO(weights); out = []
    for f in sorted(glob.glob(str(camera.DEMO_CARDS_DIR / "*.jpg"))):
        truth = level_from_name(os.path.basename(f).rsplit(".", 1)[0]); base = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        for name, fn in VARIANTS.items():
            r = m.predict(fn(base), imgsz=224, verbose=False)[0]
            p = r.names[int(r.probs.top1)]; c = float(r.probs.top1conf)
            out.append({"card": os.path.basename(f), "variant": name, "truth": truth, "pred": p, "conf": round(c, 2)})
    return out
def summary(rows, t=0.6):
    n = len(rows); right = sum(r["pred"] == r["truth"] for r in rows)
    sure_wrong = sum(r["pred"] != r["truth"] and r["conf"] >= t for r in rows)
    unsure = sum(r["conf"] < t for r in rows)
    return f"{right}/{n} right ({right/n:.0%}); confidently wrong (sent to board) {sure_wrong}; held back as not sure {unsure}"
DISHES = {1: "noodles (foil tray)", 2: "scrambled eggs", 3: "rice (round dish)", 4: "sausages"}   # grid tile order


def unseen() -> list[dict]:
    from ultralytics import YOLO

    rows = []
    for k, dish in DISHES.items():
        with tempfile.TemporaryDirectory() as tmp:
            src, held = Path(tmp) / "photos", []
            for lv in camera.LEVELS:
                (src / lv).mkdir(parents=True)
                for f in glob.glob(str(camera.PHOTOS_DIR / lv / "*.jpg")):
                    if f.endswith(f"_messy_{k}.jpg"):
                        held.append((lv, f))
                    else:
                        shutil.copy(f, src / lv)
            weights = Path(tmp) / "model.pt"
            camera.train(src=src, weights_out=weights, write_results=False)
            m = YOLO(str(weights))
            for lv, f in held:
                r = m.predict(Image.open(f).convert("RGB"), imgsz=224, verbose=False)[0]
                rows.append({"hidden_dish": dish, "truth": lv, "pred": r.names[int(r.probs.top1)],
                             "conf": round(float(r.probs.top1conf), 2)})
    return rows


if __name__ == "__main__":
    if sys.argv[1] == "stress":
        res = {}
        for label, w in (("old", sys.argv[2]), ("new", sys.argv[3])):
            res[label] = run(w)
            print(label, summary(res[label]))
        Path(sys.argv[4]).write_text(json.dumps(res, indent=1))
    else:
        rows = unseen()
        print(summary(rows))
        for r in rows:
            print(f"  {r['hidden_dish']:20} {r['truth']:5} -> {r['pred']:5} {r['conf']:.2f}")
