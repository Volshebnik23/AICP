# AGENTS.md — Agent-First SDD Map (read this first)

This repository uses **Agent-First SDD (Spec-Driven Development)**: humans write intent + constraints; agents implement via PRs.

## Quick start (one-command standard)
- Setup: `make setup`
- Run tests: `make test`
- Lint: `make lint`
- E2E / golden flows: `make e2e`
- Dev server: `make dev`

If any of these commands are missing, **add them** (don’t document around it).

## Where the “truth” lives
- **Workflow & local dev:** `WORKFLOW.md`
- **Definition of Done / quality gates:** `QUALITY_GATES.md`
- **Architecture boundaries:** `ARCHITECTURE.md`
- **Golden principles (anti-drift):** `GOLDEN_PRINCIPLES.md`
- **Product specs (PRDs):** `docs/product-specs/`
- **Design docs (RFCs):** `docs/design-docs/`
- **Execution plans:** `docs/exec-plans/`
- **Decisions (ADRs):** `docs/adr/`
- **Operational playbooks:** `docs/playbooks/`
- **Curated external refs for agents:** `docs/references/`

## Hard constraints (minimum)
1. **Repo is the system of record.** If it matters, it must be in-repo (spec/decision/runbook).
2. **Small PRs, fast loops.** Prefer iterative PRs over giant merges.
3. **DoD is executable.** If it’s important, enforce it in CI (`QUALITY_GATES.md`).
4. **Behavior changes require docs updates.** Specs/runbooks/ADRs must match the code.
5. **Golden/e2e protect user flows.** New user-facing features add at least one golden flow.
6. **Architecture rules are not optional.** Update `ARCHITECTURE.md` *and* its enforcement if you change boundaries.

## How to open a PR (required)
Follow the PR contract described in `QUALITY_GATES.md` (verification evidence, risk, rollout/rollback, doc links).

## If an agent is stuck (2+ iterations)
Don’t push harder—add capability:
- missing doc → add in `docs/`
- missing command → add `make ...`
- missing test → add golden/e2e
- unclear boundary → update `ARCHITECTURE.md` + enforce
- hard to debug → add logs/metrics/traces + local harness
