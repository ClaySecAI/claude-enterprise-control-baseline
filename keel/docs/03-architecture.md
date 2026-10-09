# 3. Architecture

## 3.1 System overview

Keel splits into a **control plane**, which Keel operates and which holds no customer content, and a **data plane**, which runs in the customer's cloud account or in a dedicated single-tenant environment and holds everything sensitive.

```
                         ┌────────────────────── CONTROL PLANE (Keel-operated) ─────────────────────┐
                         │  Tenant registry · Policy authoring · Connector catalog · Release mgmt   │
                         │  Admin console · Admin API · Licensing/metering (counts only, no content)│
                         └───────────────▲──────────────────────────────────────────────────────────┘
                                         │ signed config + policy bundles (pull, mTLS)
┌──────────────────────────────────── DATA PLANE (customer cloud / segmented hosted) ─────────────────────────────┐
│                                                                                                                 │
│  Surfaces            ┌────────────┐                                                                             │
│  Web · Teams · Slack │  API edge  │──── IdP (SAML/OIDC) ─── SCIM                                               │
│  ───────────────────▶│  + AuthN   │                                                                             │
│                      └─────┬──────┘                                                                             │
│                            ▼                                                                                    │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐   ┌───────────────────────────┐   │
│  │ Task service │◀─▶│ Agent runtime│──▶│ Policy       │──▶│ Tool gateway    │──▶│ Connectors (MCP servers)   │──┼─▶ SaaS / on-prem
│  │ (durable     │   │ (harness,    │   │ decision pt  │   │ (credential     │   │ M365, Slack, Jira, SFDC... │   │    systems
│  │  workflows)  │   │  planner)    │◀──│ (PDP)        │◀──│  broker, DLP,   │   └───────────────────────────┘   │
│  └──────┬───────┘   └──────┬───────┘   └──────────────┘   │  rate limits)   │                                   │
│         │                  │                              └────────┬────────┘                                   │
│         │                  ▼                                       │                                            │
│         │           ┌──────────────┐                               │                                            │
│         │           │ Model gateway│──── Tenant's registered models (BYOM): hosted APIs · Bedrock · Azure AI    │
│         │           │ (routing,    │     Foundry · Vertex AI · self-hosted vLLM/TGI. PrivateLink where offered  │
│         │           │  redaction,  │                                                                            │
│         │           │  metering)   │                                                                            │
│         │           └──────────────┘                                                                            │
│         ▼                                                                                                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                                      │
│  │ Approvals    │   │ Memory store │   │ Audit ledger │──▶│ SIEM / WORM  │                                      │
│  │ service      │   │ (per-user,   │   │ (append-only,│   │ archive      │                                      │
│  └──────────────┘   │  inspectable)│   │  hash-chained│   └──────────────┘                                      │
│                     └──────────────┘   └──────────────┘                                                         │
│                                   All at-rest data encrypted with customer-managed keys                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Deployment models

| Model | Control plane | Data plane | Who it's for |
|---|---|---|---|
| **Customer cloud** | Keel-hosted | The customer's own AWS or Azure account (GCP later), deployed with Terraform + Helm and operated by Keel through a narrow break-glass role. **On AWS the models come from Amazon Bedrock, on Azure from Microsoft Foundry**, reached over private endpoints, so content never leaves the customer's cloud boundary. Self-hosted models are also supported. | Large FS and healthcare; anyone whose security review requires data to stay in their own account |
| **Keel-hosted, segmented** | Keel-hosted | Keel-hosted, but **one isolated environment per customer**: its own cloud account or subscription, its own network, database, object storage, encryption keys, and model endpoints. Nothing is shared with other customers except the control plane, which holds no content. | Mid-size FS and healthcare that want no infrastructure to run |
| **Sovereign / air-gapped** | Customer-hosted | Customer-hosted, running on self-hosted open-weight models or a model in an authorized government cloud region. BYOM is what makes this deployment possible. | Public sector, defense-adjacent (year two, see doc 5) |

#### Environment factory (hosted option)

The hosted option depends on spinning up a fresh, segmented environment for each customer quickly and repeatably. Keel provisions it from the same Terraform and Helm code used for the customer-cloud option, so there is one deployment artifact rather than two products.

- **One account or subscription per customer.** Not a namespace or a database schema in a shared cluster. The blast radius of any single compromise is one customer.
- **Per-customer keys.** Each environment has its own encryption keys, held in a key store the customer can control (BYOK/HYOK, ENT-12). Revoking the key makes that environment unreadable.
- **No shared data stores, queues, or model endpoints.** The only cross-customer systems are the control plane and the build pipeline, and neither handles content.
- **Operator access is narrow and recorded.** Keel staff use a break-glass role that is time-limited, requires a ticket and a second approver, and is written to the customer's own audit ledger and SIEM feed.
- **Promotion path.** A customer can move from the hosted option to their own cloud account with the same configuration, because the environment is defined as code.

Note on the security bar: the request was for a security profile "similar to Muse". I have not verified Muse's actual hosting or isolation model, so this spec sets its own bar (a separate account per customer with customer-held keys) rather than copying a claim about Muse.

The control plane never receives prompts, documents, model outputs, or memory. It sends signed policy and config bundles down, and receives only metering counts and health telemetry back. We will publish the full list of telemetry fields, and each tenant can turn it off.

## 3.3 Components

### API edge and identity
- Terminates TLS and authenticates users via the tenant IdP (OIDC/SAML). It honors IdP session lifetime and conditional-access claims.
- SCIM endpoint maintains users and groups. A deprovision event fans out to the credential broker (revoke), the task service (halt), and the audit ledger (record).

### Task service (durable workflow engine)
- Every task is a durable workflow: plan → steps → waits → checkpoints → report. The workflow engine is Temporal or an equivalent. The key property is deterministic replay, so a task survives restarts without re-calling the model for steps that already finished.
- Waits (for approvals, replies, or schedules) hold no model session and cost no tokens (AGT-04).
- Holds the autonomy budget ledger for each task and enforces it independently of the agent runtime (AGT-07). The model cannot talk its way past a budget, because the budget is not in the model's control path.
- Scheduled and triggered tasks are workflows with an owner, an expiry, and a re-attestation reminder (AGT-05). This closes the "scheduled tasks have no technical control" gap in the Control Baseline (section 6.3).

### Agent runtime (harness)
- Keel's own agent loop, which is **provider-neutral**. It talks to models only through the model gateway's internal interface: messages, tool definitions, tool calls and results, structured output against a JSON schema, and streaming. The loop never imports a vendor SDK.
- **Planner/executor split.** One call produces a structured plan against a strict schema, which is validated before execution. Each step then runs with only the tools that step needs, which shrinks the injection blast radius per step. This split also suits BYOM: a strong model can plan while cheaper or self-hosted models execute narrow steps.
- **Schema-first tool calling.** Tool calls are validated against the tool's JSON schema in Keel, not trusted from the provider. A malformed call is returned to the model as an error and never executed. Models without native tool calling can still run executor steps through constrained structured output, but only up to the tier that allows it.
- **Context hygiene.** Retrieved content is wrapped and labeled as untrusted data, and operator instructions go through the system channel only. Keel owns context management (summarizing and trimming history) rather than relying on a provider feature, so long tasks behave the same on every model.
- **Per-model prompt profiles.** Each certified model gets a versioned prompt profile: system prompt variant, tool-description style, and reasoning or effort settings. Profiles are part of what certification tests, so changing one triggers recertification.

### Model gateway
The gateway is the core of BYOM.

- **Adapters.** One adapter per provider family: Anthropic API, OpenAI API, Google Gemini API, Amazon Bedrock, Azure AI Foundry / Azure OpenAI, Google Vertex AI, and a generic OpenAI-compatible adapter for self-hosted vLLM and TGI. Each adapter maps the internal interface to the provider's wire format, including tool-call format, stop and refusal reasons, and usage counting. Adapters are the only provider-specific code in Keel.
- **Model registry.** Holds each registered model's endpoint, region, credentials reference (stored in the tenant's secret manager, never in Keel), exact version, context window, approved data classifications, certification results, and tier (MOD-01, MOD-07).
- **Routing.** Chooses a model per step from the tenant's step-type map (MOD-03). The router enforces data-classification routing *before* anything is sent (MOD-04), then falls back down the ordered list on errors, refusals, or rate limits. A fallback model must hold a tier at least as high as the step requires, and a fallback can never route content to a model that isn't approved for its classification.
- **Version pinning and drift detection.** Where the provider exposes a version, it is pinned. Where it doesn't, the gateway fingerprints behavior with a small canary set. Either way, a detected change pauses that model and queues recertification (MOD-05).
- **Private connectivity.** PrivateLink or Private Service Connect wherever the provider offers it. Self-hosted endpoints stay inside the VPC.
- **DLP and metering.** Pre-send DLP and redaction (ENT-10), and a post-receive check for refusals, truncation, and injected tool-call patterns. Tokens and cost are metered per task, user, group, *and model* (ENT-13).
- **Residency.** Each registered model carries its region, and the router will not send content to a model outside the tenant's residency boundary (ENT-11).

#### Capability tiers

Certification assigns each model a tier. Tiers decide which jobs a model may run, not whether the system is safe; safety is enforced outside the model (principle 8).

| Tier | May run | Minimum certification bar |
|---|---|---|
| **T1: Planner** | Planning, multi-step long-running tasks, judgment steps (triage, drafting that goes to people) | Passes the full capability suite, the full injection suite, and reliable schema-valid tool calling across long contexts |
| **T2: Executor** | Single executor steps with a narrow tool set; drafting; bulk writes after approval | Reliable tool calling on short contexts; injection suite pass rate above the tenant's threshold |
| **T3: Utility** | Extraction, classification, summarization, redaction. No tools. | Accuracy on extraction and summary sets. Structured output only. |

At launch, the reference model list (MOD-08) will cover at least two T1 models from different vendors and at least one self-hosted open-weight model at T2 or better, so an air-gapped tenant is never left without a working configuration. Which specific models land in which tier is a phase-0 output, not a spec decision.

### Policy decision point (PDP)
- Evaluates every proposed tool call *before* execution. Inputs: the principal (user + agent instance), the action and its class, the target resource, the data classification of the payload, the task's remaining budget, and time.
- Outputs: `allow`, `deny`, `require_approval(approver_rule)`, or `allow_with_redaction`.
- The policy language is Cedar or OPA/Rego (decision in doc 5). Policies are authored in the control plane, signed, and distributed as bundles, then evaluated locally in the data plane with no network hop to the control plane.

### Tool gateway and credential broker
- The only path from the agent to any connector. It enforces the PDP decision, rate limits, and the payload DLP check.
- **Credential broker.** The agent never holds a long-lived token. For each approved call, the broker mints or exchanges a short-lived, down-scoped credential: OAuth token exchange (RFC 8693) with the user as subject and the agent instance as actor, where the target system supports it, and otherwise a scoped service credential with the user identity asserted. Credentials are bound to the task ID and expire within minutes.
- Writes the audit record *before* dispatching the call, then updates it with the outcome (NFR-04).

### Connectors
- Each connector is an MCP server that runs inside the data plane, and each ships with a **manifest**:
  ```yaml
  connector: salesforce
  version: 1.4.0
  actions:
    - name: query_records        class: read          data: [customer_pii, financial]
    - name: update_record        class: write         data: [customer_pii, financial]
    - name: delete_record        class: destructive
    - name: share_report_external class: external-share
  scopes: [api, refresh_token]
  honors_source_acl: true
  ```
- Keel reviews and signs first-party connectors. Private connectors are signed by the tenant's own key, and the tool gateway refuses unsigned connectors.
- A connector only executes actions. Every policy and permission decision is made by the gateway and PDP.

### Approvals service
- Renders an approval card showing the exact diff or payload, the reason, the plan step, and the sources. Cards appear in Teams, Slack, and the web app.
- Supports single-approver, two-person, and role-based approver rules, with an expiry after which the step is cancelled.
- The approver's decision is signed and written to the audit ledger with a hash of the payload the approver saw. The executed payload must match that hash, or the action is refused.

### Memory store
- Per-user and per-task memory lives in the data plane under customer-managed keys.
- Each memory item carries provenance: which task created it and from what source. Users can view, edit, and delete memory items, and admins can see them under policy (ENT-15). Memory follows retention policy like any other record.
- Memory writes that originate from untrusted content, such as a retrieved document, are quarantined until confirmed. Otherwise an injected instruction could persist across tasks.

### Audit ledger
- Append-only and hash-chained per tenant, with periodic anchoring to WORM storage (ENT-09).
- Streams to the SIEM in near real time (ENT-07). Schema is in doc 4.

## 3.4 Data flow: one write action, end to end

1. The user asks: "Update the renewal date on the Acme opportunity to 2027-03-31 and tell the account team."
2. The agent runtime asks the tenant's T1 planner model (via the model gateway) to produce a plan with two steps: `salesforce.update_record` (write) and `slack.post_message` (write).
3. The plan is validated against its schema and shown to the user (AGT-02). The user confirms.
4. For step 1, the runtime proposes a tool call. The tool gateway asks the PDP, which answers `require_approval(role=account_owner)` because the record is tagged `customer_financial`.
5. The approvals service sends a card to the account owner, and the task service puts the task into a zero-token wait.
6. The owner approves. The signed decision and payload hash are written to the audit ledger.
7. The gateway checks the payload hash, and the credential broker mints a 5-minute Salesforce token bound to this task. A pre-dispatch audit record is written, the call executes, and the outcome is appended.
8. Step 2 goes through the same flow, and the PDP allows it without approval.
9. The task writes its final report (AGT-08). The full chain is in the SIEM.

## 3.5 Tech choices to confirm

| Area | Leading option | Decide by |
|---|---|---|
| Workflow engine | Temporal | Phase 0 spike |
| Policy language | Cedar (analyzable, readable by non-engineers) vs. OPA/Rego (existing enterprise familiarity) | Phase 0 |
| Harness | Build Keel's own loop (recommended) vs. adopt a provider-neutral open-source agent framework | Phase 0 spike |
| Model gateway | Build on a thin in-house adapter layer vs. adopt an open-source LLM gateway (LiteLLM-class) and extend it with registry, classification routing, and certification hooks | Phase 0 spike |
| Self-hosted serving | vLLM (leading) vs. TGI as the reference stack for self-hosted models | Phase 0 |
| Primary datastore | PostgreSQL (tasks, policy, metadata) + object storage (artifacts, archives) | Phase 0 |
| Memory retrieval | pgvector in the same PostgreSQL, to avoid a new data store in the boundary | Phase 1 |
| Deploy tooling | Terraform + Helm on EKS / AKS / GKE | Phase 0 |
