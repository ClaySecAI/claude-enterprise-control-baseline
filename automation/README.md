# Staleness watcher

Two stages, both in [`watch-anthropic-updates.yml`](../.github/workflows/watch-anthropic-updates.yml) as dependent jobs of one run. Stage 1 detects upstream change; Stage 2 drafts the baseline update for review. Nothing here pushes to `main`.

**Stage 1, the `check` job. Automated, no judgment involved.** Runs weekly, or on demand via `workflow_dispatch`. It calls [`check_updates.py`](check_updates.py), which fetches the sources in [`sources.json`](sources.json), diffs each against the snapshot committed under `state/`, and:

- if nothing changed: does nothing.
- if something changed: pushes the new snapshots to a `watch/upstream-<date>-<run>` branch and opens a pull request labeled `anthropic-update` carrying the diff in its body.

The snapshot advances in that PR rather than in the drafting job on purpose. It has to advance even when nothing turns out to be baseline-relevant, or the same diff re-reports every week forever — and doing it here means it still happens if the drafting job fails or `ANTHROPIC_API_KEY` is unset. The failure mode is a one-line snapshot PR to merge, not silence.

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

**The `Drafted` column.** Every control row in the baseline carries the date its substance was last authored against upstream docs. It is not a "verified on" date. It exists so the `draft` job can triage an upstream change dated *D*: rows drafted before *D* were written without knowledge of it and are revision candidates, while a capability with no row at all is a coverage gap wanting a new control. Bump a row's date only when its substance changes — a link or typo fix does not count — and never backfill dates onto rows you did not edit, because that erases the signal. [`check_tables.py`](check_tables.py) enforces the structure and runs on every PR via [`validate.yml`](../.github/workflows/validate.yml).

**Stage 2, the `draft` job.** Depends on `check` and runs only when it reports a change. It checks out the branch `check` just pushed and runs the [Claude Code GitHub Action](https://github.com/anthropics/claude-code-action) with a fixed prompt: read the diff, read the current baseline, judge whether each change is admin/security-relevant, and:

- if nothing is relevant: comment on the PR explaining why, and stop. The PR stays open, because it still carries the snapshot update a human should merge.
- if something is relevant: update or add the affected control row, bump only that row's `Drafted` date, add a dated `CHANGELOG.md` entry, commit to the same branch, and rewrite the PR body to say what changed and what was deliberately skipped.

It runs both validators before committing, and the job re-runs them afterwards as a backstop so a push that does not pass fails the job loudly rather than resting on the prompt having been obeyed. It never merges the PR, never pushes to `main`, and is instructed to mark any NIST crosswalk it isn't confident about as `(proposed — verify)` rather than presenting a guess as settled. You are still the reviewer of record.

**Why one workflow and not two.** The two stages used to be separate workflows joined by an issue: Stage 1 opened it, Stage 2 triggered on it. That handoff never worked once. GitHub does not fire workflow triggers for events raised with the repository's own `GITHUB_TOKEN`, so the issue was inert — no Stage 2 run was created at all, not even a skipped one, and both halves looked healthy from the Actions tab. `workflow_dispatch` and `repository_dispatch` are suppressed identically, so dispatching across workflows is not a way around it. Job dependencies inside a single run are, because no event is involved.

The same restriction has one consequence left over: because the `check` job opens the PR with `GITHUB_TOKEN`, [`validate.yml`](../.github/workflows/validate.yml) will not auto-run on it. The content is still checked — both validators run inside the `draft` job — but the PR's own check will sit unreported until a human pushes to the branch or closes and reopens the PR. Worth knowing before marking `tables` a required check in a ruleset.

Runs on Claude Haiku 4.5 (`--model claude-haiku-4-5-20251001` in `claude_args`), not Sonnet — this is a triage/drafting task gated by human review either way, so the cheaper model is the right tradeoff. Bump it back to a Sonnet model in the workflow if the PRs it drafts turn out to need better judgment than Haiku gives.

We looked at routing this through Nous Portal instead of the direct Anthropic API to cut cost further, but its `inference-api.nousresearch.com` endpoint speaks an OpenAI-chat-completions-style schema, while Claude Code's `ANTHROPIC_BASE_URL` only speaks Anthropic's native Messages API — incompatible wire formats, not just a config toggle. Bridging that would mean adding an unofficial translation proxy into this repo's own CI, which is more attack surface and trust exposure than it's worth for a hardening reference. Model choice was the actual lever for cost; we used it directly instead.

**Setup required before the `draft` job can run:** it needs an `ANTHROPIC_API_KEY` repo secret. Add it yourself — this is not something to hand to any automation:

```bash
gh secret set ANTHROPIC_API_KEY --repo ClaySecAI/claude-enterprise-control-baseline
```

Until that secret exists, the `draft` job fails visibly at the Claude Code Action step. The `check` job is unaffected and still opens its snapshot PR, so an unconfigured repository degrades to "you get told what changed" rather than to silence.

## Validators

Two, both wired to [`validate.yml`](../.github/workflows/validate.yml), both run by the `draft` job before it commits, and both re-run by that job afterwards as a backstop.

[`check_tables.py`](check_tables.py) checks structure: every control table's column counts line up, and every control row carries a well-formed `Drafted` date.

[`check_nist.py`](check_nist.py) checks that every SP 800-53 Rev 5 and CSF 2.0 identifier in `docs/` actually exists. This matters because the `draft` job proposes NIST crosswalks unattended on a small model, and structure validation will happily pass a row citing a control that was never written. For a document whose central claim is that its citations were verified, that was the gap worth closing.

It validates against [`state/nist-ids.json`](state/nist-ids.json), an ID inventory generated from NIST's own OSCAL catalogs, so CI needs no network and the result is deterministic. Regenerate it when NIST publishes a new release of either catalog:

```bash
python3 automation/check_nist.py --refresh
```

Both catalogs come from [`usnistgov/oscal-content`](https://github.com/usnistgov/oscal-content), which carries CSF 2.0 as well as SP 800-53 — worth knowing, because `csrc.nist.gov` returns 403 to automated clients and cannot be used from CI.

Two limits to be honest about. **A real ID can still be the wrong mapping**, and no catalog check detects that: `IA-8` exists but is non-organizational users and is wrong for employee SSO, `IA-5(1)` exists but is password-based authenticators and is wrong for API key rotation, and `SI-10` exists but does not reach prompt injection. Semantic fit stays a human job, which is why the `draft` job is told to mark uncertain mappings `(proposed — verify)`. Second, an identifier whose *family* letters are not a real 800-53 family is skipped rather than flagged, so `ZZ-1` passes silently; this keeps unrelated identifiers elsewhere in the document from being misread as citations, at the cost of not catching a typo in the family itself.

One parsing detail worth preserving if this is ever rewritten: a naive `[A-Z]{2}-\d+` pattern matches the tail of every CSF subcategory — `PR.PS-01` yields `PS-01`, `DE.CM-09` yields `CM-09` — and because `PS`, `CM`, `IR`, `RA` and `SC` are all real 800-53 families, those phantoms survive the family filter and report as eleven failures that are not real. The negative lookbehind in `SP_REF` is what prevents that.

## Running it locally

```bash
python3 automation/check_updates.py           # diff the tracked sources
cat automation/last-diff.md                   # only exists if something changed
python3 automation/check_tables.py            # control tables and Drafted dates
python3 automation/check_nist.py              # NIST identifiers resolve
python3 automation/check_nist.py --refresh    # rebuild the NIST ID inventory
```

No dependencies beyond the standard library.
