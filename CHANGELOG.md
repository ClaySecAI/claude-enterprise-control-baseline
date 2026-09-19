# Changelog

Content changes to the baseline itself. Not to be confused with `automation/last-diff.md`, which is a raw diff of an upstream Anthropic source and gets cleared every run — entries land here only once a diff has actually been reviewed and turned into a doc change.

## [Unreleased]

Nothing yet. See `automation/README.md` for how upstream changes get surfaced.

## 2026-09-19 — `Owner` column: who implements each control

The document is organised by Anthropic product surface, which quietly implied every control is an Anthropic setting. Many are not. Those were present but scattered as implementation notes — the egress proxy in 1.7, MDM in 3.11 and 3.15 and 3.17, EDR in 3.16, the IdP dependency in 1.1, SIEM throughout section 5 — so they read as incidental rather than as a layer with its own owners.

- Added an `Owner` column to every control table except section 4's setting baseline, whose ownership is uniform (MDM managed preferences, Windows registry, or server-managed settings) and is stated in prose instead. The CI/CD rows at the end of section 4 do carry it.
- 59 rows classified against a controlled vocabulary: `Anthropic`, `IdP`, `MDM`, `Network`, `Endpoint`, `Browser fleet`, `SIEM`, `CI/CD`, `DNS`, `Process`, with `X + Y` meaning both halves are required and the control is incomplete with either alone.
- **21 of 59 levelled rows are not configured in an Anthropic panel at all.** That number is the substance of the change: a reader who adopts only what the admin console offers has implemented about two thirds of this baseline, and none of what 6.2 identifies as holding the rest up.
- Noted in the new section that several families in the 9.3 crosswalk — SI-3 and SI-4 for EDR, SC-7 for egress, SC-28 for encryption at rest, AU-6 for log review — are satisfied by customer infrastructure rather than by any Anthropic setting, which the control identifiers alone do not reveal.

No control's substance changed, so no `Drafted` date moved. This records who configures each control, not what it should be set to.

First half of #19. The controls that are missing entirely rather than merely scattered — DLP, browser extension install blocklisting, CASB, shadow-AI discovery — still have no home and are the second half.

## 2026-09-18 — watcher reaches `main` only through review

The two watcher stages were separate workflows joined by an issue, and that handoff had never once worked. Stage 1 fired on schedule on 2026-09-14, detected a real change and opened an issue; Stage 2 produced no run at all — not a skipped one, none. GitHub does not fire workflow triggers for events raised with the repository's own `GITHUB_TOKEN`, so the issue was inert, and both halves looked healthy from the Actions tab. The contrast that identified it: twelve issues created the same week through the API with a user token each produced a Stage 2 run, correctly skipped by the label guard.

- Merged both stages into `watch-anthropic-updates.yml` as dependent jobs of one run. A job dependency involves no event, so the restriction does not apply. `workflow_dispatch` and `repository_dispatch` are suppressed the same way and would not have helped.
- **The watcher no longer pushes to `main`.** Snapshots go to a `watch/upstream-<date>-<run>` branch and reach `main` only through a reviewed pull request. This is what lets `main` carry a protection ruleset, and it makes "a security baseline must not rewrite itself unreviewed" structural rather than aspirational — previously the snapshot half of that promise was a direct push.
- The snapshot PR is opened by the `check` job, before any model runs. It has to advance even when nothing is baseline-relevant, or the same diff re-reports weekly forever; opening it early means that still happens when the `draft` job fails or `ANTHROPIC_API_KEY` is unset. An unconfigured repository degrades to "you get told what changed", not to silence.
- The `draft` job now adds its changes to that same branch and updates the PR body, rather than opening a second PR. On a no-op it comments and leaves the PR open, since the snapshot still wants merging.
- Added a post-action re-validation step running both validators, so a push that does not pass fails the job rather than resting on the prompt having been obeyed.
- Removed `draft-baseline-update.yml`.
- Dropped the path filters from `validate.yml`. A required status check that only runs for some paths never reports on the others, and a check that never reports blocks a pull request forever. Both validators take under a second, so this makes `tables` safe to mark required in a ruleset.

