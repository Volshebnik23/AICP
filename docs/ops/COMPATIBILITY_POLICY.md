# Compatibility Policy (MVP)

## Version semantics
- **Protocol version (`aicp_version`)** identifies interoperable wire/protocol semantics.
- **Artifact version (`suite_version`, repo `VERSION`)** identifies shipped repository artifacts.
- Conformance evidence MUST preserve this distinction.

## Stability levels
- **stable**: backward compatibility expected across minor updates.
- **experimental**: may change quickly with explicit release-note callouts.
- Registries are authoritative for declared status.

## Breaking changes
A change is breaking if it can cause previously-valid artifacts to fail validation or conformance, including:
- message/schema field removals or required-field additions,
- canonicalization/hash/signature semantic changes,
- registry identity renames/removals without compatibility aliases,
- conformance rule tightening without migration notes.

## Deprecation policy
- Deprecations MUST be documented in release notes before removal.
- Deprecated IDs MAY remain as aliases for a transition window; canonical IDs MUST be documented.

## Conformance evidence
- Compatibility claims MUST be backed by current `make validate`, `make conformance-all`, and snapshot outputs.
- Degraded-mode reports do not grant compatibility marks.
