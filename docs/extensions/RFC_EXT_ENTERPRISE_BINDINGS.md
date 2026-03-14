# RFC EXT-ENTERPRISE-BINDINGS

- **Extension ID:** `EXT-ENTERPRISE-BINDINGS`
- **Status:** Experimental
- **Category:** Extension RFC
- **Version:** 0.1
- **Last updated:** 2026-03-14

## 1. Purpose and scope

`EXT-ENTERPRISE-BINDINGS` defines a **content-layer binding/reference model** for linking AICP-governed actions to external enterprise artifacts.

This extension is intentionally narrow:
- It standardizes binding objects and cross-references.
- It preserves transcript-level auditability and deterministic hashability.
- It does **not** define runtime adapters, vendor-specific connectors, or transport behavior.

## 2. Out of scope

This extension does not:
- embed full OpenAPI or OData documents in transcript payloads;
- implement OpenAPI/OData execution engines;
- replace enterprise IAM or policy engines;
- complete M25 policy semantic interoperability profiles.

## 3. Contract-level enterprise bindings

Enterprise bindings are declared under:
- `CONTRACT_PROPOSE.payload.contract.ext.enterprise_bindings`

The contract object includes:

1) **OpenAPI tool-operation bindings** (`openapi_bindings`)
- `binding_id`: stable local binding identifier.
- `spec_ref`: stable external spec reference (URL, digest URI, registry ref).
- `operation_id`: operation-level identifier.
- `tool_id`: mapped AICP tool identifier.
- optional projection/policy hooks (`projection_ref`, `policy_ref`) and namespace/version fields.

2) **OData retrieval bindings** (`odata_bindings`)
- `binding_id`: stable local binding identifier.
- `service_ref`: stable OData service/model reference.
- `target_ref`: normalized retrieval target (entity set / collection key).
- optional normalized query-shape references (`select_ref`, `filter_ref`, `order_ref`, `page_ref`).

3) **Policy cross-reference bindings** (`policy_xrefs`)
- `xref_id`: stable local policy-xref identifier.
- `policy_kind`: policy family (`abac`, `rbac`, `opa`) validated semantically.
- `policy_ref`: external policy reference.
- optional subject/resource/action mapping references and OPA package/module pointers.

Optional contract switch:
- `requires_obs_correlation` (boolean) to require M27 correlation evidence for enterprise-bound calls.

## 4. Message-level binding linkage

Enterprise-bound tool calls include:
- `TOOL_CALL_REQUEST.payload.ext.enterprise_bindings.binding_ref_id`

`binding_ref_id` MUST resolve to a declared `binding_id` from either `openapi_bindings` or `odata_bindings` in the active contract.

Optional message ext coexistence with shipped controls:
- `payload.ext.iam_bridge` (M28 linkage)
- `payload.ext.human_approval` (M26 linkage)

## 5. Conformance expectations

`EB_ENTERPRISE_BINDINGS_0.1` verifies:
- OpenAPI binding presence/shape and operation linkage.
- OData binding presence/shape and target linkage.
- Policy xref object presence and policy kind validity.
- Internal reference integrity (`binding_ref_id` resolution).
- Coherent linkage with M28 IAM bridge semantics.
- Coherent linkage with M26 approval evidence.
- Optional required correlation with M27 `OBS_SIGNAL` evidence.

Schema-vs-semantic layering:
- schema validates structure and required fields;
- conformance checks validate policy-kind allowlist, cross-object linkage, and transcript evidence integrity.

## 6. Relationship to adjacent milestones

- **M27 Observability:** this extension can require observability correlation evidence via `requires_obs_correlation` and `OBS_SIGNAL.correlation_ref.tool_call_id` linkage.
- **M28 IAM bridge:** enterprise-bound calls may carry IAM action refs that must align to policy xrefs.
- **M25 policy semantics:** this extension references ABAC/RBAC/OPA policy surfaces but does not claim full semantic interoperability profile completion.

## 7. Security considerations

Implementations should:
- treat external refs as untrusted input until policy-validated;
- prevent confused-deputy behavior by requiring explicit `binding_ref_id` linkage;
- bind approvals/IAM/observability evidence to concrete tool-call IDs;
- avoid runtime privilege escalation via implicit external-policy resolution.

## 8. Privacy considerations

Implementations should:
- avoid embedding raw enterprise policy documents, sensitive identity attributes, or full query strings when stable refs suffice;
- minimize tenant-identifying data in binding refs;
- ensure policy and retrieval refs can be audited without exposing protected payload contents.

## 9. Registry entry

`registry/extension_ids.json` MUST include `EXT-ENTERPRISE-BINDINGS` with this RFC as `spec_ref`.
