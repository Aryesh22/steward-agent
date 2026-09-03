# Steward — Architecture

> Full component diagram + data flows live in `IMPLEMENTATION_PLAN.md` §5. This file is the narrative companion
> and the place to export a PNG of the diagram for the demo/README if needed.

## Components & the AWS service each maps to

| Component | Responsibility | AWS / SDK |
|---|---|---|
| Entrypoint | Receives invocations (sweep or event), runs the graph, handles interrupts | `BedrockAgentCoreApp` (bedrock-agentcore), AgentCore **Runtime** |
| Router / Orchestrator | Classifies input → `task_type` + confidence; pulls org context | Strands `Agent` + AgentCore **Memory** |
| Specialist agents (Recruiter / Matcher / Grant) | Do the actual task via tools | Strands **Agents-as-Tools** |
| ReviewerAgent | Independent verification of each action (feeds graduation) | Strands `Agent` (cheap model) |
| Trust Ratchet gate | Decides act-vs-escalate per task-type (autonomy + confidence gates) | Strands **Graph** conditional edge + **DynamoDB** |
| human_review node | Escalation surface — pause and ask the coordinator | Strands **interrupt** → **Twilio** SMS |
| Tools (Sheets, SNS) | Read/write the org Sheet; send SMS | AgentCore **Gateway** (MCP) + **Identity** |
| Trust state | Per-task-type autonomy counters, keyed by `org_id` | **DynamoDB** (`steward_trust`) |
| Audit journal | Append-only record of every action + confidence + reasoning | **DynamoDB** (`steward_audit`) + CloudWatch |
| Institutional knowledge | Org facts/preferences/summaries surviving turnover | AgentCore **Memory** |
| Triggers | Nightly sweep + inbound SMS | **EventBridge Scheduler** + API Gateway/Lambda → `InvokeAgentRuntime` |
| Observability | Traces, token usage, errors | AgentCore **Observability** → **CloudWatch** |

## Two data flows
1. **Nightly sweep:** EventBridge Scheduler → `InvokeAgentRuntime` (`mode:"sweep"`) → read Sheet → per-task ratchet
   gate → execute or escalate → ReviewerAgent verifies → ratchet updates. Long runs use the async-task pattern.
2. **Inbound event:** Inbound SMS → API Gateway → Lambda → `InvokeAgentRuntime` (`mode:"event"`) → Matcher (L1) →
   escalate if a perishable can't be placed / confidence low.

## Key design decisions (see IMPLEMENTATION_PLAN.md §16)
- Trust counters in **DynamoDB** (atomic), not AgentCore Memory (which is semantic/retrieval).
- Trust keyed by **`org_id`**, not user → institutional persistence.
- Interrupts come from the **Strands** layer; scheduling via **EventBridge Scheduler + async task** (no native
  Runtime interrupt or EventBridge target).
- **SMS via Amazon SNS** (boto3, no extra credentials — reuses existing IAM/AWS creds); replaces Twilio.
  Sheets/SNS start as local `@tool`s, migrate to **Gateway** MCP tools by Phase 4.