One consequence of the same token restriction remains and is documented rather than worked around: because the `check` job opens the PR with `GITHUB_TOKEN`, `validate.yml` will not auto-run on it. The content is still validated inside the `draft` job, but the PR's own check sits unreported until someone pushes to the branch or closes and reopens it.

## 2026-09-17 — NIST identifiers validated in CI

The verification pass on 2026-09-12 checked every NIST citation by hand and then made no arrangement to keep checking. Stage 2 proposes crosswalk mappings unattended on a small model, and `check_tables.py` validates structure only — it passes a row citing a control that does not exist. That is the one failure mode this repository's central claim cannot survive, so it is now checked by machine on every change.

- Added [`automation/check_nist.py`](automation/check_nist.py). Validates every SP 800-53 Rev 5 and CSF 2.0 identifier under `docs/` against an ID inventory generated from NIST's own OSCAL catalogs. Runs offline against the committed [`automation/state/nist-ids.json`](automation/state/nist-ids.json); `--refresh` regenerates that inventory when NIST publishes a new catalog release.
- Wired into [`validate.yml`](.github/workflows/validate.yml) alongside `check_tables.py`, and added to Stage 2's pre-commit gate. Stage 2 is told not to run `--refresh`, since rewriting the inventory is not what a failing check means.
- **Fixed a bug that made Stage 2's existing validation step unreachable.** Its `--allowedTools` list had no `Bash(python3:*)` entry, so the instruction to run `check_tables.py` before opening a PR could never have executed. Both validators are now runnable there.
- Current counts, produced by the validator rather than asserted: 401 SP 800-53 citations across 72 distinct written references, 149 CSF 2.0 citations across 22 distinct subcategories, all resolving. The prior hand count of "396" in the verification section was stale; the figure is now generated.
- Corrected the CSF 2.0 sourcing claim. That count was attributed to NIST's CPRT export, but CPRT sits on `csrc.nist.gov`, which returns 403 to automated clients and cannot be used from CI. NIST's `usnistgov/oscal-content` repository carries CSF 2.0 alongside SP 800-53 and is reachable, so both catalogs now come from there. The 185-subcategory figure is confirmed correct against it.
- `AC-2j` is now recognised as a statement-part reference rather than treated as a control ID, and reported separately so it stays deliberate.
- Bumped `actions/checkout` from v4 to v5 across all three workflows; v4 pins Node 20, which GitHub has deprecated.

Known limits, documented in [`automation/README.md`](automation/README.md): the validator cannot detect a real-but-wrong mapping (`IA-8`, `IA-5(1)` and `SI-10` all exist and are all wrong for the things they get cited for), and an identifier whose family letters are not a real 800-53 family is skipped rather than flagged.

## 2026-09-12 — `Drafted` column added

Every control row now carries a `Drafted` date: the date that row's substance was last authored against upstream documentation. It is not a "verified on" date and makes no claim about current accuracy.

Its purpose is triage for the automation. When the watcher surfaces an upstream change dated *D*, rows drafted before *D* were written without knowledge of it and are the revision candidates, and a capability with no row at all is a coverage gap wanting a new control. Without the dates, every run would have to re-reason about the whole document to work out what is new.

- 64 rows at 2026-09-11 (original drafting), 27 at 2026-09-12 (substance rewritten in the verification pass below). Rows where only a reference URL changed kept their original date.
- Rule going forward: bump a row's date only when its substance changes. Link, typo, and NIST-identifier fixes do not bump it. New rows are stamped with the day they are added.
- [`automation/check_tables.py`](automation/check_tables.py) enforces table structure and date format; [`validate.yml`](.github/workflows/validate.yml) runs it on every PR, since Stage 2 edits these tables unattended.
- Stage 2's prompt now uses the dates for triage and is told never to backfill dates onto rows it did not edit.

## 2026-09-12 — first verification pass

Every control setting, framework identifier, and link re-checked against primary sources. The document had never been verified row by row before this.

**Wrong, now corrected**

