# 1. Scope and decisions

## 1.1 Problem

Personal AI agents moved from demo to mass market in September 2026. Meta's Muse topped the US app charts within weeks of launch and is already being extended to small businesses with Shopify, Dropbox, and Slack integrations. Employees at regulated firms will want the same thing at work: an agent that follows up on the thread, assembles the quarterly pack, chases the three approvals, and reports back.

Regulated firms cannot allow a consumer agent to do that, for four structural reasons, none of which is about model quality:

1. **Identity.** The agent acts as the user, with all of the user's access, and there is no separate credential to scope, rotate, or revoke.
2. **Attribution.** When something goes wrong, nobody can reconstruct which instruction, which data, and which tool call produced the action.
3. **Data boundary.** Prompts, retrieved documents, and memory leave the tenant, get retained on the vendor's terms, and may cross borders.
4. **Autonomy without a leash.** Long-running tasks run for hours with no human checkpoint and no enforceable limit on what they can touch.

Keel is designed around those four problems first and features second.

## 1.2 Target customers

| Segment | Examples | Dominant requirement |
|---|---|---|
| Financial services | Banks, broker-dealers, asset managers, insurers | Recordkeeping and supervision (SEC 17a-4, FINRA 3110/4511), model risk management (SR 11-7), DORA in the EU |
| Healthcare and life sciences | Payers, providers, pharma | HIPAA with BAA, 21 CFR Part 11 for GxP workflows |
| US public sector | Federal civilian, state and local, defense-adjacent | FedRAMP Moderate/High authorization, CJIS, ITAR data handling for some |

**Beachhead recommendation:** financial services first. The recordkeeping and supervision requirements are the most precise, so meeting them forces the audit design to be right. The buyers also have budget and an existing habit of buying supervised communication tools. Healthcare second. Public sector is gated on a FedRAMP authorization and is a year-two motion (see doc 5).

## 1.3 In scope for v1

- **Work-app connectors:** read and act in Microsoft 365 (SharePoint, OneDrive, Teams), Google Workspace (Drive, Chat), Slack, Jira, Confluence, ServiceNow, Salesforce, Box.
- **Long-running tasks and goals:** a user states a goal, and Keel plans it, runs steps over hours or days, pauses at checkpoints for approval, and reports progress.
- **Enterprise control plane:** SSO/SCIM, RBAC, policy, audit, retention, and DLP. The admin console and APIs.

## 1.4 Out of scope for v1 (and why)

| Excluded | Reason | Revisit |
|---|---|---|
| Sending email or calendar invites on the user's behalf | Outbound email is the highest-risk exfiltration and impersonation channel, and FINRA-supervised firms must capture it anyway. Read access and *drafting* are in v1. Sending is not. | v2, behind per-tenant policy and supervision capture |
| Avatar, voice, video | No regulated buyer is asking for it, and it adds biometric data obligations such as BIPA | Not planned |
| Consumer or BYO accounts | Every identity must come from the tenant IdP | Not planned |
| Open plugin marketplace | Supply-chain risk. v1 ships a curated connector set and a private-connector SDK only. | v2: a tenant-curated private catalog |
| Browser or computer-use automation | Largest prompt-injection surface, and its actions are the hardest to audit | v2 at the earliest, L1 profile only |

## 1.5 Design principles

Every later decision is checked against these principles. Where two conflict, the earlier one wins.

1. **The agent is a principal, not a puppet.** Each agent instance has its own workload identity and delegated, scoped, time-boxed credentials. It never holds the user's primary token.
2. **Deny by default and allow by policy.** Every tool call passes through a policy decision point before it executes. No connector action is reachable unless policy grants it.
3. **Every action is attributable.** The audit record ties each side effect to the user, the goal, the plan step, the model input that proposed it, and the policy decision that allowed it.
4. **The tenant owns the data plane.** Customer content, memory, and logs live in the customer's cloud account or in a dedicated single-tenant deployment. The model provider is a stateless processor.
5. **Autonomy is a budget, not a mode.** Long-running tasks carry explicit limits: time, spend, number of actions, which systems are reachable, and which actions need a human.
6. **Configuration is inspectable.** Every instruction that shapes agent behavior is stored centrally, versioned, and reviewable by security, including user-level instructions and memory.
7. **Reads are cheap and writes are ceremonies.** Read-only work flows freely. Writes cost more the more they matter: an approval, a two-person rule, or a hard block.

## 1.6 Key architectural bets

| Decision | Choice | Alternative rejected |
|---|---|---|
| Model provider | Claude, reached through the customer's chosen channel (Anthropic API, Claude Platform on AWS, Amazon Bedrock, Google Vertex AI, Microsoft Foundry) | Multi-vendor abstraction on day one. It doubles eval and safety work, and we can add it later behind the model gateway. |
| Agent harness | Self-hosted harness in the Keel data plane | Anthropic Managed Agents. It is the simplest path on the first-party API, but it isn't offered on Bedrock, Vertex, or Foundry, where most regulated buyers consume Claude. It also puts the loop and sandbox outside the customer boundary. We keep it as an optional runtime for tenants on the first-party API or Claude Platform on AWS. |
| Deployment | Customer-VPC data plane with a Keel-hosted control plane, plus a fully dedicated option | Multi-tenant SaaS only. It fails most FS and public-sector security reviews. |
| Connector protocol | MCP servers run inside the data plane behind the policy gateway | Direct vendor SDK calls. They are harder to govern uniformly. |
