# AICP Threat Model (Protocol Scope)

## 1) Scope and non-scope
Scope:
- AICP protocol artifacts: message formats, hash chain semantics, signatures, registries, and conformance behavior.

Non-scope:
- Hosted platform operations, centralized chat/enforcer products, IAM replacement, endpoint hardening internals.

## 2) Assets
- Transcript integrity (hash-chain consistency).
- Identity authenticity (signature/key binding correctness).
- Policy/enforcement decision integrity.
- Auditability and reproducibility of conformance outcomes.

## 3) Actors
- Honest participant.
- Buggy implementation.
- Malicious participant.
- Malicious mediator.
- Passive/active observer.

## 4) Trust boundaries
- Mediator-controlled channels are not equivalent to end-to-end trust.
- AICP provides verifiable evidence structures; deployment trust and isolation remain platform concerns.

## 5) Attack surfaces
- Canonicalization pitfalls (Unicode normalization, numeric edge cases, object ordering assumptions).
- Hash-chain manipulation, replay, and truncation.
- Spoofed enforcement verdicts or spoofed operational alerts.
- CAPNEG downgrade or capability spoofing.
- OBJECT_RESYNC leakage/amplification or DoS patterns.
- RESUME abuse (session probing, amplification, forced resync loops).

## 6) Mitigations: AICP vs platform responsibilities
AICP provides:
- Hash-chain and message-hash verification semantics.
- Registry-governed IDs/codes for interoperable validation.
- Conformance suites for repeatable behavior checks.

Platforms should additionally provide (deployment controls):
- Transport/session hardening, abuse-rate controls, anti-amplification guardrails.
- Identity lifecycle operations and secure key custody.
- Operational monitoring, alerting policy, and incident response procedures.

## 7) Residual risks and recommended platform controls
Residual protocol-adjacent risks:
- Valid-but-malicious inputs that are syntactically correct.
- Privacy leakage via overly verbose operational messages.

Recommended platform-side controls (optional deployment controls):
- Strict rate limiting and replay detection.
- Minimize sensitive payload details; prefer machine-readable codes.
- Segmented trust zones for mediator and policy components.
