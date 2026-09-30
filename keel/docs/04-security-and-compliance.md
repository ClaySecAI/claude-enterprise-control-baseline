# 4. Security and compliance

## 4.1 Identity model

Keel has three kinds of principal:

| Principal | Source | Holds credentials? |
|---|---|---|
| **User** | Tenant IdP via SSO, lifecycle via SCIM | Only an IdP session. Keel never stores user passwords or primary refresh tokens for connected systems beyond what the credential broker needs to perform token exchange. |
| **Agent instance** | Minted by Keel per task. Workload identity (SPIFFE ID or cloud workload identity) with `sub=agent:{task_id}` and `act_for=user:{user_id}` | No standing credentials. It receives short-lived, down-scoped tokens per approved call from the credential broker. |
| **Standing task** | A named service principal owned by a user, with an expiry | Same as agent instance. Owner deprovisioning or expiry halts the task. |

This directly addresses the "non-human agent identity" gap in the Claude Enterprise Control Baseline (section 9.5). Agents do not inherit the user's permissions wholesale. They get the intersection of three things: what the user can do, what the policy allows for this action class, and what the task's plan declared it needs.

## 4.2 Authorization layers

A tool call executes only if **every** layer allows it:

1. **Source-system ACL.** The target system's own permissions for the user (CON-04).
2. **Connector enablement.** An admin has enabled the connector and this action for the user's group (CON-06).
3. **Plan scope.** The action and system were declared in the approved plan. Anything off-plan triggers a re-plan and new user confirmation.
4. **Policy decision.** The PDP rule over principal, action class, data classification, and budget (ENT-04).
5. **Approval.** Required where policy says so, bound to the exact payload hash (ENT-05).
6. **Budget.** The task's autonomy budget has room (AGT-07).

### Default policy profiles

These reuse the Control Baseline's L1–L3 levels.

| Action class | L1 (minimum) | L2 (default for regulated) | L3 (high-assurance) |
|---|---|---|---|
| read | allow | allow | allow; sensitive-labeled data requires the user to have the label clearance |
| write | allow | allow with user confirmation of plan | approval by the user per action |
| destructive | require approval | require approval by a second person | deny |
| external-share | require approval | deny unless an allowlisted domain and approval are both present | deny |
| standing tasks | max 90-day expiry | max 30-day expiry, read-only unless approved | deny by default |
| memory | on | on, with untrusted-origin quarantine | off, or per-task only |

## 4.3 Audit

### Event schema (core fields)

| Field | Notes |
|---|---|
| `event_id`, `prev_hash`, `hash` | Hash chain per tenant |
| `ts`, `tenant_id`, `region` | |
| `user_id`, `agent_id`, `task_id`, `step_id` | Full attribution chain |
| `event_type` | `task.created`, `plan.proposed`, `plan.approved`, `model.request`, `model.response`, `tool.proposed`, `policy.decision`, `approval.requested`, `approval.decided`, `tool.dispatched`, `tool.result`, `memory.write`, `budget.exceeded`, `task.halted`, `config.changed`, `admin.action` |
| `model` | Model ID, provider channel, token counts, stop reason |
| `tool` | Connector, action, action class, target resource ID |
| `policy` | Policy bundle version, rule ID, decision |
| `payload_ref` | Pointer to the full payload in encrypted object storage, with a content hash |
| `data_labels` | Classification labels detected on the payload |

**Write-ahead rule.** `tool.dispatched` is durably written before the network call. A crash mid-call leaves a record showing the action was attempted with no recorded outcome, so it is never silently lost.

**Full-content capture is configurable per tenant.** The default captures everything, because FS supervision requires it. Healthcare tenants may prefer references plus hashes for PHI, with the content held under a stricter retention policy.

## 4.4 Data controls

| Control | Implementation |
|---|---|
| Tenant isolation | A dedicated data plane per tenant (no shared databases). The control plane is logically multi-tenant but holds no content. |
| Encryption | TLS 1.2+ in transit, with mTLS inside the data plane. At rest, AES-256 under customer-managed keys in the customer's KMS. Revoking the key renders the data plane unreadable. |
| Residency | Region is pinned at tenant creation. Model inference stays in-region, using the provider's inference-geography control or a regional endpoint. Backups also stay in region. |
| Model provider retention | Customers consume Claude under their own agreement and channel. Keel documents what each channel retains and supports tenants that require zero data retention. Some newer Claude models have retention requirements that exclude ZDR orgs, so the model gateway blocks selecting a model that the tenant's retention posture does not allow. |
| No training | Contractual commitment that Keel never trains on customer data. Depends on the provider terms of the channel the customer uses. |
| DLP | Ingress and egress classification, Purview label inheritance, and redaction before model send where policy requires it |
| Retention and legal hold | Per data class. Legal hold overrides deletion. eDiscovery search spans tasks, transcripts, approvals, and memory. |

