# Documentation Layout

This repository follows an SDD-first docs structure:

- `docs/suite/` — suite-level overview and pointers to included specifications.
- `docs/core/` — normative Core specification text and supporting notes.
- `docs/extensions/` — extension RFCs that register optional capabilities.
- `docs/bindings/` — binding RFCs that define transport/runtime mappings.

When documentation introduces normative meaning changes, update corresponding machine-readable artifacts (`schemas/`, `fixtures/`, `registry/`, and `conformance/`) in the same PR.
