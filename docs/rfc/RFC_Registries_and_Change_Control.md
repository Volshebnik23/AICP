8. RFC: Registry and Change Control
AICP requires public, mirrorable registries and a transparent change-control process to prevent identifier collisions, enable interoperable extensions, and keep compatibility reproducible without dependence on any single SaaS platform.
8.1 Principles (normative)
•	Registries MUST be publicly accessible, versioned, and mirrorable.
•	Each registry entry MUST reference a stable normative specification and a compatibility range.
•	Registries SHOULD support status stages: experimental, stable, deprecated, withdrawn.
•	Changes MUST be reproducible: tracked as diffs with a changelog and semantic versioning.
8.2 Minimum registry set (v0.1)
•	Message Types Registry (non-Core message_type identifiers).
•	Policy Categories Registry (machine-checkable schemas and semantics).
•	Security and Crypto Profiles Registry (canonicalization/hash/sign/encryption profiles).
•	Object Hash Domains Registry (domain separation strings).
•	Transport Bindings Registry (canonical BIND-*-<ver>, deprecated aliases EXT-BIND-*).
•	Policy Languages and Bindings Registry (for EXT-POLICY-EVAL).
•	Policy Reason Codes Registry (stable reason identifiers).
•	Attestation Types and Identity Providers Registry (for identity lifecycle).
•	Security Events and Alert Categories Registry (for EXT-SECURITY-ALERT).
•	Dispute and Claim Types Registry (for challenges/claims).
8.3 Namespaces and collision avoidance (normative)
Identifiers SHOULD be namespaced using reverse-DNS (e.g., com.example.aicp.workflow.WORKFLOW_DECLARE). The namespace aicp.core.* is reserved and MUST NOT be used for third-party extensions.
8.4 Registry entry format (normative minimum)
Each registry entry MUST include: id, type, status, spec_ref, introduced_in, maintainer, security_considerations, and (optionally) conformance test references.
8.5 Registration and stability process (normative intent)
Registration MUST be open and auditable (e.g., public pull requests). To reach stable status, an entry SHOULD have at least one independent implementation and a minimal conformance suite. Crypto- and identity-affecting extensions SHOULD require security review.
8.6 Deprecation and withdrawal
Deprecated entries MUST provide a deprecation plan and recommended replacement. Withdrawn entries SHOULD be used only for severe security issues; history MUST remain available for audit reproducibility.
8.7 Publication integrity (recommended)
Registry releases SHOULD be signed and/or recorded in a transparency log (e.g., Sigstore) to provide tamper-evidence.
