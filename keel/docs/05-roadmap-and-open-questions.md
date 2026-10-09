# 5. Roadmap and open questions

## 5.1 Phases

| Phase | Duration | Scope | Exit criteria |
|---|---|---|---|
| **0: Foundations spike** | 8–10 weeks | Provider-neutral harness and model gateway with at least three adapters (two hosted vendors and one self-hosted vLLM); first cut of the certification suite and capability tiers; Temporal task skeleton; PDP with Cedar vs. Rego bake-off; credential broker with token exchange against M365 and Salesforce; audit ledger write-ahead; first injection eval corpus | One end-to-end write action, as in doc 3 section 3.4, runs in a test environment shaped like a customer-cloud deployment with a complete audit chain, **on at least two models from different vendors with no code change**. The injection suite runs in CI against every model on the draft reference list. |
| **1: Private design-partner alpha** | 3 months | 3–4 design partners (2 FS, 1–2 healthcare). Connectors: M365, Slack, Jira, Salesforce. Core jobs 1 and 4. SSO/SCIM, built-in roles, L2 policy profile, SIEM streaming. Model registry, tenant certification, and classification routing. Each partner runs on its own already-approved model. | Partners run it on real work with 50+ users each. No P0 security findings from partner pen tests. |
| **2: v1 GA** | 4–5 months | All v1 connectors, core jobs 2 and 3 (long-running and standing tasks), approvals in Teams and Slack, memory, retention and eDiscovery, WORM archive, both deployment options (customer cloud on Bedrock or Foundry, and the segmented Keel-hosted environment factory), admin API | SOC 2 Type I, HIPAA BAA available, 17a-4 attestation letter, published NIST 800-53 mapping, a published reference model list with at least one self-hosted model, and every P0 requirement in doc 2 met |
| **3: v1.x** | Ongoing | Private connector SDK GA, EU region and DORA, email send behind supervision, L3 profile, cost analytics | By customer demand |
| **4: Public sector** | Year two | Sovereign deployment, FedRAMP Moderate then High | Agency sponsor secured, 3PAO engaged |

## 5.2 Team shape (to reach v1 GA)

About 16–20 engineers:

- Agent runtime and evals: 4
- Model gateway and certification: 2
- Platform, workflow, and data plane: 4
- Identity, policy, and security: 3
- Connectors: 3
- Web, Teams, and Slack surfaces: 2
- SRE and deploy: 2

Plus one security and compliance lead from day one, a PM, and a designer. Compliance is not a post-GA workstream in this market.

## 5.3 Open questions

Rows marked **Decided** were settled with the project owner and are no longer open. The rest still have a recommendation to react to.

| # | Question | Options | Recommendation |
|---|---|---|---|
| Q1 | **Name.** Keep "Keel"? | Keel / other | Run a trademark search before any external use. Avoid any name that evokes Muse or Meta. |
| Q2 | **Beachhead vertical.** FS or healthcare first? | FS / healthcare / both | **Decided: financial services first**, and the owner wants to explore aligning Keel with Drydock (drydock.build), especially its Pathspan product. See Q13. |
| Q3 | **Default deployment model** | Dedicated SaaS / customer VPC | **Decided: offer both.** (1) Run in the customer's own cloud, using Amazon Bedrock on AWS or Microsoft Foundry on Azure for models. (2) A hosted option where Keel spins up a separate, isolated environment per customer. Detail in doc 03, section 3.2. |
| Q4 | **Which adapters ship first** | All major providers at once / the ones design partners use | Build to design partners' approved models. Expect Bedrock and Azure to dominate in FS, plus one self-hosted open-weight model for healthcare and the public sector. |
| Q5 | **Business model** | Per seat / per task / platform + usage | Platform fee plus per-seat, with model usage passed through or billed on the customer's own cloud commitment |
| Q6 | **Email send in v1?** | Yes behind policy / no | No. Revisit in v1.x with supervision capture. |
| Q7 | **Mobile surface** | Native app / Teams and Slack mobile only | Teams and Slack mobile only for v1. Approvals are the main mobile need, and both clients already handle them. |
| Q8 | **Build vs. buy for DLP and classification** | Build / integrate Purview and existing DLP | Integrate. Customers already have a DLP engine and won't accept a second source of truth. |
| Q9 | **Minimum model bar.** Should Keel refuse to run long-running tasks on a tenant's model that fails T1? | Refuse / allow with warning | **Decided: refuse.** Long-running autonomous tasks on a model that can't plan reliably will produce the failures customers blame on Keel. The tenant can still use that model for T2/T3 steps. |
| Q10 | **Should Keel also offer a bundled default model** for tenants that don't have one approved? | BYOM only / BYOM + optional managed default | **Decided: no bundled default.** The reference model list is the easy path. |
| Q11 | **Who pays for certification compute** (eval runs use the tenant's model and tokens) | Tenant / Keel credits | **Decided: the customer pays** to run certification on their models, with the cost estimated and shown before the run (MOD-09). |
| Q12 | **Where does this spec live long-term?** | This folder / new repo | **Decided: GitHub, and ideally its own private repo.** Everything built stays in GitHub. Repo creation from the session was refused (403), so until a repo is attached the work lives in `keel/` on branch `claude/enterprise-muse-framework-rfxo53`. |
| Q13 | **Drydock / Pathspan alignment.** How should Keel relate to Drydock (drydock.build) and its Pathspan product? | Design partner / shared product direction / vertical focus / unrelated | **Open, needs information.** I could not read drydock.build (blocked in this environment) or find public information on either name, so nothing in this spec assumes anything about them. To decide, we need: what Pathspan does, who its customers are, and what the owner and their friend want from the alignment. |

## 5.4 Risks to the plan

- **Platform risk.** Meta, Microsoft (Copilot), Google, and Anthropic's own enterprise products may move into governed agents. Keel's defensibility is the identity, policy, and audit layer and its regulated-vertical depth, not the agent loop.
- **Connector breadth.** Buyers compare on connector count. Stay narrow and deep for v1, and let the private connector SDK carry the long tail.
- **Injection.** A single public incident at a regulated customer would be existential. The eval gate and the "bounded by plan and policy" design are the product, not overhead.
- **Model churn times model count.** Every provider ships new models and API changes several times a year, and BYOM multiplies that by the number of providers supported. Adapter maintenance and recertification are a permanent cost, which is why the gateway and certification team is on the plan from day one. Tenant-pinned versions plus the eval gate turn each upgrade into a scheduled change, not an incident.
- **Lowest-common-denominator drag.** A provider-neutral harness can't lean on any one vendor's advanced agent features. Mitigation: the internal interface supports optional capabilities (such as server-side caching, extended reasoning, and larger context) that adapters light up where available, without making the core loop depend on them.
- **Blame for weak models.** Tenants that pick a weak model will judge Keel by it. Capability tiers, the reference model list, and visible per-model analytics keep that attribution honest.
