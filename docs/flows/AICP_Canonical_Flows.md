# AICP Canonical Flows and State Machines (M8.4)

This catalog provides implementer-oriented canonical message flows and state machines for AICP Core and key extensions.

## How to read these flows
- **Sequence diagrams** show the typical message exchange order across participants.
- **State diagrams** show lifecycle checkpoints and transition conditions.
- **Normative notes** under each diagram call out interoperability-critical invariants.
- **Executable counterpart:** these diagrams are paired with conformance suites and fixtures; use those artifacts as the source of machine-verifiable behavior.

---

## 2.1 Core Happy Path (signed transcript)

```mermaid
sequenceDiagram
    participant A as Agent A
    participant B as Agent B

    A->>B: CONTRACT_PROPOSE
    B->>A: CONTRACT_ACCEPT
    A->>B: ATTEST_ACTION
```

```mermaid
stateDiagram-v2
    [*] --> Proposed: CONTRACT_PROPOSE
    Proposed --> Accepted: CONTRACT_ACCEPT
    Accepted --> ActiveExchange: ATTEST_ACTION
    ActiveExchange --> [*]
```

Normative notes:
- Messages in the transcript MUST form a valid hash chain (`prev_msg_hash` references prior `message_hash`).
- `message_hash` MUST recompute from message body.
- Where signatures are present and verification is enabled, signatures SHOULD verify against known public keys.

Conformance reference: `conformance/core/CT_CORE_0.1.json`; fixtures: `fixtures/golden_transcripts/`.

---

## 2.2 Capability Negotiation (EXT-CAPNEG)

```mermaid
sequenceDiagram
    participant A as Initiator
    participant B as Responder

    A->>B: CAPABILITIES_DECLARE
    B->>A: CAPABILITIES_PROPOSE
    A->>B: CAPABILITIES_ACCEPT / CAPABILITIES_REJECT
```

```mermaid
stateDiagram-v2
    [*] --> Declared: CAPABILITIES_DECLARE
    Declared --> Proposed: CAPABILITIES_PROPOSE
    Proposed --> Negotiated: CAPABILITIES_ACCEPT
    Proposed --> Rejected: CAPABILITIES_REJECT
```

Normative notes:
- Conceptually this is request/response-style capability negotiation, represented by `DECLARE` + `PROPOSE` + terminal `ACCEPT`/`REJECT` messages.
- Implementations SHOULD prevent downgrade by binding accepted profile/capabilities to negotiated context.

Conformance reference: `conformance/extensions/CN_CAPNEG_0.1.json`; fixtures: `fixtures/extensions/capneg/`.

---

## 2.3 Policy Evaluation (EXT-POLICY-EVAL)

```mermaid
sequenceDiagram
    participant Agent
    participant Enforcer as Policy Engine / Enforcer

    Agent->>Enforcer: POLICY_EVAL_REQUEST (evaluation_context, target refs)
    Enforcer->>Agent: POLICY_EVAL_RESULT (decision, reason_codes)
```

```mermaid
stateDiagram-v2
    [*] --> Requested: POLICY_EVAL_REQUEST
    Requested --> Evaluated: POLICY_EVAL_RESULT
    Evaluated --> [*]
```

Normative notes:
- The request binds what is being evaluated via context and target references.
- Result decisions and reason codes MUST be machine-checkable against registry-defined reason codes.

Conformance reference: `conformance/extensions/PE_POLICY_EVAL_0.1.json`; fixtures: `fixtures/extensions/policy_eval/`.

---

## 2.4 Mediated Blocking Enforcement (EXT-ENFORCEMENT)

```mermaid
sequenceDiagram
    participant S as Sender
    participant E as Enforcer
    participant M as Mediator
    participant R as Receiver

    S->>M: CONTENT_MESSAGE
    M->>E: evaluate target_message_hash
    E->>M: ENFORCEMENT_VERDICT (ALLOW / DENY)
    M->>R: CONTENT_DELIVER (only on ALLOW)
```

```mermaid
stateDiagram-v2
    [*] --> PendingVerdict: CONTENT_MESSAGE received
    PendingVerdict --> Allowed: ENFORCEMENT_VERDICT(decision=ALLOW)
    PendingVerdict --> Blocked: ENFORCEMENT_VERDICT(decision!=ALLOW)
    Allowed --> Delivered: CONTENT_DELIVER
    Blocked --> [*]
    Delivered --> [*]
```

Normative notes:
- In blocking mode, mediator MUST NOT emit `CONTENT_DELIVER` without an `ALLOW` verdict.
- Verdict binding MUST be consistent: `target_message_hash` in verdict matches delivered `original_message_hash`.

Conformance reference: `conformance/extensions/ENF_ENFORCEMENT_0.1.json`; fixtures: `fixtures/extensions/enforcement/`.

---

## 2.5 Operational Alerts (EXT-ALERTS)

