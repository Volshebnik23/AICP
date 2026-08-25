# ADR: M65 registered-message surface completion

Status: accepted by the M65 executable corpus.

## Decision

Positive message coverage is byte-backed. A registered message is covered only
when a positive case in an owning conformance suite references a fixture whose
parsed bytes contain that message. `expected_message_types` remains exact
sequence metadata and cannot manufacture coverage. The M65 completion gate
reuses `derive_message_surface()` and fails unless every registered message has
one mechanically derived owner, one canonical payload mapping, an owning suite,
and an actual positive fixture.

Existing orphan fixtures are preferred. M65 reuses five paths and strengthens
their generation or semantics where their old bytes were only placeholders.
Six genuinely new fixture paths provide the remaining coverage. Generator-owned
families are changed through their deterministic generators, all of which expose
`--check` for the M65 outputs.

Presence alone is insufficient where the owning RFC already specifies a
relationship. Existing check families are strengthened for bid, participant,
identity-key, dispute-evidence, and delegated-binding relations; four narrow
checks cover migration-AID, arbitration, delegation-revoke, and
policy-attestation binding. Hash-valid mutation tests prove those relationships
are load-bearing. No new Facilitation state machine is introduced because the
current Facilitation RFC registers agenda/turn messages but does not define the
proposed agenda-update or turn-revoke relation as a MUST.

Protocol bytes remain stable: M65 does not change the message registry, payload
schemas, compatibility marks, Core/CAPNEG/profile/binding wire semantics, or
external target identities. Evidence TCK 1.8 is frozen byte-for-byte and remains
historical/strong-eligible; TCK 1.9 becomes current solely because the referenced
conformance corpus expanded.

Product-IUT v1 and `AICP-IUT-TCK-1.1.0` remain byte-for-byte frozen. The product
IUT bundle includes the ordinary conformance runner, so M65 lifecycle additions
execute through the additive `scripts/m65_extension_semantics.py` gate instead
of changing that frozen runner. `validate`, `message-surface-complete`, and
`conformance-ext` all invoke the gate, while hash-valid mutation tests exercise
the same combined base-plus-M65 path.

The reviewed per-message owner/schema/suite/candidate/check/negative/remediation
matrix is machine-checked in
[`M65_Message_Surface_Audit.json`](../process/M65_Message_Surface_Audit.json).
