# GOLDEN_PRINCIPLES.md — Anti-Drift Rules (short, strong, enforceable)

These principles prevent architecture and behavior drift when agents ship fast.
If a principle matters, **encode it in checks** (lint/tests/structural rules).

## Core principles
1. **Validate at boundaries.** External inputs are validated at the edge; no “YOLO parsing.”
2. **Single source of truth for invariants.** Shared rules live in one place; avoid copy-paste helpers.
3. **Behavior changes require docs updates.** Specs/runbooks/ADRs must match the code.
4. **Small PRs, reversible changes.** Prefer feature flags; migrations must be rollbackable.
5. **Invariants over style.** Prefer rules that define what must remain true, not how it’s implemented.
6. **Legibility > elegance.** Optimize for discoverability, reproducibility, and verifiability by an agent.
7. **If it’s important, enforce it.** Don’t rely on “please.” Write a check.
8. **Fight entropy systematically.** Recurring cleanup PRs are first-class work.

## How to evolve principles
- Propose changes via an ADR (`docs/adr/`).
- Add/adjust enforcement in CI.
- Update docs indexes so agents can find the new source of truth.
