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
- **Question:** Should full RFC8785 numeric canonicalization (including float edge cases) be required for Core v0.1 reference implementation, or is integer/string/object coverage sufficient for current fixture set?
- **Proposed options:**
  - Option A: Keep current strict rejection for floats until dedicated numeric fixtures are added.
  - Option B: Implement full RFC8785 float canonicalization now.
- **Decision owner:** AICP Working Group
- **Status:** open
- **Target milestone:** M5
- **Notes / links:** Reference code currently raises explicit errors on unsupported float cases.
