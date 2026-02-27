# Documentation Layout

This repository follows an SDD-first docs structure:

- `docs/suite/` — suite-level umbrella overview and pointers to standalone RFC specifications.
- `docs/core/` — normative Core specification text.
- `docs/rfc/` — suite-wide RFCs (registries, error model, governance, reference/conformance, interop/security).
- `docs/extensions/` — extension RFCs that register optional capabilities.
- `docs/bindings/` — binding RFCs that define transport/runtime mappings.

Moved suite file:
- Canonical: `docs/suite/AICP_Suite_Overview_and_Skeleton_v0.1.21_EN.md`
- Backward-compat stub: `AICP_Suite_Overview_and_Skeleton_v0.1.21_EN.md`

When documentation introduces normative meaning changes, update corresponding machine-readable artifacts (`schemas/`, `fixtures/`, `registry/`, and `conformance/`) in the same PR.
