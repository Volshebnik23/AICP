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
- **Status:** in_review | in_review | decided | deferred
- **Target milestone:**
- **Notes / links:**

## Questions

- **ID:** OQ-0001
- **Context:** JCS canonicalization in `reference/python/aicp_ref/jcs.py`.
- **Question:** How should AICP maintain and evolve numeric canonicalization after shipping float support + safe-number policy in M16?
- **Proposed options:**
  - Option A: Keep current policy (finite floats supported, unsafe integers rejected) and add more cross-language numeric vectors.
  - Option B: Expand to full RFC8785 numeric coverage (including broader edge-case test corpus) in a follow-on milestone.
- **Decision owner:** AICP Working Group
- **Status:** in_review
- **Target milestone:** M16
- **Notes / links:** M16 Part 1 (float rejection parity) is historical; M16 Part 2 now supports finite floats with deterministic normalization and enforces safe integers across reference + dropins + SDK. Numeric guardrails now require float-pass and unsafe-int fail behavior.
