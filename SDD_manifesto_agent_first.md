# Agent‑First SDD (Spec‑Driven Development) — Startup Manifesto & Repo Playbook

> **Purpose:** enable a small team to ship fast with ChatGPT/Codex-style agents by making work **spec-driven**, **repo-native**, and **mechanically verifiable**.  
> **Inspired by:** OpenAI “Harness engineering: leveraging Codex in an agent-first world” — https://openai.com/index/harness-engineering/

---

## 0) One‑page summary (how we build)

**Humans steer. Agents execute.**  
Humans write *intent + constraints + acceptance criteria*; agents implement, test, document, and iterate in PRs.

**Repo is the system of record.**  
If it matters, it lives in the repository: specs, decisions, runbooks, quality rules, and executable checks.

**Legibility > elegance.**  
Optimize for an agent that can: find context → run the system → reproduce → validate via tests/UI/observability → open a clean PR.

**If an agent struggles, add capability—not pressure.**  
Missing docs, missing commands, missing tests, missing guardrails, missing observability, unclear boundaries.

---

## 1) The SDD Manifesto (14 principles)

1. **Humans steer. Agents execute.** Humans own goals, risks, judgment calls. Agents own code, tests, docs, CI wiring.
2. **Repo‑native truth.** Product intent, architecture, and operational reality must be in-repo.
3. **Index, don’t dump.** `AGENTS.md` is a short map; detail lives in `docs/`.
4. **Legibility wins.** Make code, docs, and workflows discoverable and runnable without tribal knowledge.
5. **Invariants over implementation.** Encode constraints as rules + checks, not “please follow.”
6. **Plans are artifacts.** Large work has an execution plan with progress + decision logs.
7. **Small PRs, fast loops.** Short-lived PRs; prefer iterative follow-ups over long blocking waits.
8. **QA scales via harness.** Give agents reliable build/test/e2e, plus UI-driving and observability access.
9. **Entropy is inevitable. Fight it systematically.** Golden principles + recurring cleanup PRs.
10. **Reproducibility first.** One-command setup/test/dev; pinned toolchains; deterministic fixtures.
11. **PRs are contracts.** Every PR carries verification evidence + risk + rollout/rollback notes.
12. **Definition of Done is executable.** DoD is CI-enforced, not a checklist in someone’s head.
13. **Behavior is protected by golden tests/evals.** Not just unit tests—end-to-end, user-journey proofs.
14. **Decisions have memory.** Use ADRs for meaningful choices so the repo can teach new humans/agents.

---

## 2) Core workflow (Issue → Spec → Agent → PR → Merge)

### 2.1. Three entry points
- **Bugfix:** bug report + steps to reproduce + expected behavior + environment.
- **Small feature:** mini‑PRD (≤1 page) + acceptance criteria.
- **Big feature:** PRD + RFC/design doc + execution plan.

### 2.2. The “SDD task prompt” (what every task must include)
Put this in the issue body (and copy into the agent prompt):

- **Context:** what and why (1–2 paragraphs)
- **Scope / Out of scope**
- **Acceptance criteria (AC):** verifiable checklist
- **Constraints:** architecture boundaries, security/privacy, perf budgets, migration rules
- **Where to look:** links to docs + key code entrypoints
- **How to verify:** commands and/or UI path

### 2.3. Agent PR loop
1. Agent creates a branch and opens a PR early.
2. Agent runs **local checks** (unit/integration/lint) and fixes failures.
3. Agent runs **e2e/golden tests**; if UI-related, drives UI automation and captures evidence.
4. Agent updates docs/ADRs/runbooks affected by behavior changes.
5. Optional: agent requests an additional agent review.
6. Human reviewer only blocks on **judgment** (product intent, safety, risk, boundaries).

### 2.4. Merge policy
- Prefer **small PRs**.
- Avoid blocking gates that require humans to babysit.
- If something flakes, prioritize **making it deterministic**; until then, follow-up PRs are acceptable.

---

## 3) Repository layout (agent‑readable)

Recommended minimum:

```
AGENTS.md
WORKFLOW.md
QUALITY_GATES.md
ARCHITECTURE.md
GOLDEN_PRINCIPLES.md

docs/
  product-specs/
    index.md
  design-docs/
    index.md
  exec-plans/
    active/
    completed/
  adr/
  playbooks/
    release.md
    migrations.md
    incidents.md
  references/
    <vendor-or-lib>-llms.txt

.github/
  PULL_REQUEST_TEMPLATE.md
```

Notes:
- Keep `AGENTS.md` short and link out.
- Keep docs **discoverable** with `index.md` files.
- Put external knowledge in `docs/references/*-llms.txt` (short, curated, repo-owned).

---

## 4) What each document must contain (templates)

### 4.1 `AGENTS.md` (1–2 screens max)
**Goal:** routing map for agents and humans.
- Quick start: setup/run/test commands (link to `WORKFLOW.md`)
- Where specs live (`docs/product-specs/`), where architecture rules live (`ARCHITECTURE.md`)
- “Hard constraints” (5–10 bullets max): forbidden actions, required checks
- PR checklist link (`QUALITY_GATES.md` + PR template)

### 4.2 `WORKFLOW.md`
- One-command standard: `make setup`, `make test`, `make lint`, `make e2e`, `make dev`
- Local dev expectations: env vars, seeds, fixtures, fake services
- How to add a new feature (small vs big)
- How to run UI automation (if applicable)
- How to read logs/metrics/traces locally

