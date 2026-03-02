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
- **Status:** decided (staged)
- **Target milestone:** M16a (completed), M16b (planned)
- **Notes / links:** Closed: M16b implemented finite-float canonicalization with shared float64 vectors under `conformance/vectors/rfc8785_float64_vectors.json`; non-finite numbers remain rejected and unsafe integers remain disallowed.
