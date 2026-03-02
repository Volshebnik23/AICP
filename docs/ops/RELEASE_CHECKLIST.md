# Release Checklist (MVP)

## Required verification commands
- `make validate`
- `make test`
- `make conformance-all`
- `make snapshot`

## Required content updates
- Update `RELEASE_NOTES.md` (Added/Changed/Fixed/Compatibility sections).
- Update `ROADMAP.md` progress + next milestone.
- Document registry changes (if any) and compatibility impact.
- Ensure tracked conformance reports/snapshot artifacts are current.

## Versioning rules
- `aicp_version` tracks protocol semantics.
- `VERSION` / `suite_version` track artifact release version.
- Any breaking semantic change MUST include explicit compatibility notes and migration guidance.

## Hygiene checks
- No manual edits to golden transcripts; use deterministic generators.
- Include exact verification commands in PR description.

- Review open errata per `docs/ops/ERRATA_CADENCE.md` and note disposition in release notes.