### 4.3 `QUALITY_GATES.md` (Executable DoD)
**Goal:** Definition of Done that CI enforces.
- Required checks by change type:
  - Backend change: unit + integration + contract tests
  - UI change: component tests + e2e golden flows
  - Data/schema change: migration tests + rollback notes
- Performance budgets (latency, payload size, bundle size, etc.)
- Observability requirements (minimum logs/metrics/traces fields)
- Documentation requirements (which docs must be updated for which changes)
- “Fail messages must instruct how to fix” rule for linters

### 4.4 `ARCHITECTURE.md`
- Domain/module map
- Allowed dependencies (directional)
- Boundary rules (auth, telemetry, feature flags, data validation on edges)
- Link to the mechanical checks that enforce the rules

### 4.5 `docs/product-specs/<feature>.md` (PRD)
- Problem / JTBD
- Users/personas
- User journeys + edge cases
- **Acceptance criteria** (verifiable list)
- Metrics (success + guardrails)
- NFRs: reliability, security/privacy, performance budgets
- Rollout plan: flags, migrations, rollback

### 4.6 `docs/design-docs/<rfc>.md` (RFC / design doc)
- Context + constraints
- Proposed design (components, contracts, data model)
- Alternatives considered (2–3) + why rejected
- Migration & rollout details
- Risk assessment
- Test strategy (what proves correctness)
- DoD summary

### 4.7 `docs/exec-plans/active/<plan>.md` (for big work)
- Goal + links to PRD/RFC
- Milestones/steps (1..N)
- **Progress log** (date → what changed)
- **Decision log** (decision → why)
- Verification plan (tests, e2e, perf, operational checks)

### 4.8 `docs/adr/NNN-<title>.md` (Architecture Decision Record)
- Context
- Decision
- Alternatives
- Consequences
- Links to PR/spec

### 4.9 `GOLDEN_PRINCIPLES.md`
Short list of “always/never” rules that prevent drift, e.g.:
- Validate external data at boundaries; no “YOLO parsing.”
- Shared invariants live in one place; avoid copy-paste helpers.
- Any behavior change requires updating spec/runbook/doc.
- If it’s important, enforce it with a check.

### 4.10 `docs/playbooks/*` (operational safety)
- `release.md`: canary, success metrics, rollback steps
- `migrations.md`: forward/backward compatibility, deployment order
- `incidents.md`: triage steps, comms, postmortem template

### 4.11 `docs/references/*-llms.txt`
Curated “agent-friendly” notes from vendor docs or internal conventions:
- 1–3 pages max
- Only stable, load-bearing facts
- Example commands, URLs, and “gotchas”

---

## 5) PR contract (required)

Create `.github/PULL_REQUEST_TEMPLATE.md` with:

- **Problem**
- **Solution**
- **Acceptance criteria** + how verified (commands, evidence, screenshots/video/log links)
- **Risk level** (low/med/high) + what can break
- **Rollout / feature flag / migration** notes
- **Rollback** plan
- **Docs updated?** links

PRs without this information are “incomplete specs.”

---

## 6) Tests & evals (protect behavior, not just code)

Minimum expectations:
- Every feature adds at least **one end-to-end golden flow**.
- “Golden” artifacts can be:
  - API snapshots
  - UI snapshots
  - trace/metric expectations (where stable)

Suggested structure:
```
tests/golden/
evals/
```

Rule of thumb: **if users care, there is a golden test.**

---

## 7) Taxonomy: how much spec is required?

| Task type | Required artifacts |
|---|---|
| Bugfix | bug report + repro + expected + verification steps |
| Small feature | mini‑PRD + AC + PR contract |
| Big feature | PRD + RFC + exec plan + e2e/golden |
| Refactor | quality gap + invariant + enforcement check |
| Reliability/ops | playbook update + observability proof + rollback plan |

---

## 8) Guardrails to encode in CI (minimum viable)

- **Architecture boundaries** (imports/dependencies rules)
- **Structured logging / telemetry contract**
- **Doc linting**: `docs/` structure, index links, broken references
- **Reproducible commands**: CI uses the same `make ...` commands as humans/agents
- **Fail messages teach**: lints/tests explain fixes

---

## 9) Repo health automation (fight entropy)

Add recurring tasks (weekly or daily depending on speed):
- dependency update PRs + vulnerability audit
- scan for violations of golden principles (open cleanup PRs)
- flaky test detector + stabilization PRs
- dead code / unused exports / outdated doc links scanner
- “doc gardening” agent that updates indices and stale sections

Treat these PRs as first-class product work: speed requires maintenance.

---

## 10) Copy‑paste mini templates

### 10.1 Mini‑PRD (≤1 page)
```
# <Feature>
## Problem
## Users
## User journey
## Acceptance criteria
- [ ]
## Metrics
## NFRs (perf/reliability/security)
## Rollout & rollback
```

### 10.2 RFC (short)
```
# RFC: <Title>
## Context & constraints
## Proposed design
## Alternatives
## Data/contracts
## Risks
## Test plan
## DoD
```

### 10.3 Exec plan
```
# Plan: <Title>
## Goal
## Links (PRD/RFC)
## Milestones
1.
2.
## Progress log
- YYYY-MM-DD:
## Decision log
- Decision:
  Why:
## Verification
- make test
- make e2e
- perf budget:
```

---

## 11) Operating rule (the “agent stuck” checklist)

If the agent is stuck for >2 iterations, we *don’t* push harder—we add capability:
- missing doc? → write it in `docs/`
- missing command? → add `make` target
- missing test? → add golden/e2e
- unclear boundary? → update `ARCHITECTURE.md` + enforce with a check
- hard-to-debug? → add logs/metrics/traces + local harness

That’s how we scale without burning human attention.
