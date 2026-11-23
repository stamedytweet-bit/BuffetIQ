"""QR code for the guest page, on screen and as a printable key-card sleeve insert.

The link is worked out from the address the presenter used to open the About
page, so it works on a laptop on the hotel Wi-Fi and through a Colab share link.
When the page was opened as 127.0.0.1 or localhost, a phone could not reach that
address, so the laptop's address on the local network is used instead (the app
must then be started with --host 0.0.0.0). On a Hugging Face Space the Space's
own https address is used. BUFFETIQ_PUBLIC_URL overrides all of these.

Print:  python -m buffetiq.qr --url http://192.168.1.20:7860/guest   (from src)
"""

from __future__ import annotations

import argparse
import os
import socket
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

from buffetiq.state import ROOT, hotel

GUEST_PATH = "/guest"
SLEEVE_PATH = ROOT / "data" / "guest_qr_sleeve.png"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0"}

# Key-card sleeve insert: 85 x 55 mm at 300 dots per inch, the size of a hotel key card
DPI = 300
SLEEVE_MM = (85, 55)


def lan_ip() -> str:
    """This laptop's address on the local network. Opening a UDP socket sends no data."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def guest_url(host: str | None = None, scheme: str = "http") -> str:
    """The address a guest's phone should open."""
    override = os.environ.get("BUFFETIQ_PUBLIC_URL")
    if not override and os.environ.get("SPACE_HOST"):
        override = "https://" + os.environ["SPACE_HOST"]
    if override:
        return override.rstrip("/") + GUEST_PATH
    host = host or "127.0.0.1:7860"
    name, _, port = host.partition(":")
    if name in LOCAL_HOSTS:
        name = lan_ip()
    return f"{scheme}://{name}{':' + port if port else ''}{GUEST_PATH}"


def url_from_request(request) -> str:
    headers = {k.lower(): v for k, v in dict(request.headers).items()}
    host = headers.get("x-forwarded-host") or headers.get("host")
    scheme = headers.get("x-forwarded-proto") or getattr(request.url, "scheme", "http") or "http"
    return guest_url(host, scheme)


def qr_image(url: str, box: int = 10) -> Image.Image:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="#1F2328", back_color="#FFFFFF").convert("RGB")


def _font(size: int, serif: bool = False) -> ImageFont.ImageFont:
    names = (["Georgia.ttf", "DejaVuSerif.ttf", "Times New Roman.ttf"] if serif
             else ["Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf"])
    folders = ["/System/Library/Fonts/Supplemental", "/System/Library/Fonts", "/Library/Fonts",
               "/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts"]
    for folder in folders:
        for name in names:
            path = Path(folder) / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def sleeve(url: str, path: Path = SLEEVE_PATH) -> Path:
    """A printable insert for a mock key-card sleeve: hotel name, a short line and the QR code."""
    w, h = (round(mm / 25.4 * DPI) for mm in SLEEVE_MM)
    img = Image.new("RGB", (w, h), "#FAF8F4")
    d = ImageDraw.Draw(img)
    pad = 48
    code = qr_image(url, box=12)
    size = h - 2 * pad
    code = code.resize((size, size), Image.NEAREST)
    img.paste(code, (w - pad - size, pad))
    x, text_w = pad, w - 3 * pad - size
    h_info = hotel()
    d.text((x, pad), h_info["name"], font=_font(58, serif=True), fill="#0F6E6E")
    d.text((x, pad + 92), "Breakfast at", font=_font(32), fill="#5F646B")
    d.text((x, pad + 134), h_info["restaurant"], font=_font(36), fill="#1F2328")
    lines = ["Scan to tell us your", "breakfast plans and see", "the quieter times."]
    for i, line in enumerate(lines):
        d.text((x, pad + 230 + i * 42), line, font=_font(30), fill="#1F2328")
    d.text((x, h - pad - 30), "Prototype · Fictional data", font=_font(24), fill="#5F646B")
    assert text_w > 0
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, dpi=(DPI, DPI))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Make the guest page QR code sleeve insert.")
    parser.add_argument("--url", help="full guest page address; default uses this laptop's network address")
    args = parser.parse_args()
    url = args.url or guest_url()
    print(f"QR code for {url}")
    print(f"Saved {sleeve(url)}")


if __name__ == "__main__":
    main()
