# AICP Glossary (Canonical)

## Agent
An AI-capable protocol participant that sends/receives AICP messages and may act on delegated authority.

## Mediator / Host
A platform-controlled channel endpoint that can enforce gating, delivery, and session lifecycle behavior for mediated interactions.

## Enforcer / Moderator
An entity that evaluates policy/evidence and emits enforcement-relevant artifacts (e.g., EXT-ENFORCEMENT verdicts, EXT-ALERTS alerts).

## Observer / Auditor
A passive or independent participant that verifies transcript integrity, signatures, and policy evidence without changing contract state.

## Session
A protocol interaction context identified by `session_id`.

## Contract
The machine-readable context contract defining goal, roles, and policies. Core v0.2 also
places an opaque `contract_version` inside the exact contract object hash.

## Contract Ref
A message-level reference (`contract_ref`) that binds processing to branch/version state.
Core v0.2 uses exact branch/base/head version-hash pairs; Core v0.1 retains its frozen
version-only shape.

## Active Contract Head
The exact `{branch_id, head:{version, contract_hash}}` selected by a valid Core v0.2
acceptance or `CHOOSE` conflict resolution. A proposal alone is not an active head.

## Amendment
In Core v0.1, an amendment follows its frozen branch/version semantics. In Core v0.2,
`CONTEXT_AMEND` is context-only with `contract_effect="none"`; contract transitions require
proposal plus exact acceptance or conflict resolution.

## Conflict / Resolve
Conflict is divergent contract-head state. Core v0.2 standardizes exact `CHOOSE` only;
deterministic contract merge/patch semantics remain deferred.

## Policy (structured object)
A contract policy entry with `policy_id`, `category`, and `parameters`, plus optional metadata (version/status/uri/notes).

## Policy Category
A registered id from `registry/policy_categories.json` or a namespaced extension category (`x-...` or `vendor:...`).

## Enforcement (EXT-ENFORCEMENT)
Extension semantics for blocking-gate delivery with auditable `ENFORCEMENT_VERDICT` and sanctions.

## Verdict
An `ENFORCEMENT_VERDICT` decision (`ALLOW`/`DENY`/`INCONCLUSIVE`) bound to a target message.

## Sanction
A codified enforcement consequence (e.g., WARN/KICK/BAN), validated against sanction registry semantics.

## Alert (EXT-ALERTS)
Operational warning/fatal signal (`ALERT`) carrying code + recommended actions for deterministic recovery handling.

## Security Alert (EXT-SECURITY-ALERT)
Security incident/event signaling extension distinct from operational EXT-ALERTS taxonomy.

## Resume (EXT-RESUME)
Reconnect handshake using `RESUME_REQUEST` / `RESUME_RESPONSE` with explicit status and recovery actions.

## Resync (EXT-OBJECT-RESYNC)
Object/state resynchronization flows used when peers are out of sync.

## Conformance Suite
A machine-readable catalog of checks + fixtures executed by the conformance runner.

## Compatibility Mark
A suite/profile capability mark awarded only when required checks run and pass without degraded-mode disqualification.

## Profile
A composition of required suites representing a practical implementation target.

## Badge eligibility vs Degraded mode
A report may be `passed=true` yet `degraded=true` when critical checks are unavailable (e.g., signature backend missing); degraded reports are not badge-eligible and MUST NOT emit compatibility marks.
An unexpected skipped mandatory check has the same eligibility effect even if an adapter
incorrectly declares `degraded=false`; external-IUT consumer results must report all skip
and degradation fields explicitly.

## Coexistence with non-AICP chats
AICP is optional: agents may operate in channels that do not use AICP. Enforcement semantics apply only where a mediated channel actually uses AICP artifacts.


## Standard Overview
A short orientation document that explains what AICP is and is not, and points implementers to first-run commands and core references.

## Degraded mode
A report state where checks pass but critical capabilities are unavailable (for example, signature verification backend missing), so compatibility marks are withheld.

## Badge eligibility
Condition where required checks both pass and are fully enforceable (non-degraded), allowing compatibility mark issuance.


## AICP product profile
A named interoperability bundle (for example `AICP-BASE`,
`AICP-MEDIATED-BLOCKING`) represented as `{profile_id, profile_version}` and validated by
its profile-level conformance evidence. CAPNEG v0.1 selects one product profile; CAPNEG
v0.2 may select a canonical set of exact product profiles.

## Profile composition
A canonical, non-empty `aicp.profile_composition.v1` set of exact registered
`{profile_id, profile_version}` pairs negotiated by experimental CAPNEG v0.2. The set has
an independent `capneg.profile_composition` hash and does not create a dynamic profile ID
or aggregate compatibility mark.

## Component profile evidence
The separate suite/profile report and compatibility-mark identity for a selected profile.
Successful composition negotiation does not award or replace component profile evidence.

## Internal composition evidence
A non-degraded `CN_CAPNEG_0.2` repository run showing that the checked-in
resolver, fixtures, hashes, and negotiation reducer agree. It is not independent external
implementation evidence. M62 registers projection-v1 capability evidence only; generalized
external composition evidence remains unavailable.

## Crypto profile
A negotiated cryptographic/canonicalization capability set represented in CAPNEG `supported_profiles` and `selected.crypto_profile`; distinct from AICP product profiles.

## Profile requirement
A declared minimum acceptable AICP product profile set (`required_aicp_profiles`) that a participant/platform demands during CAPNEG.

## Downgrade (CAPNEG)
Selection of a weaker or unacceptable negotiated set (extensions/crypto/product profile) relative to declared requirements or previously accepted baseline; MUST be rejectable and auditable.
