# AICP Pairwise TCK

M66 publishes one exact target: `AICP-BASE@0.1+BIND-MCP@0.1`. The current
release is `AICP-PAIRWISE-TCK-1.1.0`; its immutable target/scenario and underlying
authority snapshots, strict joint schema, runner/evaluator import closures, semantic
normalizer, Core validator, and independent evaluator are digest-bound under this
directory. Issued `AICP-PAIRWISE-TCK-1.0.0` bytes remain frozen, while release policy
classifies that release historical and strong-ineligible with a deterministic reason.

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
`tools/call` send/poll exchanges. The evaluator independently validates TCK
provenance, all four side reports through frozen authorities, exact process/build
identity, both directions, actual Core v0.1 transcript validity, normative AICP hashes,
runtime-challenge binding, hash-chain causality, first-seen visibility, replay resistance,
and cross-run semantic equivalence.

An eligible joint report yields `eligible_pairwise_relations`; it always yields
an empty `eligible_marks`. Public packages need exactly five report files and
may use the non-promotable template at
`interop/submissions/templates/pairwise_submission/`.
