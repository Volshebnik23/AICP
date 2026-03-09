# RFC: Artifact Manifests and Contract Pinning (M30 baseline)

## 1. Scope (normative)
This RFC defines a minimal, offline-verifiable supply-chain baseline for AICP tool/resource/prompt usage.

The baseline adds:
- canonical artifact manifest objects,
- issuer-scoped anti-shadowing identity,
- contract-level pinning,
- required TOOL_CALL_REQUEST binding to pinned manifests.

This baseline extends existing `EXT-TOOL-GATING` behavior. It does not replace gating verdict/result semantics.

## 2. Canonical manifest objects (normative)
The baseline object model is `artifact_manifest` with `artifact_kind` values:
- `tool`
- `resource`
- `prompt`

Required fields:
- `manifest_id` (stable identifier)
- `artifact_kind`
- `issuer_id`
- `issuer_scoped_id` (MUST be issuer-scoped identity)
- `version`
- `interface_version`
- `description`
- `risk_class`
- `content_hash`

Optional:
- minimal `metadata`
- `signature` attribution block

Schema reference: `schemas/extensions/ext-artifact-manifests-pinning.schema.json#/$defs/artifact_manifest`

## 3. Anti-shadowing and namespacing (normative)
`issuer_scoped_id` MUST be issuer-qualified (`issuer_id#manifest_id` equivalence by value).

Implementations MUST reject collision/shadowing where the same apparent `manifest_id` is used with a different `issuer_id` than the one pinned by contract.

## 4. Contract pinning model (normative)
A governed contract that enables this baseline MUST include `contract.ext.artifact_pinning` (or `contract.extensions["EXT-ARTIFACT-PINNING"]`) with:
- `manifest_set_hash`
- `pinned_artifacts[]` entries (`artifact_kind`, `manifest_id`, `issuer_id`, `issuer_scoped_id`, `version`, `content_hash`)

Optional `manifests[]` may carry full manifest objects for transcript-local verification.

Silent manifest drift is forbidden:
- Any change to pinned version/hash/issuer MUST use explicit renegotiation (`CONTEXT_AMEND` or equivalent contract update flow).
- A tool call against unamended pins MUST fail conformance.

## 5. TOOL_CALL_REQUEST linkage (normative)
When contract pinning is active, `TOOL_CALL_REQUEST.payload.manifest_ref` MUST be present and MUST match an active pinned artifact:
- `manifest_id`
- `issuer_id`
- `issuer_scoped_id`
- `version`
- `content_hash`

`EXT-TOOL-GATING` verdict/result/attest checks remain unchanged. M30 adds supply-chain integrity constraints before/alongside gating decisions.

## 6. Baseline conformance expectations (normative)
M30 baseline conformance MUST verify:
- manifest/pinning schema validity,
- issuer-scoped anti-shadowing,
- manifest hash/pin integrity,
- contract pinning enforcement on tool requests,
- expected-fail rug-pull case,
- expected-fail shadowing case,
- expected-pass explicit renegotiated upgrade.

## 7. Deferred topics (non-goals of this baseline)
Explicitly deferred:
- online transparency log ecosystems,
- package repository lifecycle semantics,
- federated discovery/trust-service protocols,
- richer governance/policy stacks beyond baseline pinning.
