# Release Notes

## Unreleased

### Added
- M17.1 anti-drift lint gate now validates compatibility mark alignment for extensions, profiles, and bindings, plus global mark uniqueness under `conformance/**`.
- Ops docs for release discipline: compatibility policy and release checklist.

### Changed
- Conformance reports now emit protocol `aicp_version` from suite/profile inputs while preserving artifact `suite_version`.
- Numeric canonicalization policy staged as M16a: integers must be IEEE-754 safe integers; floats remain rejected pending M16b.
- CAPNEG guidance now treats `BIND-MCP-0.1` as canonical negotiated binding ID (with `EXT-BIND-MCP` as deprecated alias).

### Fixed
- Pytest degraded-badge test mocks now include protocol version fields required by profile aggregation.

### Compatibility
- Stability graduation: `EXT-CAPNEG` and `AICP-BASE@0.1` are now marked stable (non-breaking; signals stricter compatibility expectations).
- **Backward compatible** for current Core schema shapes.
- **Policy tightening**: unsafe integers are now rejected during canonicalization; encode out-of-range values as strings.
- **Float acceptance**: finite floats are now canonicalized per RFC8785/ECMAScript numeric formatting; implementations must not rely on prior float-rejection behavior.
- M16b (future RFC8785 float support) MUST follow compatibility policy and include migration notes.
