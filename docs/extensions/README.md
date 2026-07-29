# Extensions index and maturity notes

Extension RFCs live in this folder (`docs/extensions/`).

## How to read maturity in this repo

- **Registry presence** means an identifier exists and is tracked (`registry/extension_ids.json`).
- **Schema/fixtures/conformance presence** means there is machine-checkable artifact coverage.
- **Milestone shipped status** is decided in `ROADMAP.md` (source of truth), and MUST remain aligned with executable schema/fixture/conformance evidence in this repo.
- RFC **experimental/stable** labels describe extension maturity and are related to, but not identical with, milestone shipped completion in the roadmap.

## Current phase summary

- M61 (`RFC_EXT_CAPNEG_v0.2.md`) is shipped as a separate experimental CAPNEG surface for
  canonical Core v0.1-family profile-set negotiation. Stable CAPNEG v0.1 remains unchanged;
  v0.2 internal evidence does not award component profile marks or external composition
  evidence.
- Core transport/binding executable baseline remains centered on the shipped M22 conformance/CI surface.
- M23 (`RFC_EXT_CONFIDENTIALITY.md`) is shipped with executable extension conformance coverage.
- M24 (`RFC_EXT_REDACTION.md`) is shipped with executable schema/fixture/conformance coverage for redaction declarations, retention/deletion policy, `pii_ref` handling, and deterministic fail vectors.
- M26 (`RFC_EXT_HUMAN_APPROVAL.md`) is shipped with executable extension conformance coverage (approval/step-up primitives).
- M28 (`RFC_EXT_IAM_BRIDGE.md`) is shipped with executable extension conformance coverage for issuer/scopes/roles/groups mapping, delegated-identity binding linkage, and step-up/approval checks.
- M27 (`RFC_EXT_OBSERVABILITY.md`) is shipped with executable extension conformance coverage for transcript-level tracing, SLA/error signaling, and normalized metering events.
- M29 (`RFC_EXT_ENTERPRISE_BINDINGS.md`) is shipped with executable extension conformance coverage for OpenAPI/OData binding references and ABAC/RBAC/OPA policy cross-references.
- M31 (`RFC_EXT_TRANSCRIPT_WITNESS.md`) is shipped with executable checkpoint/receipt/head-exchange/inclusion-proof witness conformance and equivocation detection checks.
- M32 (`RFC_EXT_EXECUTION_LIFECYCLE.md`) is shipped with executable run/thread lifecycle ordering, terminal-state guardrails, and store-ref/object-resync linkage checks under the optional execution interop profile.
- M35 (`RFC_EXT_ADMISSION.md`, `RFC_EXT_QUEUE_LEASES.md`) is shipped with executable admission/queue-lease crowd-control conformance coverage and explicit overload signaling.
- M36 (`RFC_EXT_MARKETPLACE.md`) is shipped with executable marketplace/orchestration conformance coverage for RFW/bid/award, auction modes, blackboard workflows, and subchat admission-aware routing.
- M37 (`RFC_EXT_PROVENANCE.md`, `RFC_EXT_RESPONSIBILITY.md`, `RFC_EXT_ACTION_ESCROW.md`) is shipped with executable provenance DAG append checks, responsibility transfer lifecycle + chain-failure attest coverage, and escrow prepare/approve/commit hash-binding enforcement.
- M38 (`RFC_EXT_CHANNELS.md`, `RFC_EXT_SUBSCRIPTIONS.md`, `RFC_EXT_PUBLICATIONS.md`, `RFC_EXT_INBOX.md`) is shipped with executable channel hierarchy, subscription cursor/state, publication delivery/retraction-reason semantics, and inbox lease/ack linkage checks.

- M40 (`RFC_EXT_EXTERNAL_TRANSACTION.md`) is shipped with executable protocol-neutral external transaction declaration/result linkage, approval/policy evidence binding, receipt-digest anchoring, and privacy-safe `pii_ref` coverage.


## Where to look next

- Extension IDs: `registry/extension_ids.json`
- Extension suites: `conformance/extensions/`
- Roadmap status: `ROADMAP.md`
- CAPNEG v0.1 single-profile RFC: `docs/extensions/RFC_EXT_CAPNEG.md`
- CAPNEG v0.2 multi-profile RFC: `docs/extensions/RFC_EXT_CAPNEG_v0.2.md`
- Session-state projection v2: `docs/extensions/SESSION_STATE_PROJECTION_v2.md`
