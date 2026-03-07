# AICP Standard Overview

AICP is a **content-layer** protocol for governed agent-to-agent interaction with portable transcript semantics.

For canonical term definitions, use [docs/GLOSSARY.md](../GLOSSARY.md).

## 1) What AICP is

- A transport-independent content-layer protocol for governed conversation/context artifacts.
- A way to represent contract, policy, attestation, and evidence-linked transcript semantics.
- A profile-driven interoperability framework backed by conformance artifacts.

## 2) What AICP is not

AICP is not:
- a discovery/directory system,
- a transport/calling protocol,
- a tool execution/catalog protocol,
- an IAM system,
- a payment rail,
- a hosted platform,
- the trust fabric itself.

## 3) What AICP standardizes

- Core message and transcript semantics.
- Contract/policy/attestation-compatible content artifacts.
- Hash/canonicalization-based verifiability.
- Conformance/profile evidence paths.
- Extension/binding compatibility framing.

## 4) What remains external

- Discovery and endpoint resolution.
- Transport/session connectivity runtime.
- Tool runtime execution stacks.
- IAM provider internals and delegated auth infrastructure.
- Commerce checkout/payment rails.
- Trust anchor issuance/status networks.

## 5) AICP in the ecosystem (summary)

AICP should be treated as the governed content layer in a larger system stack. It complements adjacent systems rather than replacing them.

See: [docs/architecture/AICP_in_the_Ecosystem.md](../architecture/AICP_in_the_Ecosystem.md).

## 6) Typical deployment modes

### Hosted brand reception
Brand host mediates incoming agent/client conversations with governed policies and moderation.

### Foreign agent joining my session
External participants join a host-owned transcript with scoped context sharing.

### Mediated multi-agent enterprise workflow
Multiple internal/partner agents coordinate under policy-gated orchestration and evidence trails.

### External protocol bridge pattern
External systems execute actions outside AICP while adapter/gateway layers anchor evidence into AICP transcripts.

## 7) Why content-layer matters

Content-layer standardization gives multi-agent systems portable governance:
- **Shared contract model** for participants and purpose.
- **Goal/roles/policies** as explicit machine-checkable context.
- **Attestations** for action/result/authority evidence.
- **Moderated delivery hooks** for host/enforcer control paths.
- **Portable transcript/context semantics** across products and deployments.

## Next steps

- [Start Here for Implementers](../../START_HERE_IMPLEMENTERS.md)
- [Profile Selection Guide](../profiles/Profile_Selection_Guide.md)
- [Playbooks](../playbooks/)
- [Enforcement Models](../architecture/Enforcement_Models.md)
