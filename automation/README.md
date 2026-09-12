# Staleness watcher

Two stages. Only the first exists yet.

**Stage 1 (this one, automated, no judgment involved).** [`watch-anthropic-updates.yml`](../.github/workflows/watch-anthropic-updates.yml) runs weekly, or on demand via `workflow_dispatch`. It calls [`check_updates.py`](check_updates.py), which fetches the sources in [`sources.json`](sources.json), diffs each against the snapshot committed under `state/`, and:

- if nothing changed: does nothing.
- if something changed: commits the new snapshot and opens an issue labeled `anthropic-update` with the diff.

Sources tracked, and why these three: they're the only sources Anthropic actually dates and changelogs, and they map onto the baseline's three surfaces.

| Source | Surface | Why this one |
|---|---|---|
| [Claude Platform release notes](https://platform.claude.com/docs/en/release-notes/overview) | Web / Console / org settings | Covers Console, API, SDKs |
| [Claude Apps release notes](https://support.claude.com/en/articles/12138966-release-notes) | Web / Desktop / Claude in Chrome | Covers claude.ai and Claude Desktop |
| [claude-code CHANGELOG.md](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md) | CLI / managed settings | Raw markdown, dated by version |

**Known gap:** this only catches what Anthropic changelogs. It won't catch a console setting that changed silently, or a genuinely new admin page nobody's written release notes for yet. Two ways to close that, not yet built:

1. Add the ~40 pages already cited as sources throughout [`docs/claude-enterprise-control-baseline.md`](../docs/claude-enterprise-control-baseline.md) to `sources.json` on a slower cadence (monthly), so a silently-edited settings page still shows up as a diff.
2. Diff `sitemap.xml` on `platform.claude.com` / `code.claude.com` (if published) against a stored URL list, to flag a brand-new page under an admin/security path before anyone's blogged about it.

**Also known:** the Claude Apps release-notes page is a Zendesk Help Center article with the full site sidebar nav on it, so a new unrelated help article elsewhere on the site can trigger a false-positive diff. Cheaper to tolerate a false positive you dismiss than to write brittle selector-scraping that silently breaks when the site's markup changes.

**Stage 2 (not built yet).** Something — you, or a Claude Code Action triggered off the `anthropic-update` label — reads the diff in the issue, decides whether it's baseline-relevant, and if so opens a PR that: adds/updates the relevant control row with today's date, and adds an entry to [`CHANGELOG.md`](../CHANGELOG.md). Deliberately never auto-merges; a security baseline shouldn't rewrite itself unreviewed.

## Running it locally

```bash
python3 automation/check_updates.py
cat automation/last-diff.md   # only exists if something changed
```

No dependencies beyond the standard library.
