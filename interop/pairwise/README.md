# AICP Pairwise TCK

M66 publishes one exact target: `AICP-BASE@0.1+BIND-MCP@0.1`. The current
release is `AICP-PAIRWISE-TCK-1.2.0`; its immutable target/scenario, release-local
registry schema, strict joint schema, runner/evaluator import closures, semantic
normalizer, Core validator, and independent evaluator are digest-bound under this
directory. It reuses the exact frozen 1.1 authority artifacts by digest. Issued
`AICP-PAIRWISE-TCK-1.0.0` and `AICP-PAIRWISE-TCK-1.1.0` bytes remain frozen and both
releases are historical and strong-ineligible.

The test peers under `cleanroom/` are repository-owned and deliberately use
different runtimes and separate semantic implementations. They are not public
submissions or external adoption evidence. Test commands retain their reports
only in temporary directories:

```bash
make pairwise-targets-validate
make pairwise-base-mcp-cleanroom
make pairwise-base-mcp-external-test
make pairwise-negative
make pairwise-submission-examples
```

The joint runner uses shell-free, allowlisted child processes, bounded JSON
lines/message counts/timeouts/stderr, fresh run material, and actual MCP
`tools/call` send/poll exchanges. Each participant's client constructs the request and
consumes the response; the repository harness only routes and records the exact JSON.
Atomic server-ready descriptors and client describe responses bind both process roles to
the exact side-report identity. The evaluator independently validates TCK provenance,
all four side reports through frozen authorities, exact process/build identity, both
directions, actual Core v0.1 transcript validity, normative AICP hashes,
runtime-challenge isolation, hash-chain causality, client-first-seen visibility, the final
consumer poll, replay resistance, and cross-run semantic equivalence.

An eligible joint report yields `eligible_pairwise_relations`; it always yields
an empty `eligible_marks`. Public packages need exactly five report files and
may use the non-promotable template at
`interop/submissions/templates/pairwise_submission/`.

Role descriptors establish black-box identity coherence for one test run; they are not
remote attestation and do not prove production key custody or organizational independence.
