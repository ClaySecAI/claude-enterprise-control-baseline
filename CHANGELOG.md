# Changelog

Content changes to the baseline itself. Not to be confused with `automation/last-diff.md`, which is a raw diff of an upstream Anthropic source and gets cleared every run — entries land here only once a diff has actually been reviewed and turned into a doc change.

## [Unreleased]

Nothing yet. See `automation/README.md` for how upstream changes get surfaced.

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
