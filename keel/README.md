# Keel

**A governed personal work agent for regulated enterprises.**

Keel is a working name. This folder is a product and architecture spec. It contains no code yet.

Keel is in the same category as Meta's Muse, a personal AI agent that carries work forward on the user's behalf instead of only answering questions. It is not affiliated with Meta and does not derive from Muse. Muse is built for consumers and small businesses. Keel starts where that design stops: organizations in finance, healthcare, and the public sector, which must prove to an auditor what an agent did, on whose authority, and with which data.

## The one-line thesis

Consumer agents inherit the user's full identity, act on it without limits, and come welded to one vendor's model. A regulated enterprise cannot accept that. Keel gives every agent its own scoped, revocable, audited identity, and makes every action it takes attributable, reviewable, and bounded by policy the tenant controls, on whatever model the tenant has already approved.

## What makes it different

1. **The agent is not the user.** Coding and desktop agents (Claude Code, Cowork) and consumer agents (Muse) act with the user's own credentials, so the agent can reach whatever the user can. A Keel agent starts with no access. For each approved action it gets a short-lived credential scoped to that one action, capped by the user's permissions, tenant policy, and the plan the user approved. See [doc 4, section 4.1.1](docs/04-security-and-compliance.md#411-how-this-differs-from-user-inherited-agents).
2. **Bring your own model.** It runs on the models the customer has already approved, including self-hosted ones.
3. **Every action is attributable.** Audit records are written before the action runs, so each action traces back to a person, a plan step, and a policy decision.

## Scope decisions (from the kickoff)

| Question | Decision |
|---|---|
| What we're building | Our own Muse-class product, not a wrapper around Muse and not a governance guide for Muse |
| Deliverable | Product and architecture spec (this folder). No code. |
| Target customer | Regulated verticals: financial services, healthcare and life sciences, US public sector |
| v1 agent capabilities | Work-app connectors; long-running tasks and goals |
| Explicitly out of v1 | Email and calendar *send* actions, avatar/voice/video, consumer accounts |
| Must-have enterprise controls | SSO/SCIM + RBAC; audit and compliance; data controls; admin and policy |
| Model strategy | **Bring your own model (BYOM) first.** The tenant registers model endpoints it has already approved: hosted APIs, cloud-marketplace models, or self-hosted open-weight models. Keel certifies them and routes between them. Keel ships no model of its own. |

## Documents

| # | Doc | What it answers |
|---|---|---|
| 1 | [Scope and decisions](docs/01-scope-and-decisions.md) | Who it's for, what's in and out, the design principles every later choice is checked against |
| 2 | [Product requirements](docs/02-product-requirements.md) | Personas, core jobs, functional requirements with IDs, the enterprise feature set |
| 3 | [Architecture](docs/03-architecture.md) | Components, deployment models, agent runtime, connector framework, task engine, data flow |
| 4 | [Security and compliance](docs/04-security-and-compliance.md) | Identity model, policy engine, audit, data controls, threat model, framework mapping |
| 5 | [Roadmap and open questions](docs/05-roadmap-and-open-questions.md) | Phased delivery, exit criteria, and the decisions still to make |

## Relationship to the Claude Enterprise Control Baseline

Keel is model-agnostic (BYOM), so the tenant's model is whatever its model-risk team has already approved. Claude is one of the models Keel certifies at launch, which is where this repo connects. The [Claude Enterprise Control Baseline](../README.md) is the control set for *consuming* Claude in an enterprise. Keel reuses its L1/L2/L3 profile levels and its NIST SP 800-53 Rev 5 spine. Keel also sets out to close three gaps that baseline documents as unsolved (section 6 and 9.5 there): unattended autonomous execution, non-human agent identity, and centrally unreviewable configuration. Doc 4 traces each one.
