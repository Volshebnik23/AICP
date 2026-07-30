# CAPNEG v0.2 threat model and executable coverage

This M61 threat note covers the experimental multi-profile negotiation surface. The
normative state and hash rules are in `docs/extensions/RFC_EXT_CAPNEG_v0.2.md`; executable
cases are in `fixtures/extensions/capneg_v0_2/negative_cases.json`.

| Threat | Required rejection or invariant | Executable cases |
|---|---|---|
| Profile-set downgrade or omission | Product requirements and each participant-required crypto minimum are present; every selection is supported | N12-N18, N76-N78 |
| Unsupported profile or Core-family injection | Profiles are exact registered pairs in the supported Core v0.1 family | N04, N06, N07 |
| Duplicate/reordered ambiguity or same-family substitution | Set is non-empty, unique, canonically sorted, and has at most one version per profile ID | N01-N05 |
| Redundant/exclusive set ambiguity | Strict requirement subsets and exclusive policy-semantic dialects fail | N08-N11 |
| Stale or forked capability declarations | Proposals and decisions bind each participant's latest valid declaration | N23-N29, N69-N72 |
| Proposal rollback or decision retargeting | Revisions are contiguous/predecessor-bound; decisions bind exact result, session, and contract | N30-N35, N39, N40, N52-N55, N66-N68 |
| Rejection/replay state corruption | Rejection is terminal per revision; exact accept/reject replay is validated before idempotence | N36-N38, N57, N58, N73-N75, N94 |
| Cross-context or missing supersession | One exact accepted root exists per session/contract/participant context; every later negotiation names it | N79-N82, N99-N102 |
| Composition/result/Core-contract substitution | Frozen Core v0.1 schemas and envelope/object contract identity pass before exact CAPNEG binding | N21, N22, N41-N43, N88-N91 |
| Projection time/substitution | Projection matches accepted state at its exact prior transcript prefix; branch-head-only evidence fails | N44-N47, N83-N87 |
| Signature spoofing, unavailable verification, or partial validation | Auth acceptances require a sender signature even without a backend; present unverifiable signatures fail closed; every present signature entry validates | N17-N20, N51, N56-N65, N97, N98, N103, N104 |
| Invalid-message state injection | Schema, ID, context, chain, hash, and signature invalidity blocks mutation and retains multiplicity | N48-N65, N95-N98 |
| Unbounded rejection constraints | Alternative constraints are closed/versioned and preserve participant requirements | N92-N94 |
| Composition explosion/resource abuse | Schema and rules enforce a bounded non-empty set; the registry maximum is 16 profiles | N01 and composition schema/rules validation |

Registry/profile substitution is prevented by resolving exact pairs and their requirements
from the generator-owned composition rules, whose source inputs are the product-profile
registry and all profile catalogs. The generated artifact is checked for drift in
`make validate`.

The fixture serializer and production implementation do not generate the expected semantic
result. A reviewed oracle catalog records exact message origin and multiplicity, with
negative controls for context, signer, rejection, participant crypto, and projection-time
defects.

Those controls run deliberately broken implementations through the same case execution,
observation normalization, oracle comparison, and suite-failure path as production. The
reviewed oracle therefore detects wrong origin, wrong multiplicity, and unexpected
observations rather than testing dictionary inequality.

CAPNEG v0.2 does not prove real participant identity, authority to declare capabilities,
truthfulness of implementation-support declarations, external component conformance,
consensus outside the observed transcript, policy correctness, or transport security.
Those properties require separate evidence and deployment controls.
