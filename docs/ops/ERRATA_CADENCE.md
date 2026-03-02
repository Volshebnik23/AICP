# Errata Cadence

## When to file errata
File an erratum when a shipped artifact has a correctness or interoperability issue in:
- normative docs,
- schemas/registries,
- fixtures/conformance,
- reference tooling.

## Triage cadence
- Weekly triage during active development.
- Before each release cut, all open high-impact errata must be reviewed.

## Status lifecycle
`open` -> `in_progress` -> `fixed` (or `wont_fix`).

## Release + compatibility integration
- Fixed errata MUST be referenced in `RELEASE_NOTES.md`.
- If the fix changes compatibility expectations, it MUST also reference `docs/ops/COMPATIBILITY_POLICY.md`.