```mermaid
sequenceDiagram
    participant A as Any Sender / Mediator / Enforcer
    participant B as Peer

    A->>B: ALERT (system-wide, no target)
    Note over A,B: Example: MEDIATOR_UNAVAILABLE

    A->>B: ALERT (target_message_hash/target_message_id)
    Note over A,B: Example: RESYNC_REQUIRED

    B->>A: recovery action (RETRY / REMEDIATE / ACK_REQUIRED)
```

```mermaid
stateDiagram-v2
    [*] --> Normal
    Normal --> Warning: ALERT(severity=WARNING)
    Normal --> Fatal: ALERT(severity=FATAL)
    Warning --> Recovering: retry/remediate/resync
    Recovering --> Normal
    Fatal --> Disconnected: disconnect/escalate
    Disconnected --> [*]
```

Normative notes:
- `ALERT.code` MUST be registered in `registry/alert_codes.json`.
- Each entry in `recommended_actions` MUST be registered in `registry/alert_recommended_actions.json`.
- Target fields are optional for system-wide alerts and provide binding when present.

Conformance reference: `conformance/extensions/AL_ALERTS_0.1.json`; fixtures: `fixtures/extensions/alerts/`.

---

## 2.6 Object Resync (EXT-OBJECT-RESYNC)

```mermaid
sequenceDiagram
    participant A as Requester
    participant B as Responder

    A->>B: STATE_SYNC_REQUEST (known heads, hints)
    B->>A: STATE_SYNC_RESPONSE (active head, branch heads)
    A->>B: OBJECT_REQUEST (optional follow-up)
    B->>A: OBJECT_RESPONSE (optional follow-up)
```

```mermaid
stateDiagram-v2
    [*] --> InSync
    InSync --> ResyncRequested: STATE_SYNC_REQUEST
    ResyncRequested --> SyncMetadataReceived: STATE_SYNC_RESPONSE
    SyncMetadataReceived --> ObjectFetch: OBJECT_REQUEST
    ObjectFetch --> InSync: OBJECT_RESPONSE verified
```

Normative notes:
- Sync exchange SHOULD minimize unauthorized state disclosure (minimize leakage).
- This flow commonly pairs with alerts (e.g., `RESYNC_REQUIRED`) to trigger deterministic recovery.

Conformance reference: `conformance/extensions/OR_OBJECT_RESYNC_0.1.json`; fixtures: `fixtures/extensions/object_resync/`.

---

## 2.7 MCP Binding (BIND-MCP)

```mermaid
sequenceDiagram
    participant Agent
    participant Host as MCP Host / Runtime
    participant Tool as aicp.* MCP Tool

    Agent->>Host: tools/call
    Host->>Tool: aicp.sendMessage / aicp.getHead / aicp.getObject
    Tool-->>Host: tool result
    Host-->>Agent: JSON-RPC result
    Note over Host,Tool: AICP message envelope is preserved in tool arguments/results
```

```mermaid
stateDiagram-v2
    [*] --> BoundRequest: tools/call received
    BoundRequest --> AICPValidated: embedded message/case validated
    AICPValidated --> BoundResponse: tool result emitted
    BoundResponse --> [*]
```

Normative notes:
- Binding maps host-mediated tool invocations to AICP operations without changing Core message semantics.
- Embedded AICP messages MUST remain schema/hash consistent with canonical envelope expectations.

Conformance reference: `conformance/bindings/TB_MCP_0.1.json`; fixtures: `fixtures/bindings/mcp/`.


---

## 2.8 Resume / Reconnect (EXT-RESUME)

```mermaid
sequenceDiagram
    participant C as Client / Rejoining participant
    participant M as Mediator / Host

    C->>M: RESUME_REQUEST (resume_id, session_id, last_seen_message_hash)
    M->>C: RESUME_RESPONSE(status=OK | NEEDS_RESYNC | UNKNOWN_SESSION)
    Note over C,M: NEEDS_RESYNC may trigger ALERT(RESYNC_REQUIRED) and/or OBJECT_RESYNC flow
```

```mermaid
stateDiagram-v2
    [*] --> ResumeRequested: RESUME_REQUEST
    ResumeRequested --> InSync: RESUME_RESPONSE(status=OK)
    ResumeRequested --> ResyncNeeded: RESUME_RESPONSE(status=NEEDS_RESYNC)
    ResumeRequested --> UnknownSession: RESUME_RESPONSE(status=UNKNOWN_SESSION)
    ResyncNeeded --> InSync: OBJECT_RESYNC and/or retry completed
```

Normative notes:
- `RESUME_RESPONSE` MUST match request `resume_id` and `session_id`.
- `status=OK` implies `current_head_hash == last_seen_message_hash`.
- `status=NEEDS_RESYNC` implies `current_head_hash != last_seen_message_hash` and should drive deterministic recovery.

Conformance reference: `conformance/extensions/RS_RESUME_0.1.json`; fixtures: `fixtures/extensions/resume/`.

## Behavioral enforcement demo pointer
- Deterministic demo transcripts and threat-driven expected-fail cases are available under `demos/enforcement_behavioral/`.
- Canonical machine-verifiable fixtures are in `fixtures/demos/enforcement_behavioral/` and suite catalog `conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json`.

