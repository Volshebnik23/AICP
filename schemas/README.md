# Schema Versioning Principles

Schemas are machine-readable truth for protocol artifacts.

## Layout

- Core schemas live in `schemas/core/`.

## Principles

- Keep schema updates aligned with normative docs.
- Prefer additive, backward-compatible changes where possible.
- For behavioral or structural changes, update fixtures and conformance checks in the same PR.
- Validate external input at boundaries; avoid permissive/ambiguous parsing.

If semantics change, include compatibility impact notes in the PR.
