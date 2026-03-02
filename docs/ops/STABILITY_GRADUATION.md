# Stability Graduation Policy

AICP registry statuses:
- `experimental`: rapid iteration, no strict compatibility guarantees.
- `stable`: compatibility intent is frozen; changes require explicit compatibility notes.
- `deprecated`: retained for transition; replacement guidance required.
- `withdrawn`: no longer for use.

## Promotion checklist (`experimental` -> `stable`)
1. Normative spec exists and is anchored (`spec_ref` with `#...`).
2. Machine-checkable schemas/registries are present.
3. Deterministic fixtures exist.
4. Conformance coverage exists and passes in CI.
5. Profile inclusion and/or interop evidence is documented.
6. Compatibility notes are recorded in registry + release notes.

## Stable change policy
Stable entries MUST avoid breaking renames/removals. Any tightening or semantic change requires:
- compatibility note,
- migration guidance,
- conformance evidence update.

## Deprecated policy
Deprecated entries MUST include deprecation notes and preferred replacement.
Removal requires prior deprecation window and release-note callouts.
