"""BuffetIQ prototype: builds every page and launches the Gradio app.

Run locally:  python app.py          (opens on http://127.0.0.1:7860)
In Colab:     python app.py --share  (or use notebooks/run_in_colab.ipynb)
On a Hugging Face Space the app listens on 0.0.0.0 and opens the showcase
morning by itself (see deploy/push_to_space.py).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import gradio as gr  # noqa: E402

from buffetiq import assistant, state, style  # noqa: E402
from buffetiq.ui import about, guest, kitchen, report, runner  # noqa: E402

# Page paths. The navbar is hidden on every page; the About page links them all.
PAGES = {
    "kitchen": "/",
    "runner": "/runner",
    "guest": "/guest",
    "report": "/report",
    "about": "/about",
}


def build_app() -> gr.Blocks:
    with gr.Blocks(title="BuffetIQ") as demo:
        kitchen.build_page()
    with demo.route("Runner", PAGES["runner"], show_in_navbar=False):
        runner.build_page()
    with demo.route("Guest", PAGES["guest"], show_in_navbar=False):
        guest.build_page()
    with demo.route("Day-end report", PAGES["report"], show_in_navbar=False):
        report.build_page()
    with demo.route("About", PAGES["about"], show_in_navbar=False):
        about.build_page(PAGES)
    return demo


def in_colab() -> bool:
    return "google.colab" in sys.modules or "COLAB_RELEASE_TAG" in os.environ


def on_space() -> bool:
    """True when running on a Hugging Face Space, which sets SPACE_ID."""
    return bool(os.environ.get("SPACE_ID"))


def public_url() -> str | None:
    """The address people open: BUFFETIQ_PUBLIC_URL, or the Space's own address."""
    if os.environ.get("BUFFETIQ_PUBLIC_URL"):
        return os.environ["BUFFETIQ_PUBLIC_URL"].rstrip("/")
    host = os.environ.get("SPACE_HOST")
    return f"https://{host}" if host else None


def launch(share: bool = False, host: str = "127.0.0.1", port: int = 7860, at: str | None = None,
           showcase_morning: bool = False, block: bool = True) -> dict:
    """Prepare the service and start the app. Returns the local and share links for each page."""
    print("Preparing the forecast for the service...")
    state.service()   # train the live forecast once, before the first page opens
    assistant.preload_whisper()   # load speech-to-text in the background so the first question is quick
    if showcase_morning:
        state.load_showcase()
        print("Loaded the showcase morning (82% occupancy, tour group of 24 at 07:45).")
    if at:
        state.service().replay_to(at)
        print(f"Replayed the morning to {at} with simulated guests and tray checks.")
    demo = build_app()
    _, local_url, share_url = demo.launch(
        share=share or in_colab(),
        server_name=host,
        server_port=port,
        theme=gr.themes.Base(font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"]),
        css=style.CSS,
        head=style.HEAD,
        js=style.JS,
        footer_links=[],
        ssr_mode=False,   # Spaces turn server-side rendering on by default; the pages' own scripts expect it off
        prevent_thread_lock=True,
    )
    base = (share_url or public_url() or local_url).rstrip("/")
    links = {name: base + (path if path != "/" else "/") for name, path in PAGES.items()}
    print("\nBuffetIQ pages:")
    for name, url in links.items():
        print(f"  {name:<8} {url}")
    if share_url:
        print("\nThe share link lasts 72 hours and anyone with it can open the app. Use fictional data only.")
    if block:
        demo.block_thread()
    return {"local": local_url, "share": share_url, "pages": links, "demo": demo}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Launch the BuffetIQ prototype.")
    parser.add_argument("--share", action="store_true", help="create a public Gradio share link (used in Colab)")
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("BUFFETIQ_PORT") or os.environ.get("GRADIO_SERVER_PORT") or 7860))
    parser.add_argument("--host", default=os.environ.get("BUFFETIQ_HOST") or ("0.0.0.0" if on_space() else "127.0.0.1"),
                        help="use 0.0.0.0 so phones on the same Wi-Fi can open the pages")
    parser.add_argument("--at", metavar="HH:MM",
                        help="replay the morning up to this time first, such as 08:40 (simulated guests and trays)")
    parser.add_argument("--showcase", action="store_true",
                        help="start with the prepared showcase morning (82%% occupancy, tour group at 07:45)")
    args = parser.parse_args(argv)
    showcase_morning = args.showcase or on_space() or os.environ.get("BUFFETIQ_SHOWCASE") == "1"
    launch(share=args.share, host=args.host, port=args.port, at=args.at, showcase_morning=showcase_morning)


if __name__ == "__main__":
    main()
