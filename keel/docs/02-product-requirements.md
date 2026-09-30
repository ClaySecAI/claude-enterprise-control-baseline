# 2. Product requirements

Requirement IDs are stable, so we can cite them in architecture, controls, and tests. Priority: **P0** blocks v1 GA, **P1** is v1 target, **P2** is v1.x.

## 2.1 Personas

| Persona | Who | What they need from Keel |
|---|---|---|
| **Knowledge worker** | Analyst, relationship manager, care coordinator, program officer | Delegate multi-step work across their tools and get a trustworthy result without babysitting it |
| **Approver** | Manager, supervisor, compliance reviewer | See exactly what the agent is about to do, approve or reject quickly, and prove later that they did |
| **Tenant admin** | IT or platform owner | Roll out safely: control who gets which capabilities, which connectors, and which data |
| **Security and compliance** | CISO org, compliance, internal audit | Evidence: complete audit trail, retention, eDiscovery, DLP events, SIEM feed, and control mappings |
| **Connector developer** | Internal platform team | Build a governed connector to an in-house system without forking Keel |

## 2.2 Core jobs (v1)

1. **"Pull it together."** Gather material from several systems and produce a draft: a deal memo from Salesforce, SharePoint, and Slack, or a prior-auth packet from the EHR export and the policy library.
2. **"Keep it moving."** Own a multi-day goal: chase open Jira tickets, re-ping owners on Teams, update the tracker, and summarize status every morning.
3. **"Watch for it."** Run a standing task on a trigger or schedule: when a ServiceNow incident of type X opens, gather context and post a triage summary.
4. **"Do the tedious write."** Make bounded, approved changes in bulk: update 40 Salesforce records, file tickets from meeting notes, or move documents to the right library.

## 2.3 Functional requirements

### Agent and tasks

| ID | Requirement | Pri |
|---|---|---|
| AGT-01 | A user can start a task from chat, from a Teams/Slack message action, or from the web app | P0 |
| AGT-02 | Before executing a multi-step task, Keel shows a plan listing the steps, the systems each step touches, and which steps will pause for approval | P0 |
| AGT-03 | Tasks persist across sessions and survive process restarts, and the user can see their state at any time | P0 |
| AGT-04 | A task can wait on external events (reply, approval, ticket state change) without consuming model tokens | P0 |
| AGT-05 | Scheduled and triggered standing tasks run under a named owner, with an expiry date that must be renewed | P0 |
| AGT-06 | The user can pause, resume, edit the goal of, or cancel any task, and cancellation stops in-flight tool calls | P0 |
| AGT-07 | Each task runs within an autonomy budget: wall-clock time, model spend, number of write actions, and allowed systems. Exceeding it pauses the task for the owner. | P0 |
| AGT-08 | Keel produces a final report per task: outcome, actions taken with links, sources used, and anything it could not do | P0 |
| AGT-09 | Memory: Keel remembers user preferences and working context across tasks. Every memory item is viewable, editable, and deletable by the user, and visible to admins under policy. | P1 |
| AGT-10 | Tasks can be shared or handed off to another user, which re-evaluates permissions under the new owner | P2 |
| AGT-11 | Cited answers: every factual claim in a draft links to the source document or record it came from | P0 |

### Connectors

| ID | Requirement | Pri |
|---|---|---|
| CON-01 | v1 connectors: M365 (SharePoint, OneDrive, Teams), Google Workspace (Drive, Chat), Slack, Jira, Confluence, ServiceNow, Salesforce, Box | P0 |
| CON-02 | Read-only mail and calendar access (M365, Google) for context gathering. Drafts are saved to the user's drafts folder and never sent. | P1 |
| CON-03 | Every connector action is classified as *read*, *write*, *destructive*, or *external-share*, and policy is written against those classes | P0 |
| CON-04 | Connectors enforce the source system's own permissions: Keel can never read what the user can't | P0 |
| CON-05 | Private connector SDK (MCP-based) with a manifest declaring actions, action classes, data categories, and scopes | P1 |
| CON-06 | Admins enable connectors per group, and can restrict to a subset of actions or of sites/projects/channels | P0 |

### Enterprise controls

| ID | Requirement | Pri |
|---|---|---|
| ENT-01 | SSO via SAML 2.0 and OIDC, with IdP-enforced MFA and conditional access passed through | P0 |
| ENT-02 | SCIM 2.0 provisioning and deprovisioning. Deprovisioning revokes all delegated credentials and halts the user's tasks within 5 minutes. | P0 |
| ENT-03 | RBAC with built-in roles (User, Approver, Connector Admin, Policy Admin, Auditor, Tenant Owner) and custom roles. Group-based assignment from the IdP. | P0 |
| ENT-04 | Policy engine: tenant-authored rules over user, group, connector, action class, data classification, time, and autonomy budget | P0 |
| ENT-05 | Approval workflows: single approver, two-person rule, and approval by a role (for example, supervising principal). Approvals are delivered in Teams, Slack, and the web app. | P0 |
| ENT-06 | Immutable audit log of every prompt, plan, model response, tool call, policy decision, approval, and side effect (schema in doc 4) | P0 |
| ENT-07 | Audit export: streaming to SIEM (Splunk, Sentinel, Chronicle), and bulk export in a documented schema | P0 |
| ENT-08 | Retention policies per data class, legal hold, and eDiscovery search across tasks, transcripts, and memory | P0 |
| ENT-09 | WORM-capable archive target for recordkeeping (SEC 17a-4(f)-compliant storage) | P1 |
| ENT-10 | DLP: classify content on ingress and egress, and block or redact per policy. Integrates with Microsoft Purview labels and existing DLP engines. | P0 |
| ENT-11 | Data residency: tenant selects region, and all customer content and inference stay in that region | P0 |
| ENT-12 | Customer-managed encryption keys (BYOK/HYOK) for all data at rest in the data plane | P0 |
| ENT-13 | Usage and cost analytics per user, group, connector, and task. Budgets and hard caps. | P1 |
| ENT-14 | Admin API for everything the console can do, so tenants can manage Keel as code | P1 |
| ENT-15 | Central view of all agent-shaping configuration: system instructions, user instructions, memory, standing tasks | P0 |
| ENT-16 | Kill switch: tenant-wide, per-group, per-connector, and per-task stop that takes effect within 60 seconds | P0 |

## 2.4 Non-functional requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-01 | Control-plane availability | 99.9% monthly |
| NFR-02 | Task durability | No task state lost on single-node or single-AZ failure |
| NFR-03 | Interactive latency | First visible response within 3 s at p50 and 8 s at p95, where the first response is the plan or a clarifying question |
| NFR-04 | Audit completeness | 100% of side-effecting actions have an audit record *before* the action executes (write-ahead) |
| NFR-05 | Scale per tenant | 50k users, 5k concurrent running tasks |
| NFR-06 | Accessibility | WCAG 2.2 AA for web app and approval surfaces |
| NFR-07 | Evaluation gate | No model, prompt, or policy-default change ships without passing the regression and safety eval suite (doc 4, section 4.7) |

## 2.5 What "done" looks like for a v1 customer

A mid-size broker-dealer can do all of the following:

- Roll Keel out to 2,000 users with SSO/SCIM.
- Restrict write actions to Salesforce and Jira, with supervisor approval on anything touching client records.
- Stream every agent action to Splunk.
- Retain transcripts to 17a-4 storage.
- Hand internal audit a control mapping they accept without a finding on agent identity or attribution.
