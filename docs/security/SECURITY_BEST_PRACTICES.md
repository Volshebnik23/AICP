# AICP Security Best Practices (Implementer-Focused)

This guide provides practical deployment guidance for teams shipping AICP systems today.
It does not introduce new protocol semantics; it maps existing AICP artifacts to safer implementation defaults.

## 1) Threat model quick-start

Before production, document at minimum:
- who can inject messages into your ingress path,
- who controls mediator/enforcer decisions,
- which external tools/APIs can create side effects,
- what identity/trust/status systems are external dependencies.

Then bind this model to profile and conformance choices (for example, mediated blocking, delegated identity, resume/object-resync).

## 2) Confused-deputy patterns

**Risk:** a privileged host/agent executes actions on behalf of lower-trust requesters without explicit scope checks.

**Safe defaults:**
- Require explicit contract/policy checks before side effects.
- Bind action authorization to transcript context and relevant attestation references.
- For delegated operations, verify actor/scope/expiry constraints consistently.
- Fail closed: when scope or authority is ambiguous, emit explicit rejection/error artifacts.

Relevant docs:
- `docs/extensions/RFC_EXT_DELEGATED_IDENTITY.md`
- `docs/extensions/RFC_EXT_IDENTITY_LIFECYCLE.md`
- `docs/extensions/RFC_EXT_POLICY_EVAL.md`

## 3) Token passthrough / credential forwarding hazards

**Risk:** forwarding bearer tokens or raw credentials across agents/tools leaks authority boundaries.

**Safe defaults:**
- Do not pass user/host bearer credentials directly to downstream agents by default.
- Use scoped, short-lived credentials minted per action boundary where possible.
- Record only needed credential references/attestations in transcript artifacts; avoid storing reusable secrets.
- Separate identity assertion artifacts from secret transport paths.

Relevant docs:
- `docs/extensions/RFC_EXT_DELEGATED_IDENTITY.md`
- `docs/extensions/RFC_EXT_TOOL_GATING.md`

## 4) SSRF via tools/resources

**Risk:** tool/resource calls can be abused to access internal metadata services or private network targets.

**Safe defaults:**
- Enforce outbound allowlists for tool/resource network access.
- Block link-local/private metadata endpoints by policy.
- Require tool-call policy checks before execution.
- Log and attest tool invocation decisions with minimal necessary details.

Relevant docs:
- `docs/extensions/RFC_EXT_TOOL_GATING.md`
- `docs/extensions/RFC_EXT_ENFORCEMENT.md`

## 5) Tool poisoning / catalog rug-pull

**Risk:** tool metadata/behavior changes unexpectedly after trust decisions are made.

**Safe defaults:**
- Pin tool manifests/versions per governed session or policy bundle.
- Validate hash/revision references before invoking high-impact tools.
- Treat dynamic tool catalog updates as policy events, not silent runtime drift.

Relevant docs:
- `docs/extensions/RFC_EXT_TOOL_GATING.md`
- `docs/rfc/RFC_Artifact_Manifests_and_Pinning.md` (M30 baseline for artifact pinning and anti-shadowing)

## 6) Session hijack / replay guidance

**Risk:** attackers replay old messages, inject stale state, or hijack resumed sessions.

**Safe defaults:**
- Enforce hash-chain integrity (`prev_msg_hash`, `message_hash`) and signature checks.
- Require deterministic replay handling and idempotency discipline in bindings.
- For resumed sessions, revalidate context assumptions and active policy constraints.
- Treat cross-session replay windows as explicit test targets.

Relevant docs/suites:
- `conformance/core/CT_CORE_0.1.json`
- `conformance/bindings/TB_HTTP_WS_0.1.json`
- `docs/extensions/RFC_EXT_RESUME.md`
- `docs/extensions/RFC_EXT_OBJECT_RESYNC.md`

## 7) Mediator equivocation considerations

**Risk:** mediator presents inconsistent views or ordering to different parties.

**Safe defaults:**
- Preserve immutable transcript logs with reproducible hash linkage.
- Keep evidence references portable so third parties can verify claims.
- Use dispute/escalation-capable profiles where multi-party trust is required.
- Prefer explicit conflict/dispute artifacts over out-of-band adjudication.

Relevant docs:
- `docs/extensions/RFC_EXT_DISPUTES.md`
- `docs/extensions/RFC_EXT_ENFORCEMENT.md`
- `docs/architecture/Enforcement_Models.md`

## 8) Practical secure defaults checklist

- Validate ingress messages against schema and conformance-relevant invariants.
- Verify signatures and signer key selection consistently.
- Minimize credential forwarding; enforce scoped delegation.
- Gate tool execution with explicit policies and outbound allowlists.
- Preserve full source envelopes for audit; project safely for internal consumers.
- Test replay/resume edge cases in CI using shipped conformance surfaces.
- Treat missing evidence as failure for high-impact actions.

## 9) Implementation references

- Start here: `START_HERE_IMPLEMENTERS.md`
- Core narrative: `docs/core/AICP_Core_v0.1_Normative.md`
- Profile selection: `docs/profiles/Profile_Selection_Guide.md`
- Enforcement topology choices: `docs/architecture/Enforcement_Models.md`
- Adapter integration pattern: `docs/guides/Protocol_Adapter_Gateway.md`
- Security hardening ops guide: `security_review/OPS_HARDENING_GUIDE.md`
- Mediated blocking production playbook: `docs/playbooks/Mediated_Blocking_in_Production.md`
