# ADR: M65 registered-message surface completion

Status: accepted with canonical-authority correction.

## Decision

Positive message coverage is byte-backed. A registered message is covered only
when a positive case in an owning conformance suite references a fixture whose
parsed bytes contain that message. `expected_message_types` remains exact
sequence metadata and cannot manufacture coverage. The M65 completion gate
reuses `derive_message_surface()` and fails unless every registered message has
one mechanically derived owner, one canonical payload mapping, an owning suite,
and an actual positive fixture.

Existing orphan fixtures are preferred. M65 reuses five paths and strengthens
their generation or fixture construction where their old bytes were only
placeholders. Six genuinely new fixture paths provide the remaining coverage.
Generator-owned families are changed through their deterministic generators,
all of which expose `--check` for the M65 outputs. A coherent example lifecycle
does not by itself create a compatibility-rejecting wire rule.

The canonical runner continues to enforce the pre-existing normative identity
post-revoke, delegated-identity use-after-revoke, participant membership-gating,
Marketplace prior-RFW/award, execution, responsibility, and disputes rules. The
correction removes M65-only prior-local-state rules for migration, key and
binding revocation, arbitration, delegation revocation, participant leave,
policy attestation, and bid lifecycle. The current 0.1 RFCs do not impose those
exact relations, so example ordering is not promoted to a universal
compatibility requirement.

Protocol bytes remain stable: M65 does not change the message registry, payload
schemas, compatibility marks, Core/CAPNEG/profile/binding wire semantics, or
external target identities. Evidence TCK 1.8 is byte-frozen and remains
historical/strong-eligible. TCK 1.9 is also byte-frozen, but is historical and
strong-ineligible because it carried the split authority and over-specified M65
semantics. TCK 1.10 is current/strong-eligible with the corrected semantics,
report 2.2, trace v4, and the same six generalized targets.

Product-IUT v1 and `AICP-IUT-TCK-1.1.0` remain byte-for-byte frozen. Ordinary
suite reports, batch reports, and profile aggregation all use
`aicp_conformance_runner.run_suite` as their single compatibility-semantic
authority. The former additive `scripts/m65_extension_semantics.py` engine and
its follow-up validator are removed; no Make target relies on a second process
to invalidate a report after its compatibility mark is computed.

The reviewed per-message positive-coverage inventory and separate normative
semantic-change table are machine-checked in
[`M65_Message_Surface_Audit.json`](../process/M65_Message_Surface_Audit.json).
