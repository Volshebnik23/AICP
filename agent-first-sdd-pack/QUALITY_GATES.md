# QUALITY_GATES.md — Executable Definition of Done (DoD)

This file defines the **Definition of Done** that should be **mechanically enforced** (CI) whenever possible.

## 1) PR contract (required)
Every PR must include:
- **Problem**
- **Solution**
- **Acceptance criteria** + **How verified** (commands + evidence)
- **Risk level** (low/med/high) + what could break
- **Rollout plan** (feature flag / migration notes if relevant)
- **Rollback plan**
- **Docs updated?** (links)

## 2) Required checks by change type (minimum)
### Backend/API
- `make test` (unit + integration)
- Contract tests for API changes (if applicable)
- Data validation at boundaries (no “YOLO parsing”)

### Frontend/UI
- Component/unit tests (as applicable)
- `make e2e` must include at least one golden user flow for new features
- Bundle/perf budgets enforced where relevant

### Data/schema changes
- Migration tests
- Backward/forward compatibility checks
- Explicit rollback steps

### Observability / reliability work
- Proof of telemetry: logs/metrics/traces added or updated
- Runbook updated in `docs/playbooks/` if operational behavior changes

## 3) Performance & reliability budgets
Define project-specific budgets here (examples):
- p95 latency: < ___ ms
- error rate: < ___
- startup time: < ___
- UI bundle size: < ___ KB

## 4) Documentation gates
When behavior changes, update:
- PRD / RFC (if intent/design changed)
- ADR (if a decision was made)
- Runbook (if ops behavior changed)
- Any relevant `docs/index.md`

## 5) CI/Lint ergonomics rule
**Fail messages must teach.**  
Any lint/test failure should include a clear instruction on how to fix it.

## 6) Golden tests / evals
Rule of thumb: **if users care, there is a golden flow.**
- Store stable, user-journey proofs in `tests/golden/` and/or `evals/`
- Keep them deterministic and fast
