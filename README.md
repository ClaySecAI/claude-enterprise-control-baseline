# Claude Enterprise Control Baseline

A setting-by-setting security hardening baseline for Claude Enterprise deployments, mapped to NIST SP 800-53 Rev 5 and NIST CSF 2.0.

Covers three surfaces:

- **Web** (claude.ai): org settings, connectors, projects, Claude in Chrome
- **Desktop** (Claude Desktop / Cowork): agent toggles, MCP and plugin control, scheduled tasks, endpoint posture
- **CLI** (Claude Code): managed settings, permission rules, sandboxing, CI/CD

## Why this exists

CIS does not publish a product Benchmark for Claude, and Anthropic publishes the raw admin documentation but not a hardening baseline. NIST's own AI-specific control work is not finished: the COSAiS overlays (NISTIR 8605 series) that would formally tailor SP 800-53 for generative AI and agentic systems are still in development, and the only published draft covers predictive AI, which is the one use case a Claude Enterprise deployment does not touch.

This fills the gap in the meantime: an assessable control layer built on SP 800-53 Rev 5, structured so the COSAiS overlays drop in cleanly when they publish.

## Contents

| Path | What it is |
|---|---|
| [`docs/claude-enterprise-control-baseline.md`](docs/claude-enterprise-control-baseline.md) | The baseline. Control tables per surface, NIST crosswalk, threat mapping, known gaps, operating cadence. |
| [`examples/managed-settings.json`](examples/managed-settings.json) | L2 Claude Code managed settings policy, ready for MDM deployment |
| [`CHANGELOG.md`](CHANGELOG.md) | What's changed in the baseline itself, and when |
| [`automation/`](automation/README.md) | Weekly watcher that flags upstream Anthropic changes worth reviewing against this baseline |

## Profile levels

| Level | Intent |
|---|---|
| L1 | Minimum baseline. Adopt everywhere. |
| L2 | Security-sensitive environments. Default target for most enterprises. |
| L3 | Regulated workloads. Accepts functionality loss. |

## How to use it

1. Read section 9.1 first. It explains which NIST publication does what, and why SP 800-53 is the spine rather than the AI RMF.
2. Work section 1 before anything else. Nothing in sections 2 through 4 holds without SSO, SCIM, tenant restrictions, and the Compliance API.
3. Pick a profile level per surface. They do not have to match.
4. Read section 6 before you present this to anyone. The known gaps are the part that changes decisions.
5. Deploy `examples/managed-settings.json` via MDM or server-managed settings after replacing the placeholders listed below.

## Placeholders to replace

The example policy ships with deliberate placeholders. Replace before deploying:

- `forceLoginOrgUUID` — your organization UUID
- `strictKnownMarketplaces[].repo` — `YOUR-ORG/approved-claude-plugins`
- `allowedHttpHookUrls` — `https://hooks.YOUR-DOMAIN/*`
- `pluginTrustMessage` — your approval channel
- `sandbox.network.allowedDomains` — your tested registry list

## Accuracy and staleness

Anthropic ships admin console changes roughly monthly, and reorganized its documentation across `platform.claude.com`, `code.claude.com`, and `support.claude.com` during 2026. Some links may redirect.

The NIST draft statuses cited (IR 8596 preliminary draft, COSAiS NISTIR 8605 series in development) were verified 2026-09-11 and will change.

**Verified 2026-09-12.** Every control setting, framework identifier, and link was re-checked against primary sources — the settings JSON schema, NIST's OSCAL Rev 5 catalog, and Anthropic's current admin documentation. That pass found and fixed real errors, including a Claude in Chrome default that flipped to *on* on 2026-09-10, an inverted claim about Cowork telemetry defaults, an incomplete RBAC capability list, and five dead links. See [CHANGELOG.md](CHANGELOG.md) for the full list and the verification section at the top of the baseline for what was confirmed correct and what remains unverified.

Validate every setting against your own tenant before adopting. Issues and PRs welcome, particularly corrections where a setting has moved or a value is wrong.

A [weekly watcher](automation/README.md) checks Anthropic's own release notes and changelogs and opens an issue when something changed. It flags candidates for review — it does not decide relevance and does not edit the baseline itself.

## Disclaimer

This is personal work. It is not endorsed by, does not represent, and does not describe the security posture of my employer or of Anthropic. It is compiled from publicly available documentation and is offered as a starting point, not as an authoritative standard. No warranty of any kind.

## License

MIT. See [LICENSE](LICENSE).
