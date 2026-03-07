# Session Topologies and Context Portability Cookbook

This cookbook documents architecture patterns for session ownership, mediation, relay, and context portability.

## Pattern 1: External agent joins my hosted AICP session
- **Problem addressed:** brand/platform needs control over moderation and policy gating.
- **Actor topology:** host mediator + external agent + optional enforcer.
- **Transcript owner:** host.
- **Mediator/enforcer:** host-owned or delegated.
- **Context shared:** host-approved scope.
- **Context withheld/redacted:** host-restricted/private data.
- **References/hashes moved:** contract refs, selected prior evidence refs.
- **Profile fit:** `AICP-MEDIATED-BLOCKING@0.1`.
- **Adjacent infra assumed:** transport + host IAM.
- **Common pitfalls:** over-sharing host-internal context.
- **When not to use:** when host cannot legally/operationally own transcript.

## Pattern 2: My agent joins a foreign hosted reception
- **Problem addressed:** consume external hosted service with governed semantics.
- **Actor topology:** foreign host mediator + your agent.
- **Transcript owner:** foreign host.
- **Mediator/enforcer:** foreign host policy domain.
- **Context shared:** minimal required request context.
- **Context withheld/redacted:** local/private context outside foreign scope.
- **References/hashes moved:** references to local context summaries where needed.
- **Profile fit:** `AICP-BASE@0.1` minimum; add resumable profile as needed.
- **Adjacent infra assumed:** foreign connectivity and identity acceptance.
- **Common pitfalls:** assuming local policy semantics automatically apply.
- **When not to use:** when foreign hosting terms conflict with your policy/compliance constraints.

## Pattern 3: Relay via a trusted third agent
- **Problem addressed:** no direct access between parties.
- **Actor topology:** source agent -> trusted relay -> destination reception.
- **Transcript owner:** depends on hosted endpoint; relay may keep independent evidence log.
- **Mediator/enforcer:** hosted endpoint; relay may add policy checks.
- **Context shared:** relay-approved and endpoint-approved subset.
- **Context withheld/redacted:** source-private data not required downstream.
- **References/hashes moved:** portability relies on summary hashes and attested relayed references.
- **Profile fit:** `AICP-BASE@0.1` plus `AICP-DELEGATED-IDENTITY@0.1` when authority delegation matters.
- **Adjacent infra assumed:** relay trust contract and identity assertions.
- **Common pitfalls:** provenance ambiguity when relay rewriting is undocumented.
- **When not to use:** if direct integration is possible and lower-risk.

## Pattern 4: Private side session + summarized return to main session
- **Problem addressed:** isolate sensitive processing while preserving main-session continuity.
- **Actor topology:** main session participants + side session participants.
- **Transcript owner:** separate owners per session.
- **Mediator/enforcer:** per-session.
- **Context shared:** summary/attested outputs back to main session.
- **Context withheld/redacted:** raw private side-session content.
- **References/hashes moved:** side-session output hashes/evidence refs.
- **Profile fit:** `AICP-RESUMABLE-SESSIONS@0.1` useful for continuity.
- **Adjacent infra assumed:** secure side-session hosting.
- **Common pitfalls:** leaking private side-session internals in summaries.
- **When not to use:** if full transparency is mandated by policy.

## Pattern 5: Subchat / scoped thread / bounded context branch
- **Problem addressed:** parallel scoped work under one broader engagement.
- **Actor topology:** parent session + bounded branch/subchat participants.
- **Transcript owner:** usually host owning parent session; may vary.
- **Mediator/enforcer:** inherited or scoped per branch.
- **Context shared:** branch-specific context + selected parent references.
- **Context withheld/redacted:** unrelated parent context.
- **References/hashes moved:** parent/branch linkage references.
- **Profile fit:** `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1` for structured branching workflows.
- **Adjacent infra assumed:** branch lifecycle controls.
- **Common pitfalls:** missing linkage causing audit gaps.
- **When not to use:** for very short interactions with no branching value.

## Pattern 6: AICP-governed conversation with MCP tool sidecar
- **Problem addressed:** governed conversation with external tool runtime.
- **Actor topology:** agent(s) + mediator + MCP-like sidecar/tool service.
- **Transcript owner:** session host.
- **Mediator/enforcer:** host plus tool-gating policy if used.
- **Context shared:** tool input/output references and approvals.
- **Context withheld/redacted:** tool internals and non-required execution traces.
- **References/hashes moved:** tool result hashes, evidence refs, approvals.
- **Profile fit:** `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1` or `AICP-MEDIATED-BLOCKING-OPS@0.1`.
- **Adjacent infra assumed:** MCP-like runtime and execution controls.
- **Common pitfalls:** treating tool protocol as if it were AICP itself.
- **When not to use:** if you only need local single-agent tool orchestration without cross-party governance.

## Pattern 7: External protocol bridge pattern
- **Problem addressed:** external action/system runs outside AICP, but governance evidence must remain portable.
- **Actor topology:** AICP session + external protocol/system + adapter/gateway.
- **Transcript owner:** session host; external system keeps its own records.
- **Mediator/enforcer:** AICP mediator/enforcer for governed conversation; external system for its own domain.
- **Context shared:** anchored references to external action results and approvals.
- **Context withheld/redacted:** external system internals not needed for AICP evidence.
- **References/hashes moved:** object hashes, external IDs, attestations, approval artifacts.
- **Profile fit:** scenario-dependent; often `AICP-BASE@0.1` + stricter profile as needed.
- **Adjacent infra assumed:** external protocol/runtime + adapter.
- **Common pitfalls:** opaque external actions with no evidence linkage.
- **When not to use:** if full in-protocol artifact capture is mandatory and bridge cannot provide it.

## Context portability

### Summary vs full object resync
- **Summary portability** is best when recipients only need decision context and evidence anchors.
- **Full object resync** is best when recipients must independently validate full prior context.

### Redacted forwarding vs attested forwarding
- **Redacted forwarding** is preferable for privacy/data minimization boundaries.
- **Attested forwarding** is preferable when trust verification across boundaries is critical.

### Unsafe replay cases
Replaying prior session context can be unsafe when:
- policy scope changed,
- consent/authority expired,
- context classification disallows reuse,
- stale or conflicting evidence refs cannot be revalidated.

## See also
- [AICP canonical flows](../flows/AICP_Canonical_Flows.md)
- [AICP in the ecosystem](../architecture/AICP_in_the_Ecosystem.md)
- [Enforcement models](../architecture/Enforcement_Models.md)
