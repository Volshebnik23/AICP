# Protocol Adapter / Gateway (CI-first)

This guide describes a minimal adapter architecture for ingesting AICP envelopes and emitting internal events.

## Module boundaries
1. **ingest**: receive envelope from transport.
2. **validate**: JSON/schema validation at boundary.
3. **verify**: recompute `message_hash`, verify signatures when available.
4. **translate**: map AICP envelope -> internal event shape.
5. **store**: append immutable transcript/event log.
6. **emit**: dispatch to internal workers or APIs.

## CAPNEG as input filter
Use negotiated CAPNEG outputs as machine-readable admission checks:
- reject unsupported profile/extension combinations,
- reject downgrade attempts,
- return deterministic `reason_code` in rejection artifacts.

## CI conformance posture
Recommended baseline in CI:
- `make validate`
- `make conformance-profiles` (selected profile)

## Degraded mode handling
If signature verification is unavailable, mark runs degraded and do **not** grant compatibility marks/badges.
