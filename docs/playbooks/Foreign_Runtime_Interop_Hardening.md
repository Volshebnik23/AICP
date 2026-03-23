# Foreign Runtime Interop Hardening Playbook

> **Status:** Informative playbook grounded in shipped AICP artifacts.
>
> **Important:** This document does **not** claim that ChatGPT or Lovable implement AICP today. In this playbook, **Runtime A = ChatGPT** and **Runtime B = Lovable** are named stand-ins for two heterogeneous, non-native external runtimes with different owners, trust roots, goals, approval boundaries, and continuity assumptions.

## 1. What this playbook is for

Use this playbook when an AICP-speaking gateway, mediator, or adapter must interoperate with a foreign runtime that is **not AICP-native** and may expose only partial continuity, approval, or identity semantics.

This playbook is intentionally narrow:
- it uses shipped AICP profile and extension surfaces as the source of truth,
- it shows how to keep interoperability claims truthful,
- it treats foreign runtimes as adjacent systems behind adapters/gateways rather than as protocol-defined peers by default.

Relevant shipped surfaces:
- profile negotiation and rejection: `EXT-CAPNEG`. 
- product profile selection: `AICP-BASE`, `AICP-MEDIATED-BLOCKING`, `AICP-MEDIATED-BLOCKING-OPS`, `AICP-RESUMABLE-SESSIONS`, `AICP-DELEGATED-IDENTITY`, and `AICP-EXECUTION-INTEROP`. 
- approval boundary evidence: `EXT-HUMAN-APPROVAL`. 
- delegated actor/account binding: `EXT-DELEGATED-IDENTITY`. 
- reconnect and recovery: `EXT-RESUME` and `EXT-OBJECT-RESYNC`. 
- deterministic rejection and escalation contour: CAPNEG `reason_code` registry plus transcript-visible rejection artifacts. 

## 2. What AICP already ships vs. what remains hypothetical

### 2.1 Shipped and repo-backed today

AICP already ships:
- deterministic capability/profile negotiation via `CAPABILITIES_DECLARE`, `CAPABILITIES_PROPOSE`, `CAPABILITIES_ACCEPT`, and `CAPABILITIES_REJECT`. 
- registered CAPNEG rejection codes such as `DOWNGRADE_NOT_ALLOWED`, `REQUIRED_PROFILE_UNSUPPORTED`, and `PROFILE_NOT_ACCEPTABLE`. 
- executable profile catalogs and conformance suites for mediated blocking, resumable sessions, delegated identity, and execution interoperability. 
- transcript-native approval artifacts (`APPROVAL_CHALLENGE`, `APPROVAL_GRANT`, `APPROVAL_DENY`, `INTERVENTION_*`) without standardizing any particular runtime UX or IAM product. 
- transcript-native resume/resync semantics that distinguish reconnect handshake from object/state rehydration. 

### 2.2 Plausible implications when a foreign runtime sits behind an adapter

If Runtime A and Runtime B are reached through gateways, it is plausible that:
- one runtime can preserve conversational continuity but cannot rehydrate opaque runtime objects,
- one runtime can execute actions only after owner-local approval, while the other treats the same action as agent-autonomous,
- one runtime can assert an operator or account identity rooted in an external issuer, while the other only exposes runtime-local actor labels,
- both runtimes can exchange governed transcript artifacts even when their internal state models differ.

### 2.3 Still hypothetical or underspecified

This repository does **not** currently standardize:
- any real ChatGPT API mapping,
- any real Lovable API mapping,
- cross-runtime object serialization for proprietary thread/run/store internals,
- equivalence rules for runtime-native approval UX outside transcript evidence,
- a universal translation layer from vendor-specific runtime memory/state into AICP object-resync artifacts.

Treat all such behavior as adapter-local and claim only the AICP profile/extension behavior you can actually evidence.

## 3. Highest-value ambiguity: continuity claims are often overstated

The most dangerous foreign-runtime mistake is to treat **“the remote runtime can resume the conversation”** as equivalent to **“the remote runtime can deterministically resync governed state and approval/identity context.”**

