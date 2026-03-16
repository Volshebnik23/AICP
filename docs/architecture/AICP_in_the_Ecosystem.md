# AICP in the Ecosystem

AICP is a **content-layer protocol** for governed agent-to-agent interactions. It sits between connectivity and application behavior: above transport/calling, below product/domain UX and execution systems.

## 1) Layered stack model

```text
[ Discovery / Directory Layer ]
[ Calling / Connectivity / Transport Layer ]
[ AICP Governed Conversation + Context Layer ]
[ Tool / API Integration Layer ]
[ External Trust / IAM / Commerce / Policy Engines ]
```

- Discovery/directory identifies where and how to reach parties.
- Calling/connectivity moves bytes/sessions and manages delivery semantics.
- AICP standardizes governed transcript semantics: contracts, policy/approval evidence, attestations, and hash-linked artifacts.
- Tool/API integration executes external actions and returns results/evidence.
- Trust/IAM/commerce/policy engines provide identity, authz, payment rails, and external assurance.

## 2) Responsibility boundaries (operational)

### Discovery / directory layer
- **Responsible for:** participant/service lookup, endpoint metadata, routing hints.
- **Not responsible for:** transcript policy/approval semantics, contract state progression.
- **Exposes to AICP:** identity/endpoint references and optional metadata.

### Calling / connectivity / transport layer
- **Responsible for:** channel/session establishment, retries, framing, reconnection behavior.
- **Not responsible for:** AICP contract/policy/evidence semantics.
- **Exposes to AICP:** delivery path/session context.

### AICP governed conversation + context layer
- **Responsible for:** transcript artifacts, policy/approval references, attestation linkage, compatibility/profile semantics.
- **Not responsible for:** discovery, transport internals, tool runtime execution, payment processing.
- **Expects from adjacent layers:** delivery path + optional externally issued identity/trust/policy artifacts.

### Tool / API integration layer
- **Responsible for:** external action invocation, side-effect execution, runtime API adaptation.
- **Not responsible for:** transcript governance by itself.
- **Exposes to AICP:** result references/hashes/attestations suitable for governed replay/audit.

### External trust / IAM / commerce / policy engines
- **Responsible for:** authn/authz, delegated identity lifecycle, trust status/revocation, checkout/payment rails, policy decision engines.
- **Not responsible for:** replacing AICP transcript semantics.
- **Exposes to AICP:** references/assertions/status/policy decisions with verifiable linkage.

## 3) Adjacent capability matrix (replace / complement / reference / orthogonal)

| Capability area | Typical adjacent systems | AICP relation | Why |
|---|---|---|---|
| Participant discovery | Directories, registries, broker catalogs | **Orthogonal / complements** | Discovery finds peers; AICP governs conversation artifacts after connection. |
| Session calling/connectivity | A2A-like calling, RPC/session protocols, HTTP/WS buses | **Complements** | Calling establishes path/session; AICP defines governed message/evidence semantics. |
| Tool invocation/runtime | MCP-like tool fabrics, execution runtimes | **Complements** | Tool execution remains external; AICP carries policy/approval/evidence context around outcomes. |
| Identity and delegation | OAuth/OIDC/IAM/delegated identity infra | **References / complements** | Identity authority remains external; AICP can carry linked identity lifecycle artifacts. |
| Commerce/checkout rails | Payment/checkout APIs and providers | **Orthogonal / references** | Checkout/payment rails stay external; AICP anchors declared/result evidence and governance context. |
| Policy computation | External policy engines (OPA/ABAC/RBAC/etc.) | **References / complements** | Decision engines are external; AICP transports requests/results/attestation evidence linkage. |
| Trust/attestation/status | PKI/issuer/trust-status/revocation infrastructure | **References / complements** | Trust fabric is external; AICP carries verifiable references and status-linked transcript artifacts. |
| Transport bindings | HTTP/WS/MCP/bus bindings | **Complements** | Bindings map channel behavior to interoperable expectations while AICP remains content-layer. |

## 4) Anti-misuse guardrails

AICP is **not**:
- a discovery protocol,
- a calling/connectivity runtime,
- a tool execution protocol,
- an IAM provider,
- a payment/checkout rail,
- a trust fabric implementation.

If your problem is purely one of those layers, AICP should not be your primary solution.

## 5) “Use AICP when…” (operational selection)

Use AICP when you need:
- governed multi-party agent transcripts with verifiable linkage,
- cross-vendor portability of contract/policy/approval/evidence semantics,
- mediation/enforcement-ready artifacts that can be externally replayed/audited,
- profile-based interoperability claims and deterministic conformance evidence.

You may not need AICP when:
- your need is discovery-only/calling-only,
- local single-agent orchestration has no governed multi-party evidence requirement,
- payment rail behavior itself is the main integration target.

## 6) Practical composition notes by boundary

- **Discovery → calling bootstrap:** discovery chooses peer/path; calling establishes session; AICP begins once governed transcript exchange starts.
- **Calling reconnect/degrade:** calling layer may reconnect/fail over; AICP continuity is maintained through transcript linkage and profile/conformance semantics.
- **Tool execution side effects:** side effects occur outside AICP; AICP should record policy/approval linkage and result evidence references.
- **IAM/delegation:** identity proofs remain external authority artifacts; AICP carries linked identity lifecycle/delegation evidence.
- **Commerce rails:** checkout/payment steps stay external; AICP records declaration/result/evidence anchors.
- **Trust/status:** revocation/status channels are adjacent trust infrastructure; AICP carries references and verification context.

## 7) Cross-links

- [A2A Integration Pattern (informative)](../adjacent/A2A_Integration_Pattern.md)
- [README.md](../../README.md)
- [START_HERE_IMPLEMENTERS.md](../../START_HERE_IMPLEMENTERS.md)
- [Protocol Adapter / Gateway guide](../guides/Protocol_Adapter_Gateway.md)
- [Profiles catalog](../profiles/AICP_Profiles.md)
- [Profile selection guide](../profiles/Profile_Selection_Guide.md)
- [Playbooks](../playbooks/)
- [Enforcement models](Enforcement_Models.md)
