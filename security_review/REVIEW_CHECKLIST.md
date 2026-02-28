# Security Review Checklist

## Core
- [ ] Canonicalization behavior is deterministic and documented.
- [ ] Message hash recomputation matches schema-bound payloads.
- [ ] Signature inputs and verification paths are unambiguous.
- [ ] Chain invariants (`prev_msg_hash`) are enforced.

## Error / Alerts
- [ ] Alert/error payloads avoid unnecessary sensitive leakage.
- [ ] Replay/idempotency expectations are explicit and tested.
- [ ] Recommended actions are registry-validated.

## CAPNEG
- [ ] Negotiation resists downgrade/capability spoofing patterns.

## POLICY_EVAL
- [ ] Decision artifacts bind clearly to evaluated context.
- [ ] Ambiguous/inconclusive outcomes are handled explicitly.

## ENFORCEMENT
- [ ] Hard-gate delivery semantics are correctly enforced.
- [ ] Verdict authenticity/spoofing concerns are addressed.

## OBJECT_RESYNC
- [ ] Object/state sync limits existence leakage.
- [ ] DoS/amplification considerations are documented.

## RESUME
- [ ] Resume does not leak session existence beyond intended semantics.
- [ ] Forced-resync loop and probing risks are considered.

## Registries
- [ ] Registry governance/change-control assumptions are explicit.

## Conformance tooling
- [ ] Coverage boundaries are clear (what tests verify vs what remains deployment-side).
- [ ] Failure modes are deterministic and diagnosable.

References:
- `docs/core/AICP_Core_v0.1_Normative.md`
- `docs/rfc/RFC_Registries_and_Change_Control.md`
- `docs/extensions/RFC_EXT_ENFORCEMENT.md`
- `docs/extensions/RFC_EXT_ALERTS.md`
- `docs/extensions/RFC_EXT_OBJECT_RESYNC.md`
- `docs/extensions/RFC_EXT_RESUME.md`
- `conformance/`
