# AICP Core

The frozen UAT target remains [Core v0.1](AICP_Core_v0.1_Normative.md).

The separate [Core v0.2 exact-contract-agreement target](AICP_Core_v0.2_Normative.md)
is experimental and post-UAT. Its versioned schemas, fixtures, and conformance suite do
not reinterpret Core v0.1.

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

`docs/core/` contains the normative AICP Core specification artifacts used by implementers and conformance tooling.

## Canonical normative source

- Canonical normative text (edited in PRs): `docs/core/AICP_Core_v0.1_Normative.md`
- Optional/release-only artifact: `docs/core/AICP_Core_v0.1_Normative_0.1.0.docx`

The Markdown document is canonical for normal development and review workflows. The `.docx` file is not edited in normal PRs and is treated as an optional release artifact.
The `.docx` artifact may contain outdated branding until it is regenerated in release tooling.

## Validate Core artifacts

From repo root run:

- `make validate`
- `make test`

Related machine-readable artifacts:
- schemas: `schemas/core/`
- fixtures: `fixtures/`
