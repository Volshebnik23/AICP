# M9.1 Internal Security Self-Review (Dry-Run)

## A) Purpose
This document is an internal dry-run of `security_review/REVIEW_CHECKLIST.md` to prepare for external security review.

## B) Method
Review method used in this dry-run:
1. Read protocol/security docs:
   - `security_review/THREAT_MODEL.md`
   - `security_review/SECURITY_ASSUMPTIONS.md`
   - `docs/core/AICP_Core_v0.1_Normative.md`
   - extension RFCs for CAPNEG, POLICY_EVAL, ENFORCEMENT, ALERTS, OBJECT_RESYNC, RESUME
2. Cross-checked executable artifacts:
   - conformance suite catalogs under `conformance/core/`, `conformance/extensions/`, `conformance/bindings/`
   - fixtures under `fixtures/` (including extension fixtures)
3. Ran repository checks as executable evidence:
   - `make validate`
   - `make conformance-all`
   - `pytest -q reference/python/tests`

Conformance suites and fixtures are treated as executable evidence of the behaviors they assert; anything not covered there is marked as doc-only or future hardening.

## C) Checklist walk-through

### Core
Covered by conformance:
- `conformance/core/CT_CORE_0.1.json` proves schema, hash-chain, message-hash, invariants, and signature/hash consistency checks.
What this proves:
- Baseline transcript integrity invariants are machine-checked.

Covered by docs only:
- Canonicalization edge-case rationale in normative docs; broad implementation pitfalls remain partly guidance-based.

Known gaps / future hardening ideas:
- Add explicit negative vectors for canonicalization edge cases (Unicode/number corner cases).

### CAPNEG
Covered by conformance:
- `conformance/extensions/CN_CAPNEG_0.1.json` validates sequence/payload correctness for negotiation flows.
What this proves:
- Negotiation message flow and payload contracts are deterministic.

Covered by docs only:
- Full downgrade-resistance strategy remains deployment+implementation guidance in RFC text.

Known gaps / future hardening ideas:
- Add negative tests focused on downgrade/capability spoofing attempts.

### POLICY_EVAL
Covered by conformance:
- `conformance/extensions/PE_POLICY_EVAL_0.1.json` validates payloads, reason-code registry checks, and context-hash consistency.
What this proves:
- Decision artifacts and reason-code references are machine-checkable.

Covered by docs only:
- Policy-engine trust model and ambiguity handling beyond encoded test cases.

Known gaps / future hardening ideas:
- Expand fixtures for borderline/inconclusive decisions and replayed decisions.

### ENFORCEMENT
Covered by conformance:
- `conformance/extensions/ENF_ENFORCEMENT_0.1.json` checks hard-gate delivery rules and sanction-code validation.
What this proves:
- Blocking-mode delivery gating is enforced by transcript checks.

Covered by docs only:
- Strong identity/auth channel assumptions for verdict origin remain deployment-side.

Known gaps / future hardening ideas:
- Add explicit spoofed-verdict negative fixtures beyond current gate checks.

### ALERTS
Covered by conformance:
- `conformance/extensions/AL_ALERTS_0.1.json` validates alert codes and recommended actions against registries.
What this proves:
- Operational alert taxonomy is registry-governed and machine-validatable.

Covered by docs only:
- Sensitive-data minimization in alert text/details is policy guidance.

Known gaps / future hardening ideas:
- Add fixture checks for overly verbose or sensitive alert payload examples (as policy/lint guidance).

### OBJECT_RESYNC
Covered by conformance:
- `conformance/extensions/OR_OBJECT_RESYNC_0.1.json` validates object/state sync payloads and object hash recomputation where present.
What this proves:
- Object resync message semantics and integrity checks are executable.

Covered by docs only:
- Leakage minimization and anti-amplification controls are mostly operational guidance.

Known gaps / future hardening ideas:
- Add larger-scale negative fixtures around abusive request cadence patterns.

### RESUME
Covered by conformance:
- `conformance/extensions/RS_RESUME_0.1.json` validates request/response matching and recommended actions registry checks.
What this proves:
- Resume handshake consistency and status/hash relationships are executable.

Covered by docs only:
- Session-probing and forced-resync loop prevention controls are platform-side hardening guidance.

Known gaps / future hardening ideas:
- Add explicit stress/loop scenarios as negative fixtures.

### Registries / Governance
Covered by conformance/tooling:
- `scripts/validate_registry.py` enforces required registry files and entry shape constraints.
What this proves:
- Registry artifacts are format-validated and linked to existing spec references.

Covered by docs only:
- Human governance workflows (deprecation/review policy rigor) remain process-driven.

Known gaps / future hardening ideas:
- Add machine-readable deprecation-policy checks where practical.

### Tooling / Conformance
Covered by conformance/tooling:
- Conformance runners plus `make validate`/`make conformance-all`/pytest checks exercise expected suite behavior.
What this proves:
- Current suite set is runnable and deterministic in repository workflows.

Covered by docs only:
- Security completeness boundaries (what tests do not cover) remain documented assumptions.

Known gaps / future hardening ideas:
- Add explicit “coverage limits” summary artifact tied to suite IDs.

## D) Findings summary
- Core: No concrete defect found in current repo artifacts; additional canonicalization negatives recommended.
- CAPNEG: No concrete defect found; downgrade-focused negatives recommended.
- POLICY_EVAL: No concrete defect found; ambiguity/replay cases can be expanded.
- ENFORCEMENT: No concrete defect found; spoofed-verdict negatives can be expanded.
- ALERTS: No concrete defect found; leakage-focused fixtures/guidance can be expanded.
- OBJECT_RESYNC: No concrete defect found; abuse-cadence negatives can be expanded.
- RESUME: No concrete defect found; loop/probing negatives can be expanded.
- Registries/Governance: No concrete defect found; stronger machine-enforced lifecycle checks possible.
- Tooling/Conformance: No concrete defect found; clearer machine-readable coverage-boundary reporting is possible.

No concrete bug requiring a new remediation-log entry was identified in this dry-run.

## E) Outcomes / next steps
- Add canonicalization-focused negative fixtures for edge-case encodings.
- Add targeted CAPNEG downgrade/spoofing negative conformance vectors.
- Add additional ENFORCEMENT/RESUME adversarial fixture scenarios (spoofing loops/probing loops).
- Add an explicit “coverage limits” section or artifact mapping test IDs to non-goals.
- Continue tightening alert/verdict privacy guidance with examples of code-first messaging.
