# 5. Roadmap and open questions

## 5.1 Phases

| Phase | Duration | Scope | Exit criteria |
|---|---|---|---|
| **0: Foundations spike** | 6–8 weeks | Harness choice (Tool Runner vs. Agent SDK); Temporal task skeleton; PDP with Cedar vs. Rego bake-off; credential broker with token exchange against M365 and Salesforce; audit ledger write-ahead; first injection eval corpus | One end-to-end write action, as in doc 3 section 3.4, runs in a customer-VPC-shaped test environment with a complete audit chain. The injection suite runs in CI. |
| **1: Private design-partner alpha** | 3 months | 3–4 design partners (2 FS, 1–2 healthcare). Connectors: M365, Slack, Jira, Salesforce. Core jobs 1 and 4. SSO/SCIM, built-in roles, L2 policy profile, SIEM streaming. | Partners run it on real work with 50+ users each. No P0 security findings from partner pen tests. |
| **2: v1 GA** | 4–5 months | All v1 connectors, core jobs 2 and 3 (long-running and standing tasks), approvals in Teams and Slack, memory, retention and eDiscovery, WORM archive, customer-VPC deploy, admin API | SOC 2 Type I, HIPAA BAA available, 17a-4 attestation letter, published NIST 800-53 mapping, and every P0 requirement in doc 2 met |
| **3: v1.x** | Ongoing | Private connector SDK GA, EU region and DORA, email send behind supervision, L3 profile, cost analytics | By customer demand |
| **4: Public sector** | Year two | Sovereign deployment, FedRAMP Moderate then High | Agency sponsor secured, 3PAO engaged |

## 5.2 Team shape (to reach v1 GA)

About 14–18 engineers:

- Agent runtime and evals: 4
- Platform, workflow, and data plane: 4
- Identity, policy, and security: 3
- Connectors: 3
- Web, Teams, and Slack surfaces: 2
- SRE and deploy: 2

Plus one security and compliance lead from day one, a PM, and a designer. Compliance is not a post-GA workstream in this market.

## 5.3 Open questions

These are the decisions still to make. Each has a recommendation to react to.

| # | Question | Options | Recommendation |
|---|---|---|---|
| Q1 | **Name.** Keep "Keel"? | Keel / other | Run a trademark search before any external use. Avoid any name that evokes Muse or Meta. |
| Q2 | **Beachhead vertical.** FS or healthcare first? | FS / healthcare / both | FS. Its requirements are more precise, it has buyers used to buying supervision tooling, and 17a-4 forces the audit design to be right. |
| Q3 | **Default deployment model** | Dedicated SaaS / customer VPC | Customer VPC for the first design partners, because it is the harder one to retrofit. Add dedicated SaaS at GA. |
| Q4 | **Claude channel** for design partners | Anthropic API / Claude Platform on AWS / Bedrock / Vertex / Foundry | Support whichever the partner already has approved. The model gateway abstracts it. Expect Bedrock to dominate in FS. |
| Q5 | **Business model** | Per seat / per task / platform + usage | Platform fee plus per-seat, with model usage passed through or billed on the customer's own cloud commitment |
| Q6 | **Email send in v1?** | Yes behind policy / no | No. Revisit in v1.x with supervision capture. |
| Q7 | **Mobile surface** | Native app / Teams and Slack mobile only | Teams and Slack mobile only for v1. Approvals are the main mobile need, and both clients already handle them. |
| Q8 | **Build vs. buy for DLP and classification** | Build / integrate Purview and existing DLP | Integrate. Customers already have a DLP engine and won't accept a second source of truth. |
| Q9 | **How far to go on multi-model** | Claude-only / pluggable later | Claude-only in v1, behind a gateway that could route elsewhere later if a customer mandates it |
| Q10 | **Where does this spec live long-term?** | This folder / new repo | New private repo once it can be created (see the top-level note) |

## 5.4 Risks to the plan

- **Platform risk.** Meta, Microsoft (Copilot), Google, and Anthropic's own enterprise products may move into governed agents. Keel's defensibility is the identity, policy, and audit layer and its regulated-vertical depth, not the agent loop.
- **Connector breadth.** Buyers compare on connector count. Stay narrow and deep for v1, and let the private connector SDK carry the long tail.
- **Injection.** A single public incident at a regulated customer would be existential. The eval gate and the "bounded by plan and policy" design are the product, not overhead.
- **Model churn.** Claude models and their API behavior change several times a year. Tenant-pinned models plus the eval gate turn each upgrade into a scheduled change, not an incident.
