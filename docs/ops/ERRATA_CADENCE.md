# Errata Cadence

## Purpose
This policy defines how AICP errata are filed, triaged, and resolved so spec/schema/fixture drift is visible and release decisions stay auditable.

## When to file an erratum
File an `ERRATA.md` entry when any shipped artifact has a correctness or consistency issue across:
- normative docs,
- schemas/registries,
- fixtures/golden transcripts,
- conformance/tests/tooling.

## Required workflow
1. Create an `ER-XXXX` entry in `ERRATA.md` with required fields.
2. Set status to `open` during intake.
3. Move to `in_progress` once an implementation PR is active.
4. Move to `fixed` when merged and validated in CI, or `wont_fix` with rationale.

## Release and compatibility linkage
- All open `high` impact errata MUST be reviewed before release tagging.
- Any erratum that changes compatibility behavior MUST include release-note compatibility text and migration guidance.
- Stable artifacts affected by errata MUST be accompanied by schema/fixture/conformance updates when applicable.

## Cadence
- Intake/triage: continuous.
- Review: at least once per sprint before release decisions.
- Closure: tracked in the PR that implements the fix.
