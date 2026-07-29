# EXT-CAPNEG v0.2 — canonical multi-profile composition

Status: experimental. Extension ID: `EXT-CAPNEG`. Compatibility mark:
`AICP-EXT-CAPNEG-0.2`.

This document defines the second, separately selected CAPNEG protocol surface.
The stable v0.1 document, schema, fixtures, suite, behavior, and
`AICP-EXT-CAPNEG-0.1` mark are unchanged.

## Version selection

The registered message IDs remain `CAPABILITIES_DECLARE`, `CAPABILITIES_PROPOSE`,
`CAPABILITIES_ACCEPT`, and `CAPABILITIES_REJECT`. Every v0.2 payload MUST contain
`"capneg_version": "0.2"`. That field selects
`schemas/extensions/ext-capneg-v0.2-payloads.schema.json`. A CAPNEG payload without
the field is exclusively v0.1 and MUST NOT be interpreted as v0.2.

CAPNEG v0.2 uses the permissive Core v0.1 envelope as its bootstrap. A selected
profile MUST resolve to `conformance/core/CT_CORE_0.1.json`. A registered profile
requiring another Core suite is recognized and rejected with
`CAPNEG_CORE_FAMILY_UNSUPPORTED`.

## Profile composition

`aicp.profile_composition.v1` has this exact shape:

```json
{
  "composition_version": "aicp.profile_composition.v1",
  "profiles": [
    {
      "profile_id": "AICP-MEDIATED-BLOCKING",
      "profile_version": "0.1"
    },
    {
      "profile_id": "AICP-RESUMABLE-SESSIONS",
      "profile_version": "0.1"
    }
  ]
}
```

`profiles` MUST contain between one and sixteen exact registered references. It MUST
be unique and lexicographically sorted by exact `profile_id`, then exact
`profile_version`. A composition MUST NOT contain multiple versions of one
`profile_id`, profiles from different Core suites, a non-negotiable Core family, a
strict required-suite subset together with its covering profile, or more than one
member of an explicit max-one group.

The generator-owned `registry/aicp_profile_composition_rules.json` is authoritative
for exact Core suites, required suites, extension/crypto/policy unions, component mark
identities, strict-subset relations, and explicit exclusive groups. A resolver MUST
fail; it MUST NOT sort a non-canonical wire value silently, remove redundant members,
or choose a newer profile version.

### Hash binding

The exact composition hash is:

```text
object_hash("capneg.profile_composition", profile_composition)
```

The complete result continues to use:

```text
object_hash("capneg.negotiation_result", negotiation_result)
```

Both use the existing AICP canonicalization and SHA-256 object-hash construction.

## Capability declaration

The required v0.2 declaration fields are:

```json
{
  "capneg_version": "0.2",
  "capabilities_id": "cap-a-1",
  "party_id": "agent:A",
  "supported_crypto_profiles": [],
  "supported_privacy_modes": ["standard"],
  "supported_aicp_profiles": [
    {"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "0.1"}
  ]
}
```

Optional fields are `required_crypto_profiles`, `required_aicp_profiles`,
`supported_extensions`, `supported_policy_categories`, `limits`, `bindings`,
`languages`, `supported_channel_properties`, and `supersedes_capabilities_id`.
The `party_id` MUST equal the envelope sender. Hashed arrays MUST be unique and
canonical. Required product and crypto profiles MUST be subsets of their supported
sets. A supersession MUST bind the latest prior declaration from that party; stale,
forked, or duplicate declarations MUST NOT support a proposal.

## Negotiation result and proposal

The exact required result fields are:

```json
{
  "negotiation_id": "neg-1",
  "proposal_revision": 1,
  "session_id": "session-1",
  "contract_id": "contract-1",
  "participants": ["agent:A", "agent:B"],
  "declaration_bindings": [
    {
      "party_id": "agent:A",
      "capabilities_id": "cap-a-1",
      "declaration_message_id": "m1",
      "declaration_message_hash": "sha256:..."
    }
  ],
  "selected": {
    "crypto_profiles": [],
    "privacy_mode": "standard",
    "profile_composition": {
      "composition_version": "aicp.profile_composition.v1",
      "profiles": [
        {"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "0.1"}
      ]
    },
    "profile_composition_hash": "sha256:...",
    "required_extensions": ["EXT-CAPNEG", "EXT-ENFORCEMENT", "EXT-POLICY-EVAL"],
    "required_policy_categories": []
  }
}
```

`participants` and bindings MUST be unique, canonical, and exact set-equals. Each
binding MUST identify that participant's latest valid declaration. Every participant
MUST support every selected profile and the complete resolved extension, crypto,
policy, privacy, binding, channel, and limit selection. Every participant's required
profiles MUST be present. `selected.crypto_profiles` MUST also contain every exact
identifier in every participant's `required_crypto_profiles`; profile-derived crypto
requirements and participant requirements are independent minimums. Composition and
result hashes MUST be recomputed.

A proposal contains `capneg_version`, `proposal_revision`, `negotiation_result`, and
`negotiation_result_hash`. Revision one starts a negotiation. Each later revision
increments by exactly one and MUST bind the immediately prior proposal message ID and
hash. A fully accepted negotiation is immutable. Changing it requires a new
`negotiation_id` and `supersedes_negotiation_id`.

