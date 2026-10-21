# Proposal: a Claude in Chrome profile with real L1, L2 and L3 (#17)

Status: accepted 2026-10-21 and folded into the baseline (section 2, "Claude in Chrome profile"). The three questions under "Not verified" were answered there; see `CHANGELOG.md`. Kept as the record of the decision.

## The problem

Claude in Chrome carries the worst residual risk in the baseline (7.6: roughly a 1 percent self-reported attack success rate after mitigations), and the least structure. Its controls are spread across 2.7 to 2.9 in the Web section, 3.5 in Desktop and 6.1 in the customer-owned layer. Every one is tagged L2, so there is no L1 and no L3 guidance at all.

That matters most at L1. Per [Claude in Chrome admin controls](https://support.claude.com/en/articles/13065128-claude-in-chrome-admin-controls), on Enterprise the extension "is on by default unless you've already disabled it". The exception is organizations with HIPAA enabled, where it stays off until turned on. An org that adopts only L1 today is told nothing about a surface that is already live in its tenant.

## Recommendation: a profile table, not a new section

\#17 proposes moving these rows into a section of their own. Doing that means renumbering 2.7 to 2.9, 3.5 and 6.1. The baseline now forbids renumbering a control, because other rows, the crosswalk and outside readers cite controls by ID, and #38 showed what renumbering breaks.

So keep the rows where they are and add one subsection, **"Claude in Chrome profile"**, at the end of section 2. It holds a level table that cites them, so Chrome reads as a surface without any ID moving:

| Control | L1 | L2 | L3 |
|---|---|---|---|
| 2.7 Org toggle | **Set it explicitly**, on or off. Never inherit the default. | On only for roles granted the Claude in Chrome capability (1.20). Strict allowlist of 5 to 10 domains. | Off, or a named pilot group under a written risk acceptance. |
| 2.8 Blocklist | Defaults plus cloud consoles, SSO admin panels and password-manager vaults. | The full list in 2.8. | Not applicable while off. |
| 2.9 Password managers | Off. | Off unless explicitly risk-accepted. | Off. |
| 3.5 Cowork built-in browser | Verify its state. | Off unless justified. | Off. |
| 6.1 Extension install control | Know where it is installed, through browser management inventory. | Block unmanaged installs; force-install the approved build to managed profiles. | Block the extension on managed profiles entirely. |
| Session transcripts (5.2) | None. | Ingest, noting the Chrome coverage is beta (7.1). | Ingest, and confirm completeness before relying on it. |

The L1 column is the real addition. "Set the toggle deliberately" is cheap and is currently nowhere at L1. The L3 column makes "off" an explicit answer rather than an absence.

## What changes in the rows themselves

- **2.7** stays L2 for its allowlist content. Its "set it explicitly" sentence moves into the profile's L1 cell, so an L1 adopter sees it.
- **6.1**'s level cell becomes "see the Claude in Chrome profile", because its right value differs by level.
- **Crosswalk:** the existing "2.7 to 2.9 Claude in Chrome" row is unchanged. The profile table carries no new controls, so it needs no crosswalk row.

## Verified for this proposal (2026-10-21)

- **Admin path:** Organization settings, Claude in Chrome. **Password managers** is the 1Password toggle, off by default ([1Password for Claude](https://support.claude.com/en/articles/15936181-get-started-with-1password-for-claude)).
- **Default:** on unless previously disabled, with the HIPAA exception above.

## Not verified, and needed before folding in

- **Allowlist versus blocklist:** how they interact when both are set. The admin-controls article describes both but not their precedence.
- **RBAC gating:** whether the Claude in Chrome RBAC capability gates the extension, or only some of its features.
- **Policy keys in 6.1:** the browser policy key names for force-install and blocklisting. 6.1 already flags these as general practice, not verified against Chrome's enterprise policy reference.

## Effort

About an hour to fold in once accepted, mostly the profile table and two row edits. No validator changes are needed: `check_tables.py` already handles a non-control table.
