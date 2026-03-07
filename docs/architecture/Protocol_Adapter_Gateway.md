# Protocol Adapter / Gateway in the Architecture Stack

This architecture note places the adapter/gateway pattern in the broader ecosystem and enforcement model.

Primary implementation guide: [docs/guides/Protocol_Adapter_Gateway.md](../guides/Protocol_Adapter_Gateway.md).

## Where adapter/gateway fits

An adapter/gateway is the integration layer between:
- existing platform protocols/models, and
- AICP content-layer governed artifacts.

It does not replace transport, IAM, discovery, or trust infrastructure. It maps between them while preserving enough envelope/evidence data for auditability.

## Relationship to ecosystem and enforcement docs

- Ecosystem boundaries: [AICP in the Ecosystem](AICP_in_the_Ecosystem.md)
- Enforcement model choices: [Enforcement Models](Enforcement_Models.md)
- Profile selection for product context: [Profile Selection Guide](../profiles/Profile_Selection_Guide.md)
- Session/topology choices: [Session Topologies](../playbooks/Session_Topologies.md)

## Minimum architecture expectations

For merge-safe onboarding, adapter/gateway deployments should:
- validate schema at ingress,
- preserve transcript hash/evidence-critical fields,
- maintain immutable storage of full source envelopes,
- map policy/verdict signals without losing provenance,
- align with selected profile conformance expectations.