A new negotiation may supersede an accepted negotiation only when the old result is
still accepted and unsuperseded and the session, contract, and participant set are
exactly equal. Merely proposing the link does not supersede anything. The old result
becomes `SUPERSEDED` only after every participant accepts the successor; cross-context,
unknown, non-accepted, participant-substitution, and double-fork supersessions fail.

## Accept and reject

An acceptance contains:

```json
{
  "capneg_version": "0.2",
  "negotiation_id": "neg-1",
  "proposal_revision": 1,
  "proposal_message_id": "m3",
  "proposal_message_hash": "sha256:...",
  "negotiation_result_hash": "sha256:...",
  "accepted": true
}
```

Every participant, including the proposer, MUST emit one exact acceptance of the
current proposal. An exact duplicate replay is safe and never counts twice. Unknown,
future, superseded, retargeted, wrong-result, and post-rejection acceptances fail.
Partial acceptance is not acceptance.

Before either decision is applied, its envelope `session_id` and `contract_id` MUST
equal the bound negotiation result, and every declaration binding MUST still identify
that participant's latest valid declaration. A newer valid declaration makes the old
proposal stale until a contiguous replacement revision binds the new declarations.
Replay safety is checked only after the replay message itself passes envelope, chain,
hash, signature, sender, proposal, result, context, and decision-consistency checks.

A rejection contains the same proposal binding plus a registered `reason_code`.
`reason_detail`, canonical `alternative_profile_compositions`, and
`alternative_constraints` are optional. A rejection blocks that revision. A valid
later revision clears prior-revision acceptance and rejection sets. No participant may
advance a rejected revision toward acceptance. Exact rejection replay is idempotent;
changed reason, alternatives, constraints, or proposal binding is a retargeted replay.

`alternative_constraints`, when present, is the closed
`aicp.capneg.alternative_constraints.v1` object defined by the v0.2 schema. It permits
only the documented profile, crypto, privacy, extension, policy, limit, binding, and
channel fields. Alternative compositions remain canonical compositions, MUST be
supported by the rejecting participant, and MUST preserve that participant's required
profile and crypto minimums.

## Authenticated Base rule

If the composition contains `AICP-AUTHENTICATED-BASE@0.1`, selected crypto MUST
contain `aicp.crypto.ed25519.v1`, every declaration MUST support it, and every
participant acceptance MUST carry a valid Ed25519 sender signature. Missing verifier
support degrades the suite and suppresses its mark. For other compositions signatures
are optional, but every signature entry present on any declaration, proposal,
acceptance, rejection, CAPNEG-bound contract, or projection message MUST validate its
structure, exact message-hash binding, signer/key identity, `kid`, and cryptographic
bytes. One valid entry never excuses another invalid entry.

## Contract binding and projection

A Core v0.1 Context Contract may use `contract.ext.capneg_v2`:

```json
{
  "capneg_version": "0.2",
  "negotiation_id": "neg-1",
  "negotiation_result_hash": "sha256:...",
  "profile_composition": {
    "composition_version": "aicp.profile_composition.v1",
    "profiles": [
      {"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "0.1"}
    ]
  },
  "profile_composition_hash": "sha256:..."
}
```

The containing `CONTRACT_PROPOSE` payload and contract object MUST first satisfy the
frozen Core v0.1 schemas, and the envelope and object contract IDs MUST be equal. The
referenced result MUST then be fully accepted, current, session/contract matched, and
byte-for-byte equal after canonicalization. Projection
`aicp.session_state_projection.v2` carries the same canonical selected profiles,
composition hash, accepted-result hash, and consistent active extensions. Projection
v1 is unchanged. Projection v2 resolves `as_of_message_hash` to one exact prior
transcript message, reduces only that prefix, and compares against the state at that
point. A branch-head-only or unknown hash is insufficient.

## State machine and validity barrier

The deterministic states are `COLLECTING_DECLARATIONS`, `PROPOSED`,
`PARTIALLY_ACCEPTED`, `REJECTED`, `REVISION_PROPOSED`, `ACCEPTED`, and
`SUPERSEDED`. Schema-invalid, identity-invalid, chain-invalid, message-hash-invalid,
signature-invalid, or composition-invalid messages MUST NOT mutate state.

The conformance validity barrier records every failure as
`{code, message_index, message_id, detail}` and compares reviewed expectations as
`{code, message_index, message_id, exact_count}` without deduplication. Fixture
messages/hashes/signatures are generated independently from the reviewed expectation
catalog; production reducers and projection validators do not generate their own
expected results.

## Security and evidence boundary

Implementations MUST fail profile omission, downgrade, unknown-profile injection,
mixed Core families, duplicate/reordered sets, registry substitution, stale
declarations, supersession forks, revision rollback, acceptance replay retargeting,
partial acceptance, hash substitution, contract/projection substitution, missing
Authenticated Base crypto, invalid signatures, and compositions above the bounded
maximum.

An internal CAPNEG v0.2 report proves only repository fixture/resolver agreement and
the exact transcript transition. It does not award component marks or prove external
implementation support, participant identity or authority, truthful declarations,
component conformance, pairwise interoperability, policy correctness, transport
security, or consensus outside the transcript. External composition claims remain
fail-closed pending M62.
