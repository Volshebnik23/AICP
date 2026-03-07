# Enforcement Models for AICP

AICP is a **content-layer protocol** designed to be enforcement-compatible. This document explains architecture choices for enforcement without changing protocol scope.

## 1) Why enforcement is central to AICP

AICP sessions often involve constrained actions, policy conditions, and accountability requirements. Enforcement is central because AICP artifacts (contracts, policy refs, attestations, transcript hashes, and moderation/verdict records) are meant to be externally checkable.

## 2) What AICP standardizes in enforcement-compatible terms

AICP standardizes content-layer artifacts that enforcement systems can consume:
- contract/policy references in governed session artifacts,
- evidence references and hash-linked transcript context,
- verdict/sanction-compatible artifacts (for applicable profiles/extensions),
- replayable transcript semantics for audit/dispute handling,
- links to escalation/dispute pathways where supported by extensions.

## 3) What AICP does NOT standardize

AICP does **not** standardize:
- the trust fabric itself,
- consensus engines,
- attester discovery,
- universal key/status infrastructure,
- a mandatory hosting model.

Those remain external infrastructure choices.

## 4) Enforcement topology models

### A) Host-owned enforcement
- **Who produces verdicts:** host/mediator-controlled enforcement stack.
- **Where trust comes from:** operator trust + published policies + audit evidence.
- **What protocol needs to see:** policy refs, verdict artifacts, evidence refs, transcript linkage.
- **Trade-offs:** simpler operations; stronger dependence on single operator trust.
- **Adjacent infrastructure:** IAM/policy engine/monitoring selected by host.
- **Best fit:** brand-owned receptions, managed support desks, centralized enterprise control.

### B) Third-party enforcement
- **Who produces verdicts:** external enforcement provider.
- **Where trust comes from:** provider assurances + contractually defined evidence formats.
- **What protocol needs to see:** provider-attested verdict/evidence linkage into transcript.
- **Trade-offs:** offloaded operations; dependency on provider availability/governance.
- **Adjacent infrastructure:** provider integration, status channels, trust anchors.
- **Best fit:** teams outsourcing moderation/compliance decisions.

### C) Federated enforcement
- **Who produces verdicts:** multiple organizations across trust boundaries.
- **Where trust comes from:** federation agreements, shared policy contracts, cross-org attestations.
- **What protocol needs to see:** interoperable verdict/evidence records from multiple domains.
- **Trade-offs:** stronger multi-party legitimacy; higher coordination complexity.
- **Adjacent infrastructure:** federation identity/trust status exchanges.
- **Best fit:** cross-enterprise or consortium workflows.

### D) Distributed / quorum enforcement
- **Who produces verdicts:** quorum of independent enforcers/authorities.
- **Where trust comes from:** quorum policy and threshold rules.
- **What protocol needs to see:** multiple attestations/verdict artifacts linked to the same governed context.
- **Trade-offs:** stronger anti-single-point-failure trust; latency/operational overhead.
- **Adjacent infrastructure:** signer coordination, key lifecycle, status/revocation channels.
- **Best fit:** high-assurance or adversarial environments.

### E) Ledger-anchored / blockchain-backed enforcement (implementation option)
- **Who produces verdicts:** host/federation/quorum models may anchor evidence to ledgers.
- **Where trust comes from:** ledger integrity + off-ledger policy/process controls.
- **What protocol needs to see:** anchored references/hashes, not mandatory chain-specific semantics.
- **Trade-offs:** stronger tamper-evidence claims; higher integration and privacy considerations.
- **Adjacent infrastructure:** chain adapters, key ops, anchoring/retrieval services.
- **Best fit:** environments requiring independent timestamping/public verifiability.

## 5) Verdict interoperability

When multiple verdict sources exist:
- represent each verdict source as explicit artifacts tied to shared transcript/evidence refs,
- preserve source identity and policy basis in the recorded artifact,
- document conflict situations (divergent verdicts, stale status, missing evidence) in-session,
- use dispute/escalation artifacts where available,
- keep evidence portable so independent reviewers can replay decisions.

Portable evidence matters because enforcement credibility depends on third-party verifiability, not only operator claims.

## 6) Cross-links

- IAM bridge milestone context: [ROADMAP.md](../../ROADMAP.md) (M28)
- Security guidance: [security_review/OPS_HARDENING_GUIDE.md](../../security_review/OPS_HARDENING_GUIDE.md)
- Error/recovery operations: [docs/ops/ERROR_AND_RECOVERY.md](../ops/ERROR_AND_RECOVERY.md)
- Profile selection guide: [docs/profiles/Profile_Selection_Guide.md](../profiles/Profile_Selection_Guide.md)
- Session topology cookbook: [docs/playbooks/Session_Topologies.md](../playbooks/Session_Topologies.md)
- Ecosystem positioning: [docs/architecture/AICP_in_the_Ecosystem.md](AICP_in_the_Ecosystem.md)
- Adapter placement: [docs/architecture/Protocol_Adapter_Gateway.md](Protocol_Adapter_Gateway.md)