In AICP those are separate claims:
- `EXT-RESUME` answers whether a participant can reconnect to a session head. 
- `EXT-OBJECT-RESYNC` answers whether missing objects/state can be retrieved or rehydrated. 
- `AICP-EXECUTION-INTEROP@0.1` bundles execution metadata with both resume and object resync, but does **not** standardize proprietary runtime internals. 

**Operational rule:** if a foreign runtime can reconnect to a thread but cannot reproduce missing governed objects, approval bindings, or delegated-identity evidence, do **not** negotiate or imply a stronger continuity profile than the transcript can prove.

## 4. Thought-experiment scenario: Runtime A (ChatGPT) vs Runtime B (Lovable)

Again, these names are placeholders only.

### 4.1 Starting assumptions

- Runtime A is controlled by Owner A and is fronted by an AICP adapter.
- Runtime B is controlled by Owner B and is fronted by a different AICP adapter.
- The owners have different approval policies and different trust roots.
- Both adapters can emit AICP envelopes, but neither should claim more than its adapter can evidence.

### 4.2 Initial negotiation branch

Runtime A declares a minimum acceptable posture equivalent to:
- `AICP-MEDIATED-BLOCKING-OPS@0.1` when externalized moderation and reconnect evidence are mandatory, or
- `AICP-DELEGATED-IDENTITY@0.1` when acting-on-behalf-of user identity must be issuer-bound.

Runtime B replies with support closer to:
- `AICP-BASE@0.1` or another weaker subset,
- local owner approvals that are not yet represented as `APPROVAL_GRANT` evidence,
- conversational resume hints without portable object-resync guarantees.

**AICP-supported action:** the adapters should negotiate explicitly through CAPNEG and either:
- select the smallest mutually acceptable shipped profile, or
- reject deterministically if the proposed downgrade would erase required enforcement, delegated-identity, or continuity guarantees. 

### 4.3 Downgrade or rejection branch

Suppose Runtime A requires delegated identity because an agent is acting for a human-owned account, but Runtime B proposes `AICP-BASE@0.1` without issuer-bound subject evidence.

The safe AICP posture is:
- reject the proposal rather than silently “best effort” the identity mapping,
- use a transcript-visible `CAPABILITIES_REJECT`,
- emit a registered reason code whose meaning matches the failure mode:
  - `REQUIRED_PROFILE_UNSUPPORTED` when the other side does not support the required shipped profile at all,
  - `PROFILE_NOT_ACCEPTABLE` when the selected profile is supported somewhere but violates local deployment policy,
  - `DOWNGRADE_NOT_ALLOWED` when the other side attempts to step below an already agreed baseline. 

### 4.4 Approval-sensitive action boundary

Assume Runtime B asks Runtime A to trigger an irreversible external action.

If Runtime A’s owner requires human review before that action, then AICP already provides the correct boundary:
- challenge the action with `APPROVAL_CHALLENGE`,
- require a matching `APPROVAL_GRANT` or `APPROVAL_DENY`,
- do not treat foreign runtime UI text such as “approved” or “confirmed” as equivalent unless it is bridged into transcript evidence by the adapter. 

**Hardening rule:** approval semantics are owner-local until they are translated into AICP evidence. A foreign runtime cannot collapse another owner’s approval boundary merely because both are participating in one conversation.

### 4.5 Continuity and resume stress point

Now suppose the transport reconnects after the approval challenge but before the action result is anchored.

A correct heterogeneous-runtime recovery path is:
1. use `RESUME_REQUEST` / `RESUME_RESPONSE` to determine whether the session head matches, 
2. if the response is `NEEDS_RESYNC`, use `EXT-OBJECT-RESYNC` to fetch the missing approval or contract objects when available, 
3. if the foreign runtime cannot provide the missing governed objects, reject progression of the irreversible action and escalate instead of pretending that conversational continuity implies object continuity. 

**Do not assume:** “same chat thread” means “same enforceable state.”

### 4.6 Delegated identity / ownership ambiguity

Suppose Runtime B says it is acting for `user:alice`, but Runtime A’s owner requires issuer-scoped proof that the sender agent is actually bound to Alice’s account.

AICP already supports the safe answer:
- use `EXT-DELEGATED-IDENTITY` with a prior `SUBJECT_BINDING_ISSUE`,
- require `ext.subject_binding_hash` on messages that act on behalf of the user,
- fail closed if the binding is missing, expired, revoked, or rooted in an untrusted issuer. 

