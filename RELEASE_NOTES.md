# Release Notes

## Unreleased

### Added
- M17.1 anti-drift lint gate now validates compatibility mark alignment for extensions, profiles, and bindings, plus global mark uniqueness under `conformance/**`.
- Ops docs for release discipline: compatibility policy and release checklist.

### Changed
- Core narrative/docs now explicitly align shipped `ERROR` baseline with schema/conformance and clarify spec → schemas → conformance → reference helper boundaries.
- TS onboarding template now reuses the official TypeScript hashing helper path and emits deterministic two-message JSONL as documented.
- Protocol-adapter template now preserves audit-critical envelope fields (`prev_msg_hash`, `signatures`, `contract_ref`, relation/extension projection) and labels remaining projection lossiness as demo-only.
- Conformance reports now emit protocol `aicp_version` from suite/profile inputs while preserving artifact `suite_version`.
- Numeric canonicalization updated to M16b: finite floats are now supported using deterministic ECMAScript/RFC8785-aligned tokens; non-finite values remain rejected.
- CAPNEG guidance now treats `BIND-MCP-0.1` as canonical negotiated binding ID (with `EXT-BIND-MCP` as deprecated alias).

### Fixed
- Python reference transcript validation now rejects non-first messages missing `prev_msg_hash`, rejects signature `object_hash` mismatches against `message_hash`, and enforces consistent signer/`kid` handling.
- Template quickstart docs now reference existing fixture paths and executable commands.
- Pytest degraded-badge test mocks now include protocol version fields required by profile aggregation.

### Compatibility
- **Backward compatible** for protocol/schema surfaces; this release is a productization hardening pass (validation strictness + doc/template/CI alignment).
- Implementations relying on previously under-enforced Python reference checks may now fail fast on invalid chains/signatures and should correct generated transcripts.
- Stability graduation: `EXT-CAPNEG` and `AICP-BASE@0.1` are now marked stable (non-breaking; signals stricter compatibility expectations).
- **Backward compatible** for current Core schema shapes.
- **Policy tightening**: unsafe integers are now rejected during canonicalization; encode out-of-range values as strings.

- Compatibility note: implementations may now exchange finite float payload values in canonical JSON. Integer values still MUST remain within IEEE-754 safe integer range (±(2^53-1)).


## v88 / 0.1.0-dev (experimental extensions)
Added experimental EXT-ECONOMICS, EXT-ADMISSION, EXT-QUEUE-LEASES, EXT-FACILITATION, EXT-CHANNELS, EXT-SUBSCRIPTIONS, EXT-PUBLICATIONS, EXT-INBOX, EXT-MARKETPLACE, EXT-PROVENANCE, and EXT-ACTION-ESCROW with schemas, fixtures, suites, and runner checks.
