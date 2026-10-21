#!/usr/bin/env python3
"""
Sweeps every link in docs/*.md and classifies each one, rather than passing or
failing it.

A naive checker cries wolf here. github.com answers automated clients with
403, some hosts refuse the connection outright, and csrc.nist.gov blocks CI,
so treating every non-200 as broken reports a dozen false failures a run and
gets muted. Only a definite 404 or 410 is a failure. Everything else is
information:

  dead          404 or 410. Fails the run.
  redirected    Resolves, but to a different URL. Update the document to the
                target, so a slug change shows up as a diff rather than
                resolving silently until the redirect is retired.
  unverifiable  403, 405, 429, 5xx, a timeout or a refused connection. Says
                nothing about the page, only about this network.
  ok            2xx at the URL as written.

Writes a Markdown report to last-links.md and, in Actions, to the job
summary. Exits 1 only when something is dead. No dependencies.
"""
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT.parent / "docs"
REPORT = ROOT / "last-links.md"

# A browser user agent: some documentation hosts serve bots a challenge page.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
LINK = re.compile(r"https?://[^\s)\]>\"`|]+")
DEAD = {404, 410}
# Example values in the document, not links to check.
PLACEHOLDER_HOSTS = ("your-domain", "example.com", "example.org", "localhost")


def links() -> dict:
    """URL (fragment dropped) -> sorted list of 'doc:line' where it appears."""
    found: dict = {}
    for doc in sorted(DOCS_DIR.glob("*.md")):
        for lineno, line in enumerate(doc.read_text().split("\n"), 1):
            for raw in LINK.findall(line):
                url = urlunsplit(urlsplit(raw.rstrip(".,;:'"))._replace(fragment=""))
                host = urlsplit(url).netloc.lower()
                if any(p in host for p in PLACEHOLDER_HOSTS):
                    continue
                found.setdefault(url, []).append(f"{doc.name}:{lineno}")
    return found


def same_place(a: str, b: str) -> bool:
    """Treat a trailing slash or an http-to-https upgrade as no redirect."""
    pa, pb = urlsplit(a), urlsplit(b)
    return (pa.netloc.lower(), pa.path.rstrip("/"), pa.query) == (pb.netloc.lower(), pb.path.rstrip("/"), pb.query)


def probe(url: str) -> tuple:
    """(class, detail). Tries HEAD, and GET whenever HEAD does not succeed."""
    last = ""
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                final = resp.geturl()
                if same_place(url, final):
                    return "ok", str(resp.status)
                return "redirected", final
        except urllib.error.HTTPError as exc:
            last = str(exc.code)
            if method == "HEAD":
                # Some hosts answer HEAD with 404, 403 or 405 and serve GET
                # fine (nvlpubs.nist.gov 404s a HEAD for a live PDF), so only
                # a GET verdict counts.
                continue
            if exc.code in DEAD:
                return "dead", last
            return "unverifiable", last
        except Exception as exc:  # noqa: BLE001 -- timeouts, TLS, refused connections
            last = type(exc).__name__
            if method == "HEAD":
                continue
    return "unverifiable", last


def main() -> int:
    found = links()
    if not found:
        print(f"FAIL no links found under {DOCS_DIR}")
        return 1

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(zip(found, pool.map(probe, found)))

    by_class: dict = {"dead": [], "redirected": [], "unverifiable": [], "ok": []}
    for url, (cls, detail) in sorted(results.items()):
        by_class[cls].append((url, detail, found[url]))

    lines = [f"# Link check: {len(found)} distinct links in docs/\n"]
    lines.append(
        f"{len(by_class['dead'])} dead, {len(by_class['redirected'])} redirected, "
        f"{len(by_class['unverifiable'])} unverifiable from this network, {len(by_class['ok'])} ok.\n"
    )
    titles = {
        "dead": "Dead (404 or 410): fix these",
        "redirected": "Redirected: update the document to the target",
        "unverifiable": "Unverifiable from this network: not failures",
    }
    for cls, title in titles.items():
        if not by_class[cls]:
            continue
        lines.append(f"\n## {title}\n")
        for url, detail, where in by_class[cls]:
            arrow = f" -> {detail}" if cls == "redirected" else f" ({detail})"
            lines.append(f"- {url}{arrow}  \n  cited at {', '.join(where)}")
    report = "\n".join(lines) + "\n"

    REPORT.write_text(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(report)
    print(report)
    return 1 if by_class["dead"] else 0


if __name__ == "__main__":
    sys.exit(main())
