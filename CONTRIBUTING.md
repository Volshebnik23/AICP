# Contributing

Thanks for helping improve AICP.

## Process

- Follow the repository `AGENTS.md` for Agent-First SDD rules.
- Keep PRs small, focused, and verifiable.
- If normative meaning changes, update matching schemas/fixtures/conformance in the same PR.
- Do not hand-edit golden transcripts; regenerate deterministically and document how.

## Before starting any sprint

Quick pre-flight checklist:

- Re-read `ROADMAP.md` and `AGENTS.md`.
- Confirm current verification targets in `Makefile` and `.github/workflows/ci.yml`.
- If working on an extension milestone, confirm discoverability/IDs in `registry/` and related extension docs.

## When to do a Repo-Truth Sync Sprint (RTSS)

If local assumptions, public `main`, roadmap/docs, and executable CI surfaces drift out of sync, pause feature work and run a small **Repo-Truth Sync Sprint (RTSS)** PR first. See `docs/process/RTSS.md` for the canonical RTSS definition and workflow. A clean working tree is not proof there is nothing to PR—always compare against public `main` and verify remote branch/PR state.

## Local checks

Run before opening a PR:

- `make validate`
- `make conformance`
- `make conformance-ext`
- `make conformance-bindings`
- `make test`
- `make quickstart-py`
- `make quickstart-ts`
- `cd sdk/typescript && npm ci && npm test && cd ../..`

Use the PR template and include risk and compatibility impact.

Reminder: reproduce the exact failing CI/local target first before editing (for example run `make conformance-ext` before touching extension code), then trace suite + generator + schema + runner routing from executable artifacts.
