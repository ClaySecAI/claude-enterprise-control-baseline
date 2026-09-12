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

**Stage 2.** [`draft-baseline-update.yml`](../.github/workflows/draft-baseline-update.yml) triggers off the same `anthropic-update` issue (on `opened` or `labeled`, or manually via `workflow_dispatch` with an `issue_number`). It runs the [Claude Code GitHub Action](https://github.com/anthropics/claude-code-action) with a fixed prompt: read the issue's diff, read the current baseline, judge whether each change is admin/security-relevant, and:

- if nothing is relevant: comment on the issue explaining why, close it, and stop — no PR for a no-op.
- if something is relevant: update or add the affected control row (adding a "Verified" column to that table if it doesn't have one yet, defaulting *other* rows in that table to `—` rather than backfilling a date on rows nobody actually rechecked), add a dated `CHANGELOG.md` entry, and open a PR against `main` that closes the tracking issue on merge.

It never merges its own PR, never pushes to `main`, and is instructed to mark any NIST crosswalk it isn't confident about as `(proposed — verify)` rather than presenting a guess as settled. You are still the reviewer of record for every PR it opens.

Runs on Claude Haiku 4.5 (`--model claude-haiku-4-5-20251001` in `claude_args`), not Sonnet — this is a triage/drafting task gated by human review either way, so the cheaper model is the right tradeoff. Bump it back to a Sonnet model in the workflow if the PRs it drafts turn out to need better judgment than Haiku gives.

We looked at routing this through Nous Portal instead of the direct Anthropic API to cut cost further, but its `inference-api.nousresearch.com` endpoint speaks an OpenAI-chat-completions-style schema, while Claude Code's `ANTHROPIC_BASE_URL` only speaks Anthropic's native Messages API — incompatible wire formats, not just a config toggle. Bridging that would mean adding an unofficial translation proxy into this repo's own CI, which is more attack surface and trust exposure than it's worth for a hardening reference. Model choice was the actual lever for cost; we used it directly instead.

**Setup required before Stage 2 can run:** it needs an `ANTHROPIC_API_KEY` repo secret. Add it yourself — this is not something to hand to any automation:

```bash
gh secret set ANTHROPIC_API_KEY --repo ClaySecAI/claude-enterprise-control-baseline
```

Until that secret exists, the workflow will trigger and fail visibly at the Claude Code Action step rather than silently doing nothing.

## Running it locally

```bash
python3 automation/check_updates.py
cat automation/last-diff.md   # only exists if something changed
```

No dependencies beyond the standard library.