- **Claude in Chrome default flipped.** Anthropic turns it on by default from 2026-09-10 unless previously disabled. The baseline said "off (Enterprise default)", which under-warned. (2.7, intro)
- **Computer Use is available**, not absent as the intro claimed. Dispatch is the genuinely unavailable one, and is Pro/Max limited beta rather than Team. (intro, 3.4)
- **RBAC capability list was incomplete**: 14 claimed, 19 documented, with several names wrong, and the seven admin permission areas omitted entirely. Propagation is up to 15 minutes, not 5. (1.17)
- **Cowork telemetry claim was inverted.** Events are metadata-only by default; prompt text requires opting in via `otlpContentCapture`. The cited `excludePromptFromTelemetry` setting does not exist. (section 5)
- **`managed-mcp.json` attributed to the wrong surface.** It governs Claude Code; Desktop/Cowork uses `managedMcpServers`. "Exclusive control" also overstated it. (3.10)
- **"Global instructions" is a per-user setting**, not the org-wide control the doc described. The org control is organization instructions. (3.6, 3.9)
- **"Chrome-to-Cowork bridge" does not exist** as a toggle; the Cowork control is Built-in browser, and Claude in Chrome is its own section, not under Connectors. (3.5)
- **Plugin states were wrong**: four states, not three, including `Required`; marketplace repos must be private or internal. (3.7)
- **CVEs misattributed.** Both are real and accurately described but are Claude Code CVEs, not Claude Desktop. (3.17)
- **`claude-code-action` v1 has no `allowed_tools` / `disallowed_tools` / `max_turns` inputs** — those are v0.x. v1 uses `claude_args`. (4.35–4.37)
- **Auto-mode guidance was outdated and partly wrong.** The `"$defaults"` sentinel now merges with built-ins, and `environment` is not specially safe. Added `hard_deny` and `classifyAllShell`. (section 4 traps)
- **Console panel locations corrected** throughout sections 1–3; the doc repeatedly said "Console" where the surface is claude.ai Organization settings.
- **NIST fixes**: `AC-2(j)` is not valid Rev 5 notation (now `AC-2j`); `IA-8` covers non-organizational users and was wrong for employee SSO; `IA-5(1)` is Password-based Authentication and was wrong for API key rotation; `SA-15` appeared in the 9.3 crosswalk but in none of the rows it summarized.
- **Five dead links replaced, ~10 changed slugs updated.**

**Checked and found correct**

All 32 Claude Code setting keys exist in the published schema with correct nesting and enums. 396 of 397 SP 800-53 citations valid. All 22 CSF 2.0 subcategories valid. The "1,196 controls across 20 families" figure is exact. Section 8 matches `examples/managed-settings.json`. Managed-settings paths, MDM domain, and registry key all correct.

**Added**

- `managedSourcesBehavior: "merge"` warning — without it, a server-managed + MDM deployment silently applies only one source.
- Six sandbox weakening keys the baseline never pinned (`filesystem.disabled`, `ignoreViolations`, `enableWeakerNetworkIsolation`, `credentials.allowPlaintextInject`, `network.deniedDomains`, `network.strictAllowlist`), each described from the schema's own `description` field, with the `enableWeakerNetworkIsolation` / TLS-inspection conflict against 1.7 called out.

**Self-corrections within this pass**

The first draft of the weakening-keys table inferred three descriptions from key names — the same failure mode this pass exists to catch. Corrected against the schema: `ignoreViolations` is an object (a map of command patterns to exempted paths), not a boolean, so "pin to `false`" was a type error and the hardened state is to omit it; `enableWeakerNetworkIsolation` is macOS-only and specifically governs access to the system TLS trust service, not network isolation generally; `strictAllowlist` is marked UNDOCUMENTED in the schema and is now flagged as such. The 22 CSF 2.0 subcategories, initially checked from recall, were re-checked against NIST's CPRT export. `IA-2(2)` no longer silently replaces the removed `IA-8` without noting that both MFA enhancements depend on the IdP. The 1.17 gating table was updated to the corrected capability names.

## 2026-09-11

- Initial publication: baseline document, NIST SP 800-53 Rev 5 / CSF 2.0 crosswalk, `examples/managed-settings.json`.
