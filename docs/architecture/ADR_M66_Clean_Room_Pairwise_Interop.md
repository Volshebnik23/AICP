# ADR: M66 clean-room pairwise interoperability

- **Status:** Accepted
- **Milestone:** M66
- **First target:** `AICP-BASE@0.1+BIND-MCP@0.1`
- **Evidence release:** `AICP-PAIRWISE-TCK-1.0.0`

## Decision

Pairwise interoperability is a separate evidence family. It does not fork or
extend the generalized Evidence TCK, does not change any AICP wire, profile, or
binding semantics, and does not mint a compatibility mark.

An eligible result is an orientation-independent typed relation between two
exact `(implementation_id, implementation_version, implementation_digest)`
tuples. Its joint report binds the exact Base full-profile and MCP full-binding
report bytes for both sides, the frozen Pairwise TCK, and two fresh runs. Each
run preserves directional `A_TO_B` and `B_TO_A` evidence over real MCP
JSON-RPC stdio child-process I/O.

The causal proof is a three-message Core chain: proposal, acceptance, and
attestation. The acceptance is constructed only after the responder receives
the proposal hash; the attestation is constructed only after the originator
receives the acceptance hash. First-seen visibility sets, exact poll results,
message hashes, sessions, contracts, and JSON-RPC correlations are retained in
the report and independently recomputed by the evaluator. Two runs use fresh
raw IDs/challenges but must normalize to the same semantics.

Ordinary conformance remains mandatory. The joint evaluator calls the existing
report-level Base and binding authorities; it does not construct a public
submission recursively and does not trust `passed` or reported marks.

The repository harness is an independent evaluator, not either peer. The
Python peer A and Node peer B own separate canonicalization, hashing, Core,
MCP, and control implementations and import no repository reference semantic
or expected-answer modules. Both peers are repository-owned test fixtures.
Their different digests prove only distinct exact builds, not organizational
independence, external adoption, or production identity custody.

Historical reports bind the immutable release snapshot, not mutable current
registry bytes. Published relation identity sorts the two exact build tuples;
directional execution inside the joint report is never normalized away.

## Scope and limitations

M66 registers only `AICP-BASE@0.1+BIND-MCP@0.1`. It does not register other
profiles, HTTP, Core v0.2, CAPNEG, or extensions. It does not demonstrate
production organizational independence, remote attestation, internet-scale
network behavior, TLS deployment quality, key custody, or external adoption.
No real external pairwise submission is checked in, so demonstrated public
relations remain zero.
