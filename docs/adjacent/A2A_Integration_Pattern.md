# A2A Integration Pattern (Informative, non-normative)

> **Status:** Informative guidance only. This document does not define protocol requirements, transport bindings, or a new standard.

## 1) Purpose

Show how an A2A-like calling/connectivity layer can coexist with AICP without boundary confusion.

- Calling/connectivity handles rendezvous, reachability, and live session transport.
- AICP carries governed transcript semantics, policy/approval/evidence linkage, and interoperability profile expectations.

## 2) Scope

In scope:
- layered composition guidance,
- practical bootstrap/handoff/relay patterns,
- failure/fallback and continuity notes.

Out of scope:
- defining an A2A protocol,
- defining discovery APIs,
- defining transport mechanics,
- defining IAM/payment/tool runtime internals.

## 3) Why A2A-like calling and AICP are complementary

They solve different problems:

- **A2A-like layer:** “How do parties find each other and exchange live calls/messages?”
- **AICP:** “How do parties represent governed conversation state and evidence so third parties can verify outcomes?”

AICP should not be treated as calling/discovery. A2A-like calling should not be treated as transcript governance evidence.

## 4) Layered composition model

```text
Discovery/Directory (optional)
    ->
A2A-like Calling/Connectivity (session path + delivery)
    ->
AICP Transcript Layer (contracts/policy/approval/evidence/profile semantics)
    ->
External execution systems (tools/IAM/commerce/trust)
```

## 5) Practical patterns

### Pattern A: Rendezvous/bootstrap
1. Discovery/directory resolves peer metadata (optional).
2. A2A-like layer establishes session channel.
3. AICP CAPNEG negotiates required profile/extensions.
4. AICP transcript proceeds with governed artifacts.

**Failure handling:**
- If calling path fails before CAPNEG completion, retry/failover at calling layer.
- If CAPNEG/profile mismatch occurs, fail deterministically in AICP transcript (not via transport assumptions).

### Pattern B: Specialist handoff
1. Primary agent receives request.
2. A2A-like layer opens sub-session with specialist.
3. AICP records governed handoff context, policy/approval requirements, and evidence refs.
4. Specialist output is returned through calling path, then anchored in AICP transcript.

**Boundary rule:** handoff routing is calling-layer behavior; accountability/evidence continuity is AICP behavior.

### Pattern C: Relay/fallback path
1. Primary calling path degrades.
2. Relay/fallback channel is selected by adjacent connectivity systems.
3. AICP transcript continuity is preserved by message linkage/evidence references/profile semantics.

**Failure handling:**
- If relay cannot preserve expected delivery guarantees, record degraded mode and continue only under policy.
- Avoid side-effect progression unless required policy/approval evidence remains valid in transcript context.

## 6) Bootstrap/failure/fallback checklist (implementation aid)

- Verify profile selection explicitly (`required_aicp_profiles` + selected profile evidence).
- Preserve transcript continuity across reconnect/failover (`prev_msg_hash` / artifact refs / linked evidence).
- Keep calling metadata and governed evidence roles distinct.
- Re-check policy/approval gating before irreversible external steps after reconnect.
- Record degraded/fallback reasons as transcript-visible artifacts when policy requires auditable continuity.

## 7) Common misuses to avoid

- Treating AICP as discovery/routing.
- Treating calling success as proof of policy/approval compliance.
- Encoding vendor runtime-only calling assumptions as profile requirements.
- Assuming payment/IAM/tool runtime behavior is standardized by AICP.

## 8) Related docs

- [AICP in the Ecosystem](../architecture/AICP_in_the_Ecosystem.md)
- [Protocol Adapter / Gateway](../guides/Protocol_Adapter_Gateway.md)
- [Session Topologies playbook](../playbooks/Session_Topologies.md)
- [Profile Selection Guide](../profiles/Profile_Selection_Guide.md)
