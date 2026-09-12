#!/usr/bin/env python3
"""
Stage 1 of the staleness watcher.

Fetches each source in sources.json, extracts visible text, and diffs it
against the last committed snapshot in state/. Writes a human-readable
summary of anything new or changed to last-diff.md and reports via
GITHUB_OUTPUT whether the workflow should open an issue.

Deliberately does no judgment about relevance -- that's Stage 2's job,
run by a human or an LLM reading the issue this creates. This script only
answers "did any of these three pages change since we last looked."
"""
import difflib
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_DIR = ROOT / "state"
DIFF_FILE = ROOT / "last-diff.md"
SOURCES_FILE = ROOT / "sources.json"

USER_AGENT = (
    "Mozilla/5.0 (compatible; claude-enterprise-control-baseline-watcher/1.0; "
    "+https://github.com/ClaySecAI/claude-enterprise-control-baseline)"
)


class TextExtractor(HTMLParser):
    """Strips tags/scripts/styles, keeps visible text, one chunk per line."""

    def __init__(self):
        super().__init__()
        self.chunks = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "header", "footer"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "header", "footer") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self.chunks.append(text)

    def get_text(self):
        return "\n".join(self.chunks)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def normalize(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def extract_text(raw: str, source_type: str) -> str:
    if source_type == "raw":
        return normalize(raw)
    parser = TextExtractor()
    parser.feed(raw)
    return normalize(parser.get_text())


def main() -> int:
    sources = json.loads(SOURCES_FILE.read_text())
    STATE_DIR.mkdir(exist_ok=True)

    sections = []
    any_change = False

    for source in sources:
        sid = source["id"]
        label = source["label"]
        url = source["url"]
        snapshot_path = STATE_DIR / f"{sid}.txt"

        try:
            new_text = extract_text(fetch(url), source["type"])
        except Exception as exc:  # noqa: BLE001 -- surface any fetch failure, don't swallow it
            any_change = True
            sections.append(
                f"### ⚠️ Fetch failed: {label}\n{url}\n```\n{exc}\n```\n"
                "This source could not be checked this run -- worth a manual look "
                "in case Anthropic changed the URL or started blocking automated fetches."
            )
            continue

        if not snapshot_path.exists():
            any_change = True
            preview = new_text[:4000]
            sections.append(
                f"### \U0001f195 New source tracked: {label}\n{url}\n"
                f"No prior snapshot -- this is the baseline for future diffs.\n"
                f"```\n{preview}\n```"
            )
            snapshot_path.write_text(new_text)
            continue

        old_text = snapshot_path.read_text()
        if old_text != new_text:
            any_change = True
            diff = "\n".join(
                difflib.unified_diff(
                    old_text.splitlines(),
                    new_text.splitlines(),
                    fromfile="previous",
                    tofile="current",
                    lineterm="",
                )
            )
            sections.append(
                f"### \U0001f514 Change detected: {label}\n{url}\n```diff\n{diff[:6000]}\n```"
            )
            snapshot_path.write_text(new_text)

    if sections:
        DIFF_FILE.write_text("\n\n".join(sections) + "\n")
    elif DIFF_FILE.exists():
        DIFF_FILE.unlink()

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as fh:
            fh.write(f"changed={'true' if any_change else 'false'}\n")

    print("Change detected." if any_change else "No change since last run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
