# 3. Architecture

## 3.1 System overview

Keel splits into a **control plane**, which Keel operates and which holds no customer content, and a **data plane**, which runs in the customer's cloud account or in a dedicated single-tenant environment and holds everything sensitive.

```
                         ┌────────────────────── CONTROL PLANE (Keel-operated) ─────────────────────┐
                         │  Tenant registry · Policy authoring · Connector catalog · Release mgmt   │
                         │  Admin console · Admin API · Licensing/metering (counts only, no content)│
                         └───────────────▲──────────────────────────────────────────────────────────┘
                                         │ signed config + policy bundles (pull, mTLS)
┌──────────────────────────────────── DATA PLANE (customer VPC / dedicated) ──────────────────────────────────────┐
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
│         │           │ Model gateway│──── Claude via tenant's channel (Anthropic API / Claude Platform on AWS /   │
│         │           │ (routing,    │     Bedrock / Vertex / Foundry), PrivateLink where available              │
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
| **Dedicated SaaS** | Keel-hosted | Keel-hosted, single-tenant, in the customer's chosen region, with customer-managed keys | Mid-size FS and healthcare that want no infrastructure burden |
| **Customer VPC (default for regulated)** | Keel-hosted | Customer's AWS, Azure, or GCP account, deployed via Terraform + Helm, and operated by Keel through a narrow break-glass role | Large FS and healthcare |
| **Sovereign / air-gapped** | Customer-hosted | Customer-hosted, with Claude via Bedrock in AWS GovCloud or the equivalent authorized channel | Public sector, defense-adjacent (year two, see doc 5) |

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
- A self-hosted agent loop that calls Claude through the model gateway using the Messages API with tool use. Two viable implementations:
  - the Anthropic SDK's Tool Runner, whose per-turn hooks give us the approval gate, audit write, and error interception points;
  - the Claude Agent SDK, if we want its built-in context management and subagents.
  Pick one after the phase-0 spike (doc 5).
- **Planner/executor split.** One call produces a structured plan with a strict schema that is validated before execution. Each step then runs with only the tools that step needs, which shrinks the injection blast radius per step.
- **Context hygiene.** Retrieved content is wrapped and labeled as untrusted data. Operator instructions arrive through the system channel only. Server-side compaction keeps long tasks inside the context window.
- **Model selection.** Default is Claude Opus 5.5 for planning and judgment-heavy steps. Claude Sonnet 5.5 or Claude Haiku 4.5 handle high-volume extraction and summarization sub-steps. Effort is tuned per step type. Every choice is pinned per tenant and changes only through the eval gate (NFR-07).
- **Optional managed runtime.** Tenants that consume Claude through the first-party API or Claude Platform on AWS can instead run steps on Anthropic Managed Agents. It still sits behind the same policy and tool gateway: custom tools route back into our data plane, so the PDP and audit remain authoritative. It is not the default, because it is unavailable on Bedrock, Vertex, and Foundry.

### Model gateway
- Routes to the tenant's configured Claude channel, over a private endpoint where the provider offers one.
- Pins model IDs per tenant. There are no silent upgrades.
- Pre-send DLP and redaction pass (ENT-10). Post-receive checks cover refusal and stop reasons and look for injected tool-call patterns.
- Meters tokens and cost per task, user, and group (ENT-13), and enforces spend caps.
- Handles the provider's data-residency controls: inference geography where supported, and otherwise regional endpoint selection (ENT-11).

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
2. The agent runtime calls Claude (via the model gateway) to produce a plan with two steps: `salesforce.update_record` (write) and `slack.post_message` (write).
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
| Harness | Anthropic SDK Tool Runner vs. Claude Agent SDK | Phase 0 spike |
| Primary datastore | PostgreSQL (tasks, policy, metadata) + object storage (artifacts, archives) | Phase 0 |
| Memory retrieval | pgvector in the same PostgreSQL, to avoid a new data store in the boundary | Phase 1 |
| Deploy tooling | Terraform + Helm on EKS / AKS / GKE | Phase 0 |
