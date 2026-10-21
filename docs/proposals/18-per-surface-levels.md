# Proposal: define L1, L2 and L3 per surface (#18)

Status: proposal for review. Nothing here changes the baseline until it is accepted and folded in.

## Where it stands

Counted from the document as it stands once #41 is merged (2026-10-21):

| Section | L1 | L2 | L3 | Form |
|---|---:|---:|---:|---|
| 1. Org-wide prerequisites | 8 | 11 | 1 | `Level` column |
| 2. Web (claude.ai) | 6 | 9 | **0** | `Level` column |
| 3. Desktop (Cowork) | 6 | 12 | 1 | `Level` column |
| 4. CLI settings | 37 rows, a value at each level | | | `L1` / `L2` / `L3` columns |
| 4. CI/CD rows | no level | | | |
| 5. Monitoring and audit | no level | | | |
| 6. Customer-owned layer | 1 | 5 | 0 | `Level` column |

Only the CLI composes: read its L2 column and you have a complete policy, shipped as `examples/managed-settings.json`. Elsewhere a `Level` tag says which level a row first applies at, not what the setting should be at the other two. Web has no L3 row at all, and Desktop has one (3.12).

## Recommendation

1. **Convert sections 2 and 3 to the three-column form section 4 uses.** Replace `Level` and `Baseline value` with `L1`, `L2` and `L3` value columns, keeping the location column. This forces an answer per level per control, which is what surfaces the missing L3s. A rollup table alone would let them stay missing by omission. It widens two tables; that cost is worth it for the two surfaces whose L3 is undefined.
2. **Leave section 1 on its `Level` column.** Its rows are prerequisites, and nearly all of them apply unchanged once adopted: SSO, provisioning, owner count, Compliance API. A three-column form there would repeat the same value three times.
3. **Say in one sentence each that section 5 and the section 4 CI/CD rows are level-independent**, applying at every level, if that is the intent. Silence reads as an oversight.
4. **Teach `check_tables.py` that a control table in sections 2 to 4 must carry `L1`, `L2` and `L3` columns**, so the form cannot regress. That is the same spirit as #12.

## Starting L3 values for Web and Desktop

These are a draft to argue with, not settled values. Each is the most restrictive setting that still leaves the surface usable for a regulated workload.

**Web (section 2):**

- **2.1** Only connectors with a completed vendor review.
- **2.2** Needs approval for every write action.
- **2.3** Write tools blocked.
- **2.4** On.
- **2.5** No custom remote MCP connectors, or internally hosted ones only, after review.
- **2.6** Egress off.
- **2.7 to 2.9** Off; see the Chrome profile in the #17 proposal.
- **2.10** Share projects off and Public projects off.
- **2.11** Rate chats off.
- **2.13** Templates off.
- **2.14, 2.15** Off.
- **2.16** Off.

**Desktop (section 3):**

- **3.1** Cowork off, or a named pilot group.
- **3.2, 3.3, 3.5** Off.
- **3.6** Deployed.
- **3.7** Not available, except Required plugins from the internal marketplace.
- **3.10** Exclusive `managed-mcp.json` allowlist.
- **3.11** Signing required.
- **3.12** Off (already L3).
- **3.13** Locked per tool.
- **3.14** Dedicated folder.
- **3.15 to 3.17** As at L2.
- **3.18** Scheduled tasks prohibited by AUP, with `keepAwakeEnabled: false`.
- **3.19** Live artifacts off.
- **3.20** As at L2.

## Effort

About half a day: two table conversions, about 34 rows, each needing a deliberate value at L1 and L3. Plus the validator rule and a short note in the Profile levels section saying what a per-surface level now means.
