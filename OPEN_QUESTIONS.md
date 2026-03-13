# OPEN_QUESTIONS

Track unresolved specification/productization questions here.

## Template
- **ID:** OQ-XXXX
- **Context:**
- **Question:**
- **Proposed options:**
  - Option A:
  - Option B:
- **Decision owner:**
- **Status:** open | in_review | decided | deferred
- **Target milestone:**
- **Notes / links:**

## Questions

- **ID:** OQ-0001
- **Context:** JCS canonicalization in `reference/python/aicp_ref/jcs.py`.
- **Question:** How should AICP complete RFC8785 numeric canonicalization and safe-number policy after the current v0.1 float-rejection baseline?
- **Proposed options:**
  - Option A: Keep strict float rejection as the baseline until full RFC8785 numeric handling lands.
  - Option B: Implement full RFC8785 float canonicalization now.
- **Decision owner:** AICP Working Group
- **Status:** decided (implemented)
- **Target milestone:** M16a (completed), M16b (completed)
- **Notes / links:** Update: M16b implemented. Canonicalization now allows finite floats with deterministic ECMAScript-aligned numeric tokens. Safe-integer enforcement for integers remains in effect.
- 2026-03-13: ROADMAP marks M24 shipped while `AICP_Backlog` remains a planning artifact listing M24 as remaining by default structure; keep treating backlog as planning-only and roadmap as shipped-state source of truth unless governance decides to prune delivered backlog sections.
- 2026-03-14: Planning-order drift noted: `AICP_Backlog` lists M27 before M28, while `ROADMAP.md` milestone progression executed M28 before M27 due enterprise-control dependency closure. Keep numbering unchanged; treat roadmap as shipped-history source and backlog as remaining-planning source.
