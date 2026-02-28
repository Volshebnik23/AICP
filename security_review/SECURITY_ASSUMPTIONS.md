# Security Assumptions

- AICP provides verifiability primitives; mediated blocking guarantees apply only where an enforcement point actually exists.
- AICP does not guarantee model truthfulness; it provides provenance, policy-gating hooks, and auditability.
- Cryptographic strength depends on selected algorithms/profiles and correct implementation of hashing/signature verification.
- Full endpoint compromise, stolen keys, and compromised runtime environments are out-of-scope for protocol-only guarantees.
- LLM weight/model compromise is out-of-scope for protocol conformance.
- Privacy-sensitive details should not be emitted in clear text where codes suffice (especially alerts/verdict notes).
