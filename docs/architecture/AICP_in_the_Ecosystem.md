# AICP in the Ecosystem

AICP is a **content-layer protocol** for governed agent-to-agent interactions. It sits between connectivity and application behavior: above transport, below business/domain UX.

## 1) Layered stack model

```text
[ Discovery / Directory Layer ]
[ Calling / Connectivity / Transport Layer ]
[ AICP Governed Conversation + Context Layer ]
[ Tool / API Integration Layer ]
[ External Trust / IAM / Commerce / Policy Engines ]
```

- Discovery/directory identifies where or how to reach parties.
- Calling/connectivity moves bytes and sessions across networks.
- AICP standardizes transcript semantics, contracts, policies, attestations, and moderation-compatible message artifacts.
- Tool/API integration executes external actions and retrieves data.
- Trust/IAM/commerce/policy engines provide identity, authorization, payments, and external assurance services.

## 2) Responsibility boundaries

### Discovery / directory layer
- **Responsible for:** participant/service lookup, endpoint publication, routing metadata.
- **Not responsible for:** governed transcript semantics or AICP contract/policy logic.
- **Exposes to AICP:** resolved peer identities/endpoints, optional metadata.
- **AICP expectation:** optional adjacency only; AICP does not require a specific discovery system.

### Calling / connectivity / transport layer
- **Responsible for:** delivery channel semantics (HTTP/WS/bus/etc.), retries, framing, QoS at transport level.
- **Not responsible for:** AICP contract progression, policy evidence, attestation semantics.
- **Exposes to AICP:** message transport envelope and session connection context.
- **AICP expectation:** transport-agnostic; bindings map transport behavior into interoperable expectations.

### AICP governed conversation + context layer
- **Responsible for:** governed transcript artifacts, contract/policy references, attestations, hash-chain semantics, compatibility profiles.
- **Not responsible for:** network transport, discovery, direct tool execution, payment processing, identity authority issuance.
- **Exposes:** portable content-layer artifacts (messages/transcripts/evidence refs) for mediation/enforcement/replay.
- **Expects from adjacent layers:** delivery path, optional identity assertions, optional external trust and policy decisions.

### Tool / API integration layer
- **Responsible for:** invoking external APIs/tools, managing execution side effects, runtime integration.
- **Not responsible for:** AICP transcript governance semantics by itself.
- **Exposes to AICP:** referenced outputs, hashes, attestations, approvals/evidence anchors.
- **AICP expectation:** tool outcomes can be represented as governed artifacts for auditability.

### External trust / IAM / commerce / policy engines
- **Responsible for:** authn/authz, delegated identity lifecycle, checkout/payment rails, trust anchor/status infrastructure, external policy engines.
- **Not responsible for:** replacing AICP’s content-layer transcript model.
- **Exposes to AICP:** references, assertions, statuses, signed objects, policy decisions.
- **AICP expectation:** interoperable references and evidence, not a mandated single provider.

## 3) Adjacency matrix

| Adjacent system | AICP relation | Boundary summary |
|---|---|---|
| Discovery / directory services | Orthogonal / complements | Discovery finds participants; AICP governs conversation artifacts once connected. |
| A2A-like calling/connectivity | Complements | Connectivity establishes transport/session paths; AICP defines governed content semantics. |
| MCP-like tool integration | Complements | MCP-style tool invocation remains external; AICP captures governance/evidence around resulting actions. |
| OAuth/OIDC/delegated identity systems | References / complements | Identity and delegated auth are external; AICP can carry references and lifecycle artifacts. |
| External commerce/checkout protocols | Orthogonal / references | Checkout/payment rails stay external; AICP governs negotiation, approvals, and evidence context. |
| Transport bindings (HTTP/WS/MCP/bus) | Complements | Bindings map transport behavior to interoperable expectations; AICP stays content-layer. |
| Trust fabrics / attestation issuers / status infra | References / complements | Trust infrastructure is external; AICP carries references, attestations, and verifiable transcript semantics. |

## 4) Anti-misuse

AICP is **not**:
- DNS/discovery,
- transport/connectivity,
- tool catalog/tool execution protocol,
- IAM system,
- payment rail,
- hosted chat platform,
- trust fabric itself.

If your problem is only one of those layers, AICP alone is not the right primary solution.

## 5) Positive selection criteria

### Use AICP when…
- you need governed multi-party agent conversations with portable transcript semantics,
- contract/policy/evidence portability matters across vendors/systems,
- moderated delivery, attestation, and dispute-ready records are required,
- profile-based compatibility claims are part of your delivery criteria.

### You may not need AICP when…
- you only need single-agent local orchestration without governed cross-party context,
- your primary gap is discovery-only, transport-only, or payment-rail-only,
- no interoperable transcript or policy/evidence portability is required.

## 6) Cross-links

- [README.md](../../README.md)
- [START_HERE_IMPLEMENTERS.md](../../START_HERE_IMPLEMENTERS.md)
- [Protocol Adapter / Gateway guide](../guides/Protocol_Adapter_Gateway.md)
- [Profiles catalog](../profiles/AICP_Profiles.md)
- [Profile selection guide](../profiles/Profile_Selection_Guide.md)
- [Playbooks](../playbooks/)
- [Enforcement models](Enforcement_Models.md)
