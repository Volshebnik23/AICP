# Session-state projection v2

Status: experimental, internal evidence in M61.

Projection v2 is a separately selected `STATE_SYNC_RESPONSE` payload capability for a
fully accepted EXT-CAPNEG v0.2 result. It does not modify strict projection v1 or make v1
composition-aware.

The exact projection object is validated by
`schemas/extensions/session-state-projection-v2.schema.json`. It carries:

- `projection_version`: exactly `aicp.session_state_projection.v2`;
- the Core v0.1 `session_id` and `contract_id`;
- canonical `selected_aicp_profiles`;
- exact `profile_composition_hash`;
- exact `accepted_negotiation_result_hash`;
- the derived active-extension set;
- transcript-visible state/evidence references.

The `STATE_SYNC_RESPONSE` envelope selects this schema through the capability selector
`aicp.session_state_projection` / `v2`. The canonical message-registry mapping remains the
stable v1 variant.

A verifier must reject a projection whose set, composition hash, accepted-result hash, or
active extensions differ from the fully accepted negotiation state. The accepted-result
hash provides the link to the participant/revision-bound CAPNEG result. A stale or
substituted result is not portable state evidence.

`as_of_message_hash` MUST identify exactly one message earlier in the observed transcript.
The verifier locates that index, applies the same message-validity barrier to the prefix,
reduces only `transcript[0 : as_of_index + 1]`, and compares the projection with the fully
accepted CAPNEG state at that point. Acceptance or supersession that occurs later in the
transcript cannot leak backward. Unknown/future hashes and hashes supplied only as an
unproved `branch_heads` entry fail; v2 defines no separate branch-head proof mechanism.

`conformance/extensions/OR_SESSION_STATE_PROJECTION_V2.json` executes four positive and nine
negative cases from `fixtures/extensions/object_resync/state_projection_v2/`, including
declaration, proposal, partial-acceptance, exact-final-acceptance, and supersession
boundaries. A complete,
non-degraded internal run emits
`AICP-Evidence-SESSION-STATE-PROJECTION-v2`. The mark is internal capability evidence, not
an ordinary product-profile mark or independent external proof. Generalized external
capability/composition evidence remains M62 work.

The projection hash proves the integrity of the supplied projection bytes. It does not
prove real participant identity, authority, truthful capability declarations, external
component conformance, consensus outside the observed transcript, policy correctness, or
transport security.
