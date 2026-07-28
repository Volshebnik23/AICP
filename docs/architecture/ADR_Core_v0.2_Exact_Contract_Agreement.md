# ADR: Versioned Core v0.2 for Exact Contract Agreement

- **Status:** Accepted
- **Milestone:** M60
- **Target:** experimental, post-UAT `AICP-BASE@0.2`

## Decision

Exact contract artifact and active-head agreement is introduced through a separate Core
v0.2 normative path, schemas, conformance suite, fixtures, profile, reference helpers, and
quickstarts. Core v0.1 and `AICP-BASE@0.1` remain frozen.

The change is Core-level because acceptance now identifies one exact proposal message,
contract object hash, transition base, and resulting head. That is lifecycle meaning, not
optional metadata.

## Rejected alternatives

1. **Silently strengthen Core v0.1.** Rejected because it would move the frozen UAT
   compatibility goalposts and invalidate previously conforming v0.1 messages.
2. **Documentation-only clarification.** Rejected because optional hashes and ambiguous
   acceptance cannot be enforced without schemas, fixtures, a reducer, and conformance.
3. **Optional extension.** Rejected because two peers could both claim Core while one omits
   exact agreement; acceptance binding is fundamental lifecycle behavior.
4. **Message-chain integrity alone.** Rejected because a valid chain proves ordered message
   bytes, not that acceptance names the exact proposal artifact or active head.
5. **Human-readable versions alone.** Rejected because opaque version labels do not bind
   contract bytes and have no numeric ordering semantics.

## Consequences

Implementations must select the exact profile version and use the matching schemas. A 0.1
report cannot substantiate 0.2. Gateways translating between versions create new artifacts,
message hashes, and any required signatures. The same six registered Core IDs therefore
have explicit version-selected schema mappings while v0.1 remains the default canonical
mapping. Base 0.2 permits unsigned messages, verifies every signature that is present, and
blocks all state effects from messages rejected by mandatory message-local validation.
Degraded or skipped execution can remain a behavioral pass but emits no Core or profile
mark. Base 0.2 has internal conformance evidence but no external-IUT target in M60.
Authenticated Base 0.2, projection-v1 composition, merge/patch semantics, and generalized
external evidence are deferred.
