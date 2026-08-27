# AICP Threat Model (Protocol Scope)

The canonical per-threat status, evidence, deferral rationale, and residual boundary are in
[`threat_coverage.json`](threat_coverage.json). This document describes the model; it does not
override that manifest.

## Scope

AICP protocol scope includes registered messages and schemas, transcript hashing and
signatures, exact-contract agreement, profile negotiation and composition, enforcement and
alerts, object resynchronization and resume flows, identity delegation, live-transport
evidence, pairwise clean-room evidence, and the tooling that evaluates those artifacts.

Hosted service operations, endpoint hardening, model behavior, secure key custody, tenant
isolation, traffic shaping, and the honesty or policy correctness of participants remain
deployment or ecosystem responsibilities unless a specific protocol-observable invariant is
defined and tested.

## Protected assets

- canonical transcript and hash-chain integrity;
- signer, delegated-identity, and enforcement-authority binding;
- exact proposal, contract, profile, context, verdict, and object references;
- deterministic conformance and evidence-release interpretation;
- confidentiality of secrets excluded from public evidence schemas;
- accurate separation of internal evidence, external evidence, and adoption claims.

## Adversaries and failure modes

The model includes buggy or malicious participants, mediators, enforcers, evidence producers,
and observers. Relevant failures include replay or truncation, stale/future/cross-contract
substitution, negotiation rollback, profile-composition downgrade, spoofed or mis-targeted
verdicts, unauthorized enforcement, resync existence leakage or amplification, resume
probing/loops, misleading evidence provenance, and accidental secret publication.

## Trust boundaries

- A mediated channel is not automatically end-to-end trusted.
- A valid signature proves control of the corresponding signing key under the selected
  profile; it does not prove participant honesty, authority, or uncompromised key custody.
- Conformance demonstrates the named executable behavior only. It is not certification,
  product assurance, ecosystem adoption, or an independent review.
- Public evidence schemas exclude known test-control secret fields, but arbitrary secret
  classification and redaction remain an operator responsibility.
- Positive OBJECT_RESYNC statuses expose protocol mechanisms; they do not establish a
  universal size, rate, authorization, or redaction policy.

## Mitigation classes

Protocol-observable mitigations are linked from covered manifest rows to exact suites, check
IDs, case IDs, and fixtures. Deployment and ecosystem risks are deferred with an explicit
class and rationale. Operator guidance appears in
[`OPS_HARDENING_GUIDE.md`](OPS_HARDENING_GUIDE.md) and is not converted into a protocol MUST.

The generated [`COVERAGE_MAP.md`](COVERAGE_MAP.md) is the review index for the complete set of
36 components and their residual boundaries.
