# AICP Pairwise TCK

M66 publishes one exact target: `AICP-BASE@0.1+BIND-MCP@0.1`. The current
release is `AICP-PAIRWISE-TCK-1.0.0`; its immutable snapshot, target/scenario
catalogs, strict joint schema, runner import closure, semantic normalizer, and
independent evaluator are all digest-bound under this directory.

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
provenance, all four side reports, exact process/build identity, both
directions, hash-chain causality, first-seen visibility, replay resistance, and
cross-run semantic equivalence.

An eligible joint report yields `eligible_pairwise_relations`; it always yields
an empty `eligible_marks`. Public packages need exactly five report files and
may use the non-promotable template at
`interop/submissions/templates/pairwise_submission/`.
