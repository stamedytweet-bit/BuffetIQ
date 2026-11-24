"""Checks for publishing to a Hugging Face Space: settings, files sent, and the app's defaults there."""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("push_to_space", ROOT / "deploy" / "push_to_space.py")
push = importlib.util.module_from_spec(spec)
spec.loader.exec_module(push)


def test_space_header_matches_the_pinned_gradio_version():
    pin = re.search(r"^gradio==([\w.]+)", (ROOT / "requirements.txt").read_text(), re.M).group(1)
    header = push.space_header()
    assert header.startswith("---\n") and f"sdk_version: {pin}\n" in header
    assert "sdk: gradio\n" in header and 'python_version: "3.12"' in header and "app_file: app.py" in header


def test_short_description_fits_the_space_limit():
    assert len(push.SHORT_DESCRIPTION) <= 60


def test_files_sent_include_space_settings_and_no_secrets():
    files = push.build_files()
    assert files["README.md"].decode().startswith("---\ntitle: BuffetIQ")
    assert b"libgl1" in files["packages.txt"]
    assert "app.py" in files and "requirements.txt" in files and "config.yaml" in files
    assert not any(f == ".env" or f.startswith(".github/") for f in files)


def test_no_tracked_file_is_matched_by_gitignore():
    # Hugging Face skips uploaded files that the Space's .gitignore matches, so the
    # forecast data once went missing on the Space although git tracked it.
    assert push.ignored_but_tracked() == []
    assert "data/synthetic_breakfast.csv" in push.build_files()


def test_space_settings_copy_only_the_app_secrets_and_never_the_token():
    env = {"GEMINI_API_KEY": "k", "BUFFETIQ_PASSCODE": " p ", "GEMINI_MODEL": "m",
           "HF_TOKEN": "hf_secret", "OTHER": "x"}
    secrets, variables = push.space_settings(env)
    assert secrets == {"GEMINI_API_KEY": "k", "BUFFETIQ_PASSCODE": "p"}
    assert variables == {"GEMINI_MODEL": "m"}
    assert push.space_settings({"GEMINI_API_KEY": "  "}) == ({}, {})


def test_space_address():
    assert push.space_address("Some_User/buffetiq") == "https://some-user-buffetiq.hf.space"


@pytest.fixture
def launched(monkeypatch):
    import app

    calls = {}
    monkeypatch.setattr(app, "launch", lambda **kw: calls.update(kw))
    for var in ("SPACE_ID", "SPACE_HOST", "BUFFETIQ_HOST", "BUFFETIQ_PORT", "BUFFETIQ_SHOWCASE",
                "GRADIO_SERVER_PORT", "BUFFETIQ_PUBLIC_URL"):
        monkeypatch.delenv(var, raising=False)
    return app, calls


def test_laptop_defaults_are_unchanged(launched):
    app, calls = launched
    app.main([])
    assert calls["host"] == "127.0.0.1" and calls["port"] == 7860 and calls["showcase_morning"] is False


def test_on_a_space_the_app_listens_publicly_and_opens_the_showcase(launched, monkeypatch):
    app, calls = launched
    monkeypatch.setenv("SPACE_ID", "someone/buffetiq")
    monkeypatch.setenv("SPACE_HOST", "someone-buffetiq.hf.space")
    app.main([])
    assert calls["host"] == "0.0.0.0" and calls["showcase_morning"] is True
    assert app.public_url() == "https://someone-buffetiq.hf.space"


def test_guest_qr_uses_the_space_address(monkeypatch):
    from buffetiq import qr

    monkeypatch.delenv("BUFFETIQ_PUBLIC_URL", raising=False)
    monkeypatch.setenv("SPACE_HOST", "someone-buffetiq.hf.space")
    assert qr.guest_url("10.0.0.5:7860") == "https://someone-buffetiq.hf.space/guest"
    monkeypatch.setenv("BUFFETIQ_PUBLIC_URL", "https://example.org/")
    assert qr.guest_url() == "https://example.org/guest"
