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
