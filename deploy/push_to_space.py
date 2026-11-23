"""Publish BuffetIQ to a Hugging Face Space.

The Space runs the same app.py as the laptop. This script copies every file
that git tracks (so .env, the virtual environment and generated data never leave
the laptop), puts the Space settings at the top of the README, adds the system
libraries the camera library needs, and uploads the lot as one commit. Files
removed from git are removed from the Space too.

The token is read from HF_TOKEN (an environment variable, a GitHub secret, or a
line in the git-ignored .env file) and is never printed.

Run from the project folder:
    python deploy/push_to_space.py --space your-username/buffetiq
    python deploy/push_to_space.py --space your-username/buffetiq --dry-run   (list files only)

GitHub runs the same command on every push to main (.github/workflows/deploy-space.yml).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

# Tracked files the Space does not need
SKIP_PREFIXES = (".github/",)

SHORT_DESCRIPTION = "Hotel breakfast buffet prototype on fictional data"


def gradio_version() -> str:
    """The Gradio version pinned in requirements.txt, so the Space matches the laptop."""
    m = re.search(r"^gradio==([\w.]+)", (ROOT / "requirements.txt").read_text(), re.M)
    if not m:
        raise SystemExit("requirements.txt must pin gradio==<version> for the Space.")
    return m.group(1)


def space_header() -> str:
    return "\n".join([
        "---",
        "title: BuffetIQ",
        "emoji: 🍳",
        "colorFrom: green",
        "colorTo: yellow",
        "sdk: gradio",
        f"sdk_version: {gradio_version()}",
        'python_version: "3.12"',
        "app_file: app.py",
        "pinned: false",
        f"short_description: {SHORT_DESCRIPTION}",
        "---",
        "",
    ])


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    files = [f for f in out.splitlines() if f and not f.startswith(SKIP_PREFIXES)]
    return [f for f in files if (ROOT / f).is_file()]


def build_files() -> dict[str, bytes]:
    """Every file for the Space, as {path in the Space: contents}."""
    files = {f: (ROOT / f).read_bytes() for f in tracked_files()}
    if ".env" in files or any(f.startswith(".env.") and f != ".env.example" for f in files):
        raise SystemExit("A .env file is tracked by git. Remove it from git before publishing.")
    files["README.md"] = (space_header() + "\n" + (ROOT / "README.md").read_text(encoding="utf-8")).encode("utf-8")
    files["packages.txt"] = (HERE / "packages.txt").read_bytes()
    return files


def git_label() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + (" with uncommitted changes" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown version"


def space_address(space: str) -> str:
    owner, _, name = space.partition("/")
    sub = re.sub(r"[^a-z0-9-]", "-", f"{owner}-{name}".lower())
    return f"https://{sub}.hf.space"


def publish(space: str, dry_run: bool = False) -> None:
    files = build_files()
    size = sum(len(b) for b in files.values()) / 1e6
    print(f"{len(files)} files, {size:.1f} MB, from {git_label()}.")
    if dry_run:
        for f in sorted(files):
            print("  " + f)
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is not set. Add it to .env (HF_TOKEN=...) or to the GitHub secrets, then try again.")

    from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi

    api = HfApi(token=token)
    api.create_repo(space, repo_type="space", space_sdk="gradio", exist_ok=True)
    remote = set(api.list_repo_files(space, repo_type="space"))
    ops = [CommitOperationAdd(path_in_repo=f, path_or_fileobj=b) for f, b in files.items()]
    ops += [CommitOperationDelete(path_in_repo=f) for f in sorted(remote - set(files)) if f != ".gitattributes"]
    api.create_commit(space, repo_type="space", operations=ops, commit_message=f"Deploy {git_label()}")
    print(f"Published. The Space rebuilds itself in a few minutes.\n"
          f"  Space page:     https://huggingface.co/spaces/{space}\n"
          f"  Kitchen board:  {space_address(space)}/\n"
          f"  About page:     {space_address(space)}/about")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Publish BuffetIQ to a Hugging Face Space.")
    parser.add_argument("--space", default=os.environ.get("HF_SPACE"),
                        help="owner/name of the Space, such as your-username/buffetiq (or set HF_SPACE)")
    parser.add_argument("--dry-run", action="store_true", help="list the files that would be sent, and stop")
    args = parser.parse_args(argv)
    if not args.space and not args.dry_run:
        parser.error("give --space your-username/buffetiq, or set HF_SPACE")
    publish(args.space or "", dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
