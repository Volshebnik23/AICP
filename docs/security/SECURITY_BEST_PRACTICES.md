# AICP Security Best Practices (Implementer-Focused)

Repository review status is narrower than this guidance surface: an internal self-review and
automated negative tests exist, but no completed independent external security review is
present. See `security_review/README.md`, `security_review/COVERAGE_MAP.md`, and
`docs/process/AICP_Repo_Truth_Baseline.md`.

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

## 10) External evidence privacy and identity boundary

External evidence reports intentionally record implementation ID, version, build digest,
adapter stderr, case observations, generated projection artifacts, and digests of required
inputs. Treat reports as potentially sensitive before publication:

- use non-secret stable implementation identifiers;
- keep credentials, private keys, bearer tokens, private endpoint data, and unneeded
  internal state out of adapter stderr and projection `extension_data`;
- inspect generated artifacts and disclosures before adding a report to a submission;
- publish only the minimum report and bundle files needed for the scoped claim;
- retain private raw logs outside the public corpus when they are not required evidence.

SHA-256 digests bind the evaluated bytes and detect drift; they do not authenticate an
organization, establish authority over a session, certify an implementation, or prove
that a named vendor produced the report. `execution_subject`, review, and publication
process supply separate identity context. The checked-in reference adapters and fictional
external-kind test adapters are not independent implementations, and no real external
capability or Tier-1 profile submission is currently present.

Evidence TCK 1.1.0 also treats expected-answer disclosure as a test-integrity risk.
Producer requests contain only raw scenario facts and a response-free transcript prefix;
reviewed projections, hashes, fixture paths, and case IDs remain private to the TCK.
Registry/schema/catalog and every statically imported load-bearing runner module are bound
by digest. Unknown handlers, unavailable schema validation, historical 1.0.0 reports, and
dependency-closure drift fail closed and emit no capability mark.

Evidence TCK 1.2.0 applies the same disclosure boundary to generated profile transcripts.
Neutral producer requests contain the exact profile, session/contract/participant facts,
required suites, and a deterministic seed, but no fixture path, case identity, golden
message/hash, expected error, or mark. Treat generated transcripts as potentially sensitive
before publication. Missing JSON Schema or Ed25519 verification, invalid hash/signature or
key lifecycle, suite/input/profile provenance drift, and incomplete coverage suppress the
profile mark. Report digests establish byte integrity, not implementer identity,
certification, live transport interoperability, or pairwise interoperability.
