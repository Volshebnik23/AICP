# ADR: M66 clean-room pairwise interoperability

- **Status:** Accepted
- **Milestone:** M66
- **First target:** `AICP-BASE@0.1+BIND-MCP@0.1`
- **Current evidence release:** `AICP-PAIRWISE-TCK-1.2.0`
- **Historical evidence releases:** `AICP-PAIRWISE-TCK-1.0.0` and
  `AICP-PAIRWISE-TCK-1.1.0` (strong-ineligible)

## Decision

Pairwise interoperability is a separate evidence family. It does not fork or
extend the generalized Evidence TCK, does not change any AICP wire, profile, or
binding semantics, and does not mint a compatibility mark.

An eligible result is an orientation-independent typed relation between two
exact `(implementation_id, implementation_version, implementation_digest)`
tuples. Its joint report binds the exact Base full-profile and MCP full-binding
report bytes for both sides, exact release-local authority snapshots, and two fresh runs. Each
run preserves directional `A_TO_B` and `B_TO_A` evidence over real MCP
JSON-RPC stdio child-process I/O. Each exact participant build supplies two
load-bearing processes: a client that authors requests and consumes responses, and a
server that produces responses. Client describe output and an atomic server-ready
descriptor must both equal the participant and the two side-report subjects.

The causal proof is a three-message Core chain: proposal, acceptance, and
attestation. The acceptance is constructed only after the responder receives
the proposal hash; the attestation is constructed only after the originator
receives the acceptance hash. First-seen visibility sets, exact poll results,
message hashes, sessions, contracts, and JSON-RPC correlations are retained in
the report and independently recomputed by the evaluator. TCK 1.2 independently
validates each exchanged transcript as exact Core v0.1, uses the normative frozen
AICP-JCS/hash implementation, binds each participant-authored MCP request and
server-produced response to opaque process-instance IDs, and requires the proposal
contract goal to equal the unpredictable runtime challenge. The consumer does not receive
that challenge or the peer hash through test control; it first learns them in its own poll
response. A final consumer poll must retrieve the attestation. Two runs use fresh raw
IDs/challenges/process IDs but must normalize to the same role-routing semantics.

Ordinary conformance remains mandatory. The TCK 1.2 joint evaluator executes
release-frozen Base and binding report-level authorities resolved mechanically from the
four side reports; it does not call mutable current public-submission or generalized
evidence validators, construct a public submission recursively, or trust `passed` or
reported marks. Its complete local executable import closure and runtime runner closure are
generated and digest-bound. The 1.2 release-local registry schema and snapshot keep its
evaluation independent of unrelated future top-level registry changes.

The repository harness is a transparent bounded relay and independent evaluator, not
either peer. It records and forwards exact participant-produced request JSON to the selected
peer server and returns exact server-produced response JSON to the originating client; it
does not construct a successful semantic request or response. The
Python peer A and Node peer B own separate canonicalization, hashing, Core,
MCP, and control implementations and import no repository reference semantic
or expected-answer modules. Both peers are repository-owned test fixtures.
Their different digests prove only distinct exact builds, not organizational
independence, external adoption, or production identity custody.

The issued TCK 1.0 files and exact vector remain byte-frozen; policy marks that release
historical and strong-ineligible because its authority provenance was mutable, actual Core
traffic was not independently validated, and its runtime challenge was not load-bearing.
Issued TCK 1.1 files and vector are also byte-frozen and historical/strong-ineligible because
the repository harness constructed its joint MCP requests and its server processes were not
bound to participant builds. TCK 1.2 reuses the unchanged frozen 1.1 IUT/Core/Evidence
authority bytes by exact digest rather than duplicating their tree. Published relation
identity sorts the two exact build tuples; directional process routing inside the joint
report is never normalized away.

## Scope and limitations

M66 registers only `AICP-BASE@0.1+BIND-MCP@0.1`. It does not register other
profiles, HTTP, Core v0.2, CAPNEG, or extensions. It does not demonstrate
production organizational independence, remote attestation, internet-scale
network behavior, TLS deployment quality, key custody, or external adoption.
Role descriptors provide self-declared black-box build identity and harness-local process
routing evidence; they are not cryptographic remote attestation.
No real external pairwise submission is checked in, so demonstrated public
relations remain zero.
