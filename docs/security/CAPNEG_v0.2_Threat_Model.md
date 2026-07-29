# CAPNEG v0.2 threat model and executable coverage

This M61 threat note covers the experimental multi-profile negotiation surface. The
normative state and hash rules are in `docs/extensions/RFC_EXT_CAPNEG_v0.2.md`; executable
cases are in `fixtures/extensions/capneg_v0_2/negative_cases.json`.

| Threat | Required rejection or invariant | Executable cases |
|---|---|---|
| Profile-set downgrade or omission | Every required profile/extension/crypto/policy category is present; every selected profile is supported by every participant | N12–N16 |
| Unsupported profile or Core-family injection | Profiles are exact registered pairs in the supported Core v0.1 family | N04, N06, N07 |
| Duplicate/reordered ambiguity or same-family substitution | Set is non-empty, unique, canonically sorted, and has at most one version per profile ID | N01–N05 |
| Redundant/exclusive set ambiguity | Strict requirement subsets and exclusive policy-semantic dialects fail | N08–N11 |
| Stale or forked capability declarations | Sender equals party; one latest declaration per party; supersession is exact; proposal binds all latest IDs/hashes | N23–N29 |
| Proposal rollback or acceptance retargeting | Revisions are contiguous and predecessor-bound; accepts target the current proposal/result | N30–N35, N39, N40 |
| Partial/replayed/conflicting acceptance | Every bound participant accepts exactly once; reject/accept conflict and duplicate counting fail | N36–N38 |
| Composition/result/contract substitution | Independent composition and result hashes match; contract binds the fully accepted current result | N21, N22, N41–N43 |
| Projection substitution | Projection set, composition hash, result hash, and active extensions match accepted state | N44–N47 |
| Authenticated Base crypto/signature spoofing | Ed25519 is selected/supported and every participant acceptance has a valid sender signature | N17–N20 |
| Invalid-message state injection | Schema/hash/chain/present-signature invalidity prevents reduction | N48–N51 |
| Composition explosion/resource abuse | Schema and rules enforce a bounded non-empty set; the registry maximum is 16 profiles | N01 and composition schema/rules validation |

Registry/profile substitution is prevented by resolving exact pairs and their requirements
from the generator-owned composition rules, whose source inputs are the product-profile
registry and all profile catalogs. The generated artifact is checked for drift in
`make validate`.

CAPNEG v0.2 does not prove real participant identity, authority to declare capabilities,
truthfulness of implementation-support declarations, external component conformance,
consensus outside the observed transcript, policy correctness, or transport security.
Those properties require separate evidence and deployment controls.
