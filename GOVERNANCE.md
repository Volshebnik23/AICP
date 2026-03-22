# Governance

AICP is maintained as a repo-first specification and conformance project.

## Stewardship model
- Maintainers/stewards make merge and release decisions for the repository.
- Humans set goals, scope, constraints, and risk posture.
- Agents may implement changes, tests, docs, and CI wiring within those constraints.
- Repo-backed normative docs, schemas, fixtures, registries, and conformance artifacts remain the source of truth.

## Decision path
- Small, reviewable PRs are preferred.
- Changes that affect shipped protocol artifacts should include the matching executable proof expected by the repo (schemas, fixtures, conformance, tests, docs as applicable).
- Releases are maintainer decisions, based on the checked-in repo state and passing verification commands.
- Compatibility and profile claims should be justified by conformance evidence, not by narrative-only assertions.

## Release posture
- AICP should not claim GA casually.
- Release-candidate and later release decisions should be backed by green CI, current release metadata, and truthful release notes.
- During RC hardening, narrow fixes and productization discipline are preferred over broad protocol expansion.

## Contribution expectations
Use the existing contribution and repo-process artifacts:
- `CONTRIBUTING.md`
- `README.md`
- `docs/`
- `conformance/`
- `schemas/`
- `fixtures/`
- `registry/`
