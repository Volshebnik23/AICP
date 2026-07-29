# ADR: EXT-CAPNEG v0.2 profile composition

Status: accepted for M61.

## Decision

EXT-CAPNEG keeps one registered extension identity and two explicit protocol versions.
The existing stable v0.1 surface is frozen. A payload without `capneg_version` continues
to use the v0.1 schema and single `selected.aicp_profile`. A payload with
`"capneg_version": "0.2"` selects the separate experimental v0.2 schema and semantics
for the same four registered CAPNEG message IDs.

CAPNEG v0.2 negotiates a non-empty canonical mathematical set of exact registered
profile references. Its serialized `profiles` array is unique and sorted by exact
`profile_id`, then exact `profile_version`; array position has no precedence meaning.
The set is hashed with `object_hash("capneg.profile_composition", composition)`.

The composition-rules registry is generated from the product-profile registry and
all profile conformance catalogs. M61 allows only profiles whose catalog resolves to
`CT-CORE-0.1`. Registered `AICP-BASE@0.2` is therefore recognized but rejected with
`CAPNEG_CORE_FAMILY_UNSUPPORTED`. Existing component profile suites and marks remain
unchanged; CAPNEG v0.2 evidence is additive and awards only
`AICP-EXT-CAPNEG-0.2`.

Every proposal binds the latest declaration of every exact participant and one exact
proposal revision. Every participant, including the proposer, must explicitly accept
that revision. A full acceptance is immutable under its negotiation ID. A changed
accepted composition requires a new negotiation ID with an explicit supersession
link.

## Rejected alternatives

- New message IDs were rejected because the payload version is sufficient to select
  a separate schema while preserving registry identity.
- Ordered precedence, a `primary_profile`, and implicit strongest-profile selection
  were rejected because they make set identity dependent on position.
- Dynamic composition profile IDs and aggregate product marks were rejected because
  a composition does not replace component conformance evidence.
- Automatic removal of redundant profiles, newest-version selection, arbitrary
  overlap inference, and a general constraint solver were rejected because they hide
  proposer intent and make results non-auditable.
- Core v0.2 composition bootstrap was rejected for M61 because the frozen
  experimental Core v0.2 message surface has no generic extension bootstrap.
- Replacing component `CN_CAPNEG_0.1` requirements with the v0.2 suite was rejected
  because it would silently change existing product-profile marks.

## Consequences

CAPNEG v0.1 remains backward compatible. CAPNEG v0.2 provides internal, deterministic
composition evidence, contract binding, and portable projection v2. It does not prove
real participant identity, authority, truthfulness of capability claims, component
implementation conformance, external interoperability, policy correctness, or
transport security. Generalized external composition evidence remains an M62 concern.
