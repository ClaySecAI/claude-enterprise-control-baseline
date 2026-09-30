# 1. Scope and decisions

## 1.1 Problem

Personal AI agents moved from demo to mass market in September 2026. Meta's Muse topped the US app charts within weeks of launch and is already being extended to small businesses with Shopify, Dropbox, and Slack integrations. Employees at regulated firms will want the same thing at work: an agent that follows up on the thread, assembles the quarterly pack, chases the three approvals, and reports back.

Regulated firms cannot allow a consumer agent to do that, for four structural reasons, none of which is about model quality:

1. **Identity.** The agent acts as the user, with all of the user's access, and there is no separate credential to scope, rotate, or revoke.
2. **Attribution.** When something goes wrong, nobody can reconstruct which instruction, which data, and which tool call produced the action.
3. **Data boundary.** Prompts, retrieved documents, and memory leave the tenant, get retained on the vendor's terms, and may cross borders.
4. **Autonomy without a leash.** Long-running tasks run for hours with no human checkpoint and no enforceable limit on what they can touch.
5. **Model lock-in.** A consumer agent comes with its vendor's model. Regulated firms already run a model-risk approval process (SR 11-7 in US banking) and have a short list of approved models, often behind their own cloud contracts. An agent that forces a new, unapproved model into that list adds 6–12 months of model validation before anyone can use it.

Keel is designed around those five problems first and features second.

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
8. **Safety must not depend on the model.** Because tenants bring their own models, no control may rely on a particular model being well-behaved or injection-resistant. Identity, policy, plan scope, approvals, budgets, and audit are all enforced outside the model's control path, so a weak or compromised model can only fail *closed*. Model quality decides how *useful* Keel is, never how *safe* it is.

## 1.6 Key architectural bets

| Decision | Choice | Alternative rejected |
|---|---|---|
| Model provider | **Bring your own model.** Tenants register endpoints they have already approved: hosted APIs (Anthropic, OpenAI, Google, and others), cloud-marketplace models (Amazon Bedrock, Azure AI Foundry, Google Vertex AI), or self-hosted open-weight models (vLLM or TGI in their VPC). Keel runs a certification suite on each one and assigns it a capability tier that decides which jobs it may run. | A single bundled model. It is simpler to evaluate, but it fails the model-risk process at most regulated buyers and it rules out air-gapped deployments. |
| Agent harness | Keel's own provider-neutral agent loop in the data plane, calling models through one internal interface (messages, tools, structured output, streaming) with a thin adapter per provider | Any vendor's agent SDK or hosted agent service. Each one ties the loop, its tool-call format, and often its sandbox to a single vendor, which defeats BYOM and puts the loop outside the customer boundary. |
| Deployment | Customer-VPC data plane with a Keel-hosted control plane, plus a fully dedicated option | Multi-tenant SaaS only. It fails most FS and public-sector security reviews. |
| Connector protocol | MCP servers run inside the data plane behind the policy gateway. MCP is model-neutral, so a connector works with every certified model. | Direct vendor SDK calls, or a model vendor's own tool format. Both are harder to govern uniformly, and the second ties connectors to one model. |
