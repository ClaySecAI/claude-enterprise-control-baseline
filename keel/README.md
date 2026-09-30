# Keel

**A governed personal work agent for regulated enterprises.**

Keel is a working name. This folder is a product and architecture spec. It contains no code yet.

Keel is in the same category as Meta's Muse, a personal AI agent that carries work forward on the user's behalf instead of only answering questions. It is not affiliated with Meta and does not derive from Muse. Muse is built for consumers and small businesses. Keel starts where that design stops: organizations in finance, healthcare, and the public sector, which must prove to an auditor what an agent did, on whose authority, and with which data.

## The one-line thesis

Consumer agents inherit the user's full identity and act on it without limits. A regulated enterprise cannot accept that. Keel gives every agent its own scoped, revocable, audited identity, and makes every action it takes attributable, reviewable, and bounded by policy the tenant controls.

## Scope decisions (from the kickoff)

| Question | Decision |
|---|---|
| What we're building | Our own Muse-class product, not a wrapper around Muse and not a governance guide for Muse |
| Deliverable | Product and architecture spec (this folder). No code. |
| Target customer | Regulated verticals: financial services, healthcare and life sciences, US public sector |
| v1 agent capabilities | Work-app connectors; long-running tasks and goals |
| Explicitly out of v1 | Email and calendar *send* actions, avatar/voice/video, consumer accounts |
| Must-have enterprise controls | SSO/SCIM + RBAC; audit and compliance; data controls; admin and policy |

## Documents

| # | Doc | What it answers |
|---|---|---|
| 1 | [Scope and decisions](docs/01-scope-and-decisions.md) | Who it's for, what's in and out, the design principles every later choice is checked against |
| 2 | [Product requirements](docs/02-product-requirements.md) | Personas, core jobs, functional requirements with IDs, the enterprise feature set |
| 3 | [Architecture](docs/03-architecture.md) | Components, deployment models, agent runtime, connector framework, task engine, data flow |
| 4 | [Security and compliance](docs/04-security-and-compliance.md) | Identity model, policy engine, audit, data controls, threat model, framework mapping |
| 5 | [Roadmap and open questions](docs/05-roadmap-and-open-questions.md) | Phased delivery, exit criteria, and the decisions still to make |

## Relationship to the Claude Enterprise Control Baseline

Keel's model layer is Claude. The [Claude Enterprise Control Baseline](../README.md) is the control set for *consuming* Claude in an enterprise. Keel reuses its L1/L2/L3 profile levels and its NIST SP 800-53 Rev 5 spine. Keel also sets out to close three gaps that baseline documents as unsolved (section 6 and 9.5 there): unattended autonomous execution, non-human agent identity, and centrally unreviewable configuration. Doc 4 traces each one.
