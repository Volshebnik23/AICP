# Security Assumptions and Assurance Boundaries

- AICP is a protocol and evidence standard, not a hosted identity, enforcement, certificate,
  storage, or anti-abuse service.
- Verifiability depends on using the registered schemas, canonicalization rules, hash domains,
  release authorities, and checks named by the applicable profile.
- Mediated blocking applies only when a conforming enforcement point exists on the delivery
  path and the selected contract/profile actually requires that behavior.
- Signatures and delegated-identity chains depend on correct key binding, algorithm selection,
  verification, lifecycle handling, and key custody. Endpoint compromise and stolen keys are
  outside protocol-only assurance.
- Exact-contract and profile checks bind transcript declarations; they do not establish the
  truthfulness, competence, intent, or policy correctness of a participant.
- OBJECT_RESYNC status, size, redaction, and authorization fields are interoperable mechanisms.
  AICP does not define one universal deployment cap, rate limit, classifier, or access policy.
- Public evidence schemas reject known test-control secret property names. Identification of
  arbitrary secrets in otherwise permitted application data remains a producer/operator duty.
- Deterministic fixtures cover their declared transcript-level behavior. They do not model
  wall-clock abuse volume, distributed denial of service, tenant isolation, or runtime supply
  chain compromise.
- Internal conformance and repository-generated evidence are not independent review evidence.
  The canonical manifest records `external_independent_review_completed: false` until a real
  artifact satisfies [`external_reviews/README.md`](external_reviews/README.md).
- Pairwise clean-room reference execution is not external adoption. The canonical manifest
  records zero externally demonstrated pairwise relations at the M67 boundary.
- Privacy-sensitive free text and application payloads should be minimized and redacted by
  deployments; registry-governed codes reduce ambiguity but cannot classify every secret.

Per-component evidence and residual risk are canonical in
[`threat_coverage.json`](threat_coverage.json).