If Runtime B cannot provide that evidence, the adapter may still continue at a weaker profile **only if** the policy allows a different trust posture. Otherwise the correct behavior is a profile-level rejection, not a silent owner-trust substitution.

### 4.7 Evidence and escalation branch

If the runtimes remain mismatched after negotiation or resume, the transcript should preserve a machine-checkable trail:
- the `CAPABILITIES_REJECT` artifact with reason code and detail, 
- any related approval challenge/denial or intervention requirement, 
- any resume response showing `NEEDS_RESYNC` or `UNKNOWN_SESSION`, 
- any delegated-identity revocation/expiry evidence that caused the rejection. 

This lets a third-party reviewer distinguish:
- supported AICP behavior,
- local runtime limitation, and
- operator policy refusal.

## 5. Decision rules for foreign-runtime adapters

### 5.1 Negotiate the smallest truthful profile

Prefer this order:
1. negotiate the smallest shipped profile that both adapters can actually evidence, 
2. reject stronger-profile claims that rely on runtime-local assumptions, 
3. downgrade only when the weaker profile still satisfies local minimum policy. 

### 5.2 Separate “conversation continuity” from “state continuity”

A foreign runtime may support chat continuity while lacking:
- object replay,
- approval evidence replay,
- delegated identity replay,
- deterministic restoration of tool/run/store objects.

If so, claim at most the continuity your transcript can prove.

### 5.3 Separate actor labels from delegated identity

A runtime-local username, workspace role, or session principal is **not** automatically a delegated-identity proof. Use `EXT-DELEGATED-IDENTITY` only when issuer-bound evidence exists.

### 5.4 Treat owner-local approvals as non-transferable by default

Owner A’s approval boundary and Owner B’s approval boundary are independent until transcript evidence explicitly bridges them. A gateway should therefore fail closed on irreversible actions if approval evidence cannot be resolved.

### 5.5 Make rejection semantics deterministic

For heterogeneous runtime mismatch, prefer transcript-visible rejection over silent fallback. A rejection should answer two questions for outside reviewers:
- **What failed?** profile, extension, approval, identity, or continuity assumption.
- **Why was it blocked?** unsupported capability, unacceptable downgrade, or policy refusal.

## 6. Minimal implementer checklist

Before claiming cross-runtime interoperability, verify:
- CAPNEG declarations enumerate only supported shipped AICP profiles/extensions. 
- `CAPABILITIES_REJECT.reason_code` is registered and semantically aligned to the mismatch. 
- approval-sensitive steps do not proceed without transcript-native approval evidence when policy requires it. 
- resume flows do not imply object resync unless the adapter can actually supply missing governed objects. 
- delegated identity claims are backed by issuer-bound subject bindings or are explicitly rejected/downgraded. 
- interop claims remain adapter-scoped and never imply product/vendor support that has not been evidenced. 

## 7. Top remaining gaps after applying this playbook

This playbook hardens decision-making, but these gaps still remain in the repo:
1. no standard adapter profile yet defines how a foreign runtime should expose proprietary run/thread/store state as portable AICP resync artifacts;
2. no cross-extension suite yet composes CAPNEG rejection, delegated identity, approval, and resume into one single executable heterogeneous-runtime drill;
3. no public interop dry-run package yet demonstrates a foreign-runtime pairwise submission using truthful “adapter-mediated” claim language.

## 8. Related repo references

- `docs/profiles/AICP_Profiles.md`
- `docs/profiles/Profile_Selection_Guide.md`
- `docs/architecture/AICP_Adoption_Core_and_Tiers.md`
- `docs/guides/Protocol_Adapter_Gateway.md`
- `docs/adjacent/A2A_Integration_Pattern.md`
- `docs/architecture/AICP_in_the_Ecosystem.md`
- `docs/extensions/RFC_EXT_CAPNEG.md`
- `docs/extensions/RFC_EXT_RESUME.md`
- `docs/extensions/RFC_EXT_OBJECT_RESYNC.md`
- `docs/extensions/RFC_EXT_DELEGATED_IDENTITY.md`
- `docs/extensions/RFC_EXT_HUMAN_APPROVAL.md`
