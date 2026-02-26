# WORKFLOW.md — How We Build (Agent-First SDD)

## 1) Operating model
**Humans steer. Agents execute.**  
Humans own: goals, constraints, acceptance criteria, risk decisions.  
Agents own: implementation, tests, docs updates, CI wiring, PR iteration.

**Repo-native truth:** specs/decisions/runbooks live in the repo.

## 2) Task entry points & required spec level

### Bugfix
Must include:
- Steps to reproduce (copy-paste runnable)
- Expected vs actual
- Environment/version info
- How to verify the fix

### Small feature
Must include:
- Mini-PRD (≤ 1 page) with **Acceptance Criteria**
- Verification path (commands + UI path if relevant)

### Big feature
Must include:
- PRD (`docs/product-specs/...`)
- RFC/design doc (`docs/design-docs/...`)
- Execution plan (`docs/exec-plans/active/...`)

### Refactor / quality
Must include:
- Quality gap + target invariant
- A mechanical enforcement plan (lint/test/structural check)

## 3) The SDD task prompt (copy-paste)
Include this in the issue body and in the agent prompt:

- **Context:** what/why (1–2 paragraphs)
- **Scope / Out of scope**
- **Acceptance criteria:** verifiable checklist
- **Constraints:** architecture boundaries, security/privacy, performance budgets, migrations
- **Where to look:** links to docs + code entrypoints
- **How to verify:** exact commands and/or UI route

## 4) Agent PR loop
1. Agent opens a PR early.
2. Agent runs local checks (`make test`, `make lint`) and fixes failures.
3. Agent runs `make e2e` (golden flows) and captures evidence if UI-related.
4. Agent updates docs/ADRs/runbooks that changed.
5. Optional: request additional agent review.
6. Human reviewer blocks only on **judgment** (product intent, risk, boundaries).

## 5) Reproducibility & local dev
**One-command standard** (CI uses the same commands):
- `make setup`, `make test`, `make lint`, `make e2e`, `make dev`

Guidelines:
- Pin toolchains (a lockfile and/or version manager).
- Prefer deterministic fixtures and seeds.
- Avoid “works on my machine” dependencies.

## 6) UI automation & observability (recommended)
If the product has UI or complex flows:
- Provide a reliable way to run UI automation locally (`make e2e`).
- Make logs/metrics/traces accessible in dev so agents can diagnose regressions quickly.

## 7) “Agent stuck” checklist
If an agent is stuck >2 iterations, we add capability:
- missing doc → write it in `docs/`
- missing command → add `make ...`
- missing test → add golden/e2e
- unclear boundary → update `ARCHITECTURE.md` + enforce
- hard-to-debug → add logs/metrics/traces + local harness
