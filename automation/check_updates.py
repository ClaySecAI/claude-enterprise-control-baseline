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

With --cited it instead tracks every Anthropic page the baseline cites,
read from docs/*.md so the tracked set cannot drift from the cited set,
into state/cited/ and last-cited-diff.md. That catches what changelogs
miss: a renamed panel, a flipped default, a setting that moved.
"""
import argparse
import difflib
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
STATE_DIR = ROOT / "state"
DIFF_FILE = ROOT / "last-diff.md"
SOURCES_FILE = ROOT / "sources.json"
DOCS_DIR = ROOT.parent / "docs"
CITED_STATE_DIR = STATE_DIR / "cited"
CITED_DIFF_FILE = ROOT / "last-cited-diff.md"
CITED_HOSTS = ("claude.com", "anthropic.com")  # and their subdomains

# GitHub rejects a pull request body over 65,536 characters, and the report
# becomes the body. A first run that baselines dozens of pages, or a month
# where many pages moved, must still open its PR rather than fail.
REPORT_LIMIT = 60_000

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


# Non-English locale paths (/docs/ja/..., /docs/pt-BR/...) are dropped: both docs
# sitemaps carry ~12 locales and each new page would otherwise appear that many times.
LOCALE_PATH = re.compile(r"/docs/(?!en/)[a-z]{2}(?:-[A-Za-z]{2,4})?/")
ADMIN_PATH = re.compile(r"admin|security|settings|iam", re.IGNORECASE)


def sitemap_urls(raw: str) -> list:
    """Sorted, de-duplicated English-only <loc> values from a plain urlset."""
    urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", raw)
    return sorted({u for u in urls if not LOCALE_PATH.search(u)})


def sitemap_section(label: str, url: str, added: list):
    """Report only added admin-path URLs; None if there is nothing to say."""
    hits = [u for u in added if ADMIN_PATH.search(u)]
    if not hits:
        return None
    lines = "\n".join(f"- {u}" for u in hits)
    return (
        f"### \U0001f9ed New admin-path pages (candidate NEW control row): {label}\n{url}\n"
        f"{len(hits)} new URL(s) matching admin|security|settings|iam "
        f"({len(added)} added in total, the rest filtered as noise).\n\n"
        "**This is a weaker signal than a content diff:** it says a page now exists, "
        "not that anything changed for an administrator. Read each page and decide "
        "whether it documents a capability with no control row. If so, add a row; "
        "this is an *add*, not a *revise* of an existing row.\n\n"
        f"{lines}"
    )


def write_report(sections: list, path: Path) -> None:
    """Write sections to path, cut at a section boundary under REPORT_LIMIT."""
    if not sections:
        if path.exists():
            path.unlink()
        return
    kept, size = [], 0
    for section in sections:
        if size + len(section) + 2 > REPORT_LIMIT:
            break
        kept.append(section)
        size += len(section) + 2
    omitted = len(sections) - len(kept)
    if omitted:
        kept.append(
            f"### \u2702\ufe0f {omitted} more section(s) omitted\n"
            "The report hit the pull request size limit. The snapshot diff in "
            "this pull request carries every change."
        )
    path.write_text("\n\n".join(kept) + "\n")


def report_changed(any_change: bool) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as fh:
            fh.write(f"changed={'true' if any_change else 'false'}\n")
    print("Change detected." if any_change else "No change since last run.")


def cited_urls() -> list:
    """Every claude.com / anthropic.com page linked from docs/*.md, fragment dropped."""
    urls = set()
    for doc in sorted(DOCS_DIR.glob("*.md")):
        for raw in re.findall(r"https?://[^\s)\]>\"`|]+", doc.read_text()):
            parts = urlsplit(raw.rstrip(".,;:"))
            host = parts.netloc.lower()
            if host in CITED_HOSTS or host.endswith(tuple("." + h for h in CITED_HOSTS)):
                urls.add(urlunsplit(parts._replace(fragment="")))
    return sorted(urls)


def snapshot_name(url: str) -> str:
    parts = urlsplit(url)
    return re.sub(r"[^a-z0-9]+", "-", f"{parts.netloc}{parts.path}".lower()).strip("-") + ".txt"


def check_cited() -> int:
    """Diff every cited Anthropic page against its snapshot in state/cited/."""
    CITED_STATE_DIR.mkdir(parents=True, exist_ok=True)
    urls = cited_urls()
    wanted = {snapshot_name(u): u for u in urls}

    sections, baselined = [], []
    any_change = False

    for name, url in wanted.items():
        snapshot_path = CITED_STATE_DIR / name
        try:
            new_text = extract_text(fetch(url), "html")
        except Exception as exc:  # noqa: BLE001 -- surface any fetch failure, don't swallow it
            any_change = True
            sections.append(f"### \u26a0\ufe0f Fetch failed\n{url}\n```\n{exc}\n```")
            continue

        if not snapshot_path.exists():
            # A newly cited page is recorded, not reported: its whole text is
            # not a change, and dozens of previews would bury the real diffs.
            any_change = True
            baselined.append(url)
            snapshot_path.write_text(new_text)
            continue

        old_text = snapshot_path.read_text()
        if old_text != new_text:
            any_change = True
            diff = "\n".join(
                difflib.unified_diff(
                    old_text.splitlines(), new_text.splitlines(),
                    fromfile="previous", tofile="current", lineterm="",
                )
            )
            sections.append(f"### \U0001f514 Cited page changed\n{url}\n```diff\n{diff[:3000]}\n```")
            snapshot_path.write_text(new_text)

    # A page the baseline no longer cites stops being tracked.
    dropped = sorted(p for p in CITED_STATE_DIR.glob("*.txt") if p.name not in wanted)
    for path in dropped:
        any_change = True
        path.unlink()
    if dropped:
        sections.append(
            "### No longer cited\n" + "\n".join(f"- `{p.name}`" for p in dropped)
            + "\n\nSnapshots removed because no document under `docs/` links these pages any more."
        )
    if baselined:
        sections.append(
            f"### \U0001f195 {len(baselined)} newly cited page(s) baselined\n"
            "Recorded for future diffs, not reported as changes:\n"
            + "\n".join(f"- {u}" for u in baselined)
        )

    write_report(sections, CITED_DIFF_FILE)
    report_changed(any_change)
    print(f"{len(urls)} cited pages checked.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cited", action="store_true", help="track the pages docs/*.md cites instead of sources.json")
    if parser.parse_args().cited:
        return check_cited()

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
            if source["type"] == "sitemap":
                new_text = "\n".join(sitemap_urls(fetch(url))) + "\n"
            else:
                new_text = extract_text(fetch(url), source["type"])
        except Exception as exc:  # noqa: BLE001 -- surface any fetch failure, don't swallow it
            any_change = True
            sections.append(
                f"### ⚠️ Fetch failed: {label}\n{url}\n```\n{exc}\n```\n"
                "This source could not be checked this run -- worth a manual look "
                "in case Anthropic changed the URL or started blocking automated fetches."
            )
            continue

        if source["type"] == "sitemap":
            # Add-only: removals are not reported, and the first run just
            # records the baseline rather than listing every existing page.
            new_set = set(new_text.split())
            if snapshot_path.exists():
                old_set = set(snapshot_path.read_text().split())
                section = sitemap_section(label, url, sorted(new_set - old_set))
                if section:
                    sections.append(section)
                if old_set != new_set:
                    any_change = True  # snapshot advances in the PR
            else:
                any_change = True
                sections.append(
                    f"### \U0001f195 New source tracked: {label}\n{url}\n"
                    f"Baseline of {len(new_set)} URLs recorded; nothing reported."
                )
            snapshot_path.write_text(new_text)
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

    write_report(sections, DIFF_FILE)
    report_changed(any_change)
    return 0


if __name__ == "__main__":
    sys.exit(main())
