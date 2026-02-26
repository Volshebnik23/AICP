# Contributing

Thanks for helping improve AICP.

## Process

- Follow the repository `AGENTS.md` for Agent-First SDD rules.
- Keep PRs small, focused, and verifiable.
- If normative meaning changes, update matching schemas/fixtures/conformance in the same PR.
- Do not hand-edit golden transcripts; regenerate deterministically and document how.

## Local checks

Run before opening a PR:

- `make validate`
- `make test`

Use the PR template and include risk and compatibility impact.
