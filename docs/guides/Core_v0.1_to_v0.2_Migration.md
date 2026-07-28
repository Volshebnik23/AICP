# Migrating from Core v0.1 to experimental Core v0.2

Core v0.1 remains valid and frozen for the current UAT baseline. Core v0.2 is an
experimental post-UAT target and is not a silent compatible reinterpretation.

## Required migration decisions

1. Negotiate or select the exact profile version: `AICP-BASE@0.1` or
   `AICP-BASE@0.2`.
2. A Base 0.1 report cannot substantiate Base 0.2.
3. Existing message type IDs are reused, but their selected schemas and lifecycle semantics
   differ by Core/profile version.
4. Add `contract_version` to the contract object.
5. Compute `object_hash("contract", contract)` using the existing AICP object-hash domain.
6. Replace version-only references with exact branch/base/head version-hash references.
7. Bind `CONTRACT_ACCEPT` to the exact prior proposal ID, message hash, contract hash, and
   envelope reference.
8. Use `CONTEXT_AMEND.contract_effect="none"` only for context-only changes; revisions use
   propose/accept or exact `CHOOSE`.
9. Bind context and action messages to the exact current head.
10. A 0.1→0.2 gateway creates new contract/message artifacts and new hashes. It is not a
    transparent byte-preserving relay.
11. Old signatures cannot be copied onto translated messages because their message hashes
    change.
12. `AICP-AUTHENTICATED-BASE@0.1` is not equivalent to Base 0.2. No Authenticated Base 0.2
    profile exists yet.
13. Strict session-state projection v1 retains its Core v0.1 reference shape. Base 0.2
    cannot be combined with projection v1 as though exact-head projection support existed.
14. External-IUT support for Base 0.2 is deferred to later generalized evidence/TCK work.
15. Unsigned Base 0.2 messages remain valid, but every signature that is present must pass
    Ed25519 verification, key resolution, `kid` matching, and message-hash binding.
16. Apply mandatory message-local validation before state reduction. A rejected message
    must not index a proposal, activate a head, record an acceptance/rejection tuple, or
    select a conflict result.
17. Select payload schemas by Core version. The repository truth map keeps v0.1 as the
    default and lists v0.1/v0.2 variants for all six reused Core message IDs.

## Validation

Use:

```text
make quickstart-core-v02-py
make quickstart-core-v02-ts
python conformance/core_v02_runner/aicp_core_v02_runner.py \
  --suite conformance/core/CT_CORE_0.2.json \
  --out out/report_core_v02.json
python conformance/core_v02_runner/aicp_core_v02_profile_runner.py \
  --profile conformance/profiles/PF_AICP_BASE_0.2.json \
  --out out/report_profile_base_v02.json
```

The expected internal marks are `AICP-Core-0.2` and, through the profile runner,
`AICP-Profile-BASE-0.2`. They are emitted only by complete, non-degraded runs with no
degraded reasons or skipped checks. These are not external implementation evidence.
