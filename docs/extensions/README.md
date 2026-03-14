# Extensions index and maturity notes

Extension RFCs live in this folder (`docs/extensions/`).

## How to read maturity in this repo

- **Registry presence** means an identifier exists and is tracked (`registry/extension_ids.json`).
- **Schema/fixtures/conformance presence** means there is machine-checkable artifact coverage.
- **Milestone shipped status** is decided in `ROADMAP.md` (source of truth), and MUST remain aligned with executable schema/fixture/conformance evidence in this repo.
- RFC **experimental/stable** labels describe extension maturity and are related to, but not identical with, milestone shipped completion in the roadmap.

## Current phase summary

- Core transport/binding executable baseline remains centered on the shipped M22 conformance/CI surface.
- M23 (`RFC_EXT_CONFIDENTIALITY.md`) is shipped with executable extension conformance coverage.
- M24 (`RFC_EXT_REDACTION.md`) is shipped with executable schema/fixture/conformance coverage for redaction declarations, retention/deletion policy, `pii_ref` handling, and deterministic fail vectors.
- M26 (`RFC_EXT_HUMAN_APPROVAL.md`) is shipped with executable extension conformance coverage (approval/step-up primitives).
- M28 (`RFC_EXT_IAM_BRIDGE.md`) is shipped with executable extension conformance coverage for issuer/scopes/roles/groups mapping, delegated-identity binding linkage, and step-up/approval checks.
- M27 (`RFC_EXT_OBSERVABILITY.md`) is shipped with executable extension conformance coverage for transcript-level tracing, SLA/error signaling, and normalized metering events.
- M29 (enterprise bindings) is pending; roadmap status is intentionally ahead-guarded until RFC/schema/fixtures/conformance artifacts are present on public `main`.


## Where to look next

- Extension IDs: `registry/extension_ids.json`
- Extension suites: `conformance/extensions/`
- Roadmap status: `ROADMAP.md`