## 4.5 Threat model (top risks)

| # | Threat | Primary mitigations | Residual |
|---|---|---|---|
| T1 | **Indirect prompt injection** via retrieved documents, tickets, or messages causes an unwanted action | Planner/executor split; per-step tool scoping; plan-scope enforcement; untrusted-content labeling; PDP on every call; approvals bound to payload hash; memory quarantine | **Medium.** No mitigation eliminates injection. The design goal is that a successful injection can only do what the approved plan and policy already allowed. |
| T2 | **Data exfiltration** through a write or external-share action | Action-class policy (external-share denied at L2+); egress DLP; domain allowlists; no general web fetch in v1 | Low–medium |
| T3 | **Privilege escalation** through the agent: the agent reaches data the user can't | Source ACL enforcement; token exchange with the user as subject; no service accounts with broad scope | Low |
| T4 | **Runaway autonomy.** A standing task loops, spams, or burns spend. | Autonomy budgets enforced outside the model path; rate limits; expiry; kill switch (ENT-16) | Low |
| T5 | **Malicious or compromised connector** | Signed connectors only; manifest-declared scopes enforced by the gateway; connectors isolated in their own pods with network policy | Medium |
| T6 | **Insider misuse.** A user tasks the agent to aggregate data they shouldn't combine. | Audit, DLP, and analytics on unusual aggregation; supervisor review queues | Medium |
| T7 | **Control-plane compromise pushes a malicious policy** | Policy bundles signed with a tenant-held co-signing key for L3; data plane rejects unsigned or rolled-back bundles; policy diffs are audited | Low |
| T8 | **Audit tampering** | Hash chain, WORM anchoring, SIEM streaming (an independent copy) | Low |

## 4.6 Compliance targets

| Framework | Target | Timing |
|---|---|---|
| SOC 2 Type II | Security, Availability, Confidentiality | Type I at v1 GA, Type II 6–9 months after |
| ISO/IEC 27001 + 27701 | Certified | Year one |
| ISO/IEC 42001 (AI management system) | Certified | Year one to two. It is increasingly asked for in FS procurement. |
| HIPAA | BAA available for dedicated and customer-VPC deployments | v1 GA |
| SEC 17a-4 / FINRA 4511 | Supported via WORM archive integration plus a third-party attestation letter | v1 GA |
| DORA (EU FS) | ICT third-party register support, exit plan, incident reporting hooks | v1.x for EU launch |
| FedRAMP Moderate → High | Sovereign deployment model, Claude via an authorized channel such as Bedrock GovCloud | Year two (see doc 5) |
| NIST SP 800-53 Rev 5 / AI RMF | Control mapping published, reusing the Control Baseline crosswalk structure | v1 GA |

**Verify before committing to a date:** which Claude models are available on each authorized government channel, and at what impact level. This changes frequently, and the Control Baseline tracks it.

## 4.7 Evaluation and model risk

Evaluation is a formal gate, because FS model-risk teams (SR 11-7) will ask for this evidence first.

- **Capability suite:** golden tasks for each core job and connector, graded on outcome correctness and citation accuracy.
- **Safety suite:** a prompt-injection corpus planted in documents, tickets, and messages, scored on whether any action outside the plan or policy was *attempted*. Also covers data-aggregation abuse cases and refusal and false-refusal rates.
- **Regression gate:** every change to model ID, prompt, tool description, or default policy runs both suites. Any regression on the safety suite blocks the release.
- **Customer-visible model cards:** per-tenant documentation of pinned models, eval results, and change history, packaged for the customer's model-risk review.

## 4.8 Gaps this closes in the Claude Enterprise Control Baseline

| Baseline gap | How Keel addresses it |
|---|---|
| 6.3 / 9.5 — Unattended autonomous execution has no technical control | Standing tasks are owned, expiring workflows with enforced budgets and a kill switch |
| 9.5 — Non-human agent identity | Per-task agent principal with delegated, down-scoped, short-lived credentials |
| 6.4 / 9.5 — Centrally unreviewable configuration | All instructions, memory, and standing tasks are stored centrally, versioned, and reviewable (ENT-15) |
| 6.6 — Prompt injection residual risk | Not eliminated, but bounded by plan scope, the PDP, and payload-bound approvals (T1) |
