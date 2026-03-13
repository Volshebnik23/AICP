# Extensions index and maturity notes

Extension RFCs live in this folder (`docs/extensions/`).

## How to read maturity in this repo

- **Registry presence** means an identifier exists and is tracked (`registry/extension_ids.json`).
- **Schema/fixtures/conformance presence** means there is machine-checkable artifact coverage.
- **Milestone shipped status** is decided in `ROADMAP.md` (source of truth), not by document presence alone.

## Current phase summary

- Core transport/binding executable baseline remains centered on the shipped M22 conformance/CI surface.
- M23 (`RFC_EXT_CONFIDENTIALITY.md`) is shipped with executable extension conformance coverage.
- M24 (`RFC_EXT_REDACTION.md`) is now represented as shipped in roadmap terms for its protocol deliverables (redaction declaration + retention/deletion policy + pii_ref + conformance).

## Where to look next

- Extension IDs: `registry/extension_ids.json`
- Extension suites: `conformance/extensions/`
- Roadmap status: `ROADMAP.md`
