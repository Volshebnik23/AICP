# AGENTS.md — AICP — Agent Interaction Content Protocol Repo (Agent-First SDD)
“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

This repository is run using **Agent-First SDD (Spec-Driven Development)**:
humans define intent + constraints + acceptance criteria; agents implement via PRs.

**Prime directive:** AICP must remain **implementable** (not theoretical).
If something matters, it must be checkable via schemas/tests/conformance.

---

## 0) Operating model (how we work)
- **Humans own:** goals, scope, constraints, acceptance criteria, risk decisions, release calls.
- **Agents own:** implementation, tests, docs updates, CI wiring, iterative PR loop.

Small PRs, fast feedback loops. Prefer incremental progress over large refactors.

---

## 1) Sources of truth (what is canonical)
### Specification (human-readable)
- `docs/` — all public documentation and RFCs
- `docs/core/` — **AICP Core v0.1 (Normative)** (the canonical normative text)
- `docs/suite/` — umbrella “suite overview” and pointers to Core + EXT RFCs
- `docs/extensions/`, `docs/bindings/` — extension & binding RFCs (Registered Extensions)

### Machine-readable truth (must match the spec)
- `schemas/` — JSON Schemas (Core + extensions/bindings as applicable)
- `registry/` — registries (message types, profiles, codes, bindings IDs, etc.)
- `fixtures/` — test vectors + golden transcripts (deterministic)

### “Executable proof”
- `conformance/` — conformance suites + runner
- `reference/` — minimal reference implementations (correctness > performance)
- `examples/` — small runnable examples (adoption accelerators)

---

## 2) One-command standard (SDD ergonomics)
This repo should offer a simple, stable interface. Prefer a Makefile or equivalent.

Expected commands (CI should use the same):
- `make validate`  — validate JSON/JSONL + schema validation of fixtures
- `make test`      — reference tests / conformance runner (as available)
- `make lint`      — optional (when code exists)
- `make e2e`       — optional (golden flows runner, if separate)

If any command is missing, **add it** (don’t document around it).

---

## 3) Hard constraints (anti-drift rules)
1) **Repo is the system of record.** If it matters, it must be in-repo.
2) **Core stability.** Changes to Core MUST include:
   - updated schemas (if structure changes),
   - updated fixtures/golden transcripts (if behavior changes),
   - updated conformance tests,
   - clear migration / compatibility notes.
3) **No “YOLO parsing”.** Validate external inputs at the boundary (schemas).
4) **Golden transcripts are sacred.** Do not edit golden transcripts by hand.
   Regenerate deterministically and document how.
5) **Registries are authoritative.** New IDs/types/codes must go through `registry/`
   and must not collide with existing entries.
6) **Enforcement must be possible externally.**
   Any normative rule should be verifiable by a third-party enforcer using:
   message hashes/chain, signatures, contract refs, and policy artifacts.

---

## 4) PR contract (required)
Every PR must include (in PR description):
- **Problem / context** (what & why)
- **Solution** (what changed)
- **Acceptance criteria** (verifiable checklist)
- **How verified** (exact commands + outputs)
- **Risk level** (low/med/high) + what could break
- **Docs updated?** (links)
- **Compatibility impact** (none / backward compatible / breaking)

If you can’t verify locally, explain why and what CI covers.

---

## 5) Change types → required gates
### A) Spec-only changes (docs)
- Must not contradict schemas/fixtures.
- If meaning changes, update schemas/fixtures/conformance accordingly.

### B) Schema changes (`schemas/`)
- Must update:
  - fixtures (if needed),
  - conformance suite,
  - reference implementations (if present),
  - compatibility notes.

### C) Registry changes (`registry/`)
- Must validate:
  - unique IDs,
  - no collisions,
  - correct formatting,
  - backward compatibility rules.

### D) Fixtures / golden transcripts changes (`fixtures/`)
- Must be deterministic.
- Must include a short note describing generation method and why it changed.

### E) Reference code changes (`reference/`, `conformance/`)
- Must keep tests green and avoid breaking the “one-command standard”.

---

## 6) How to write an SDD task prompt (copy-paste)
Use this structure in issues and in agent prompts:

- **Context:** why (1–2 paragraphs)
- **Scope / Out of scope**
- **Acceptance criteria:** verifiable checklist
- **Constraints:** compatibility, security, privacy, performance, no hand-edits of fixtures
- **Where to look:** files/dirs to touch
- **How to verify:** exact commands
- **Deliverable:** PR + summary + verification notes

---

## 7) If an agent is stuck
If an agent loops >2 iterations, add capability:
- missing doc → write it in `docs/`
- missing test → add a conformance test / fixture
- missing command → add to Makefile and CI
- unclear norm → clarify normative text (MUST/SHOULD) + add test

Keep moving with small PRs.

If ambiguity or inconsistency is discovered during implementation, record it in `OPEN_QUESTIONS.md` or `ERRATA.md` and reference it in the PR.
