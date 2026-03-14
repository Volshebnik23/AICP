# RFC_EXT_ENTERPRISE_BINDINGS (EXT-ENTERPRISE-BINDINGS)

Status: Experimental  
AICP Version: 0.1

## 1. Purpose

`EXT-ENTERPRISE-BINDINGS` defines a conservative, transcript-auditable reference layer for enterprise integration mapping:

- OpenAPI operation bindings for AICP tool actions,
- OData retrieval bindings for query/data targets,
- ABAC/RBAC/OPA policy cross-references.

This extension standardizes binding metadata. It does **not** implement enterprise runtime adapters.

## 2. Scope boundaries (normative)

This extension is **not**:

- an OpenAPI client/runtime,
- an OData server/client implementation,
- a policy engine,
- a vendor-specific connector framework.

Payloads MUST remain content-layer, transport-neutral, and hashable.

## 3. Binding model overview (normative)

Binding objects SHOULD be declared at contract level:

- `CONTRACT_PROPOSE.payload.contract.ext.enterprise_bindings`

Message-level usage MAY reference those bindings from relevant actions.

## 4. OpenAPI binding semantics (normative)

Each `openapi_binding` object MUST include:

- `binding_id` (non-empty string)
- `spec_ref` (stable external spec reference token)
- `tool_id` (AICP tool identifier)

Optional fields:

- `operation_id` (OpenAPI operation identifier)
- `projection_ref` (parameter/result projection reference)
- `policy_ref` (external policy reference)
- `binding_version` (binding schema/version token)

Rules:

- full OpenAPI document blobs MUST NOT be embedded.
- references MUST be stable enough for transcript-level audit.

## 5. OData retrieval binding semantics (normative)

Each `odata_binding` object MUST include:

- `binding_id`
- `service_ref` (stable OData service/model reference)
- `target_ref` (entity set/collection target)

Optional fields:

- `query_profile_ref` (normalized retrieval-profile reference)
- `projection_ref`
- `binding_version`

Rules:

- this extension does not define an OData parser.
- bindings are references, not runtime query execution instructions.

## 6. Policy cross-reference semantics (normative)

Each `policy_xref` object MUST include:

- `xref_id`
- `policy_kind` (`abac`, `rbac`, or `opa`)
- `policy_ref`

Optional fields:

- `subject_ref`
- `resource_ref`
- `action_ref`
- `opa_package_ref`
- `authority_map_ref`

Rules:

- policy cross-references are mapping hints and audit references.
- this extension does not claim full M25 semantic interoperability profile completion.

## 7. Conformance expectations

Conformance MUST verify at least:

- OpenAPI binding integrity (`spec_ref`, target tool linkage, operation reference semantics),
- OData binding integrity (service and target reference semantics),
- policy xref shape and allowed policy kinds,
- transcript-level linkage with M28 IAM-aware actions,
- transcript-level linkage with M26 approval/intervention-governed actions,
- transcript-level linkage with M27 observability correlation evidence,
- internal reference integrity for binding IDs/targets.

## 8. Security considerations

- Treat enterprise binding references as policy-sensitive metadata.
- Avoid embedding secrets, credentials, or raw tokens in binding refs.
- Keep policy references explicit to reduce ambiguity during audit.

## 9. Privacy considerations

- Do not leak sensitive enterprise schema content by embedding full external documents.
- Prefer stable reference tokens and projection/profile refs.
- Keep subject/resource identifiers minimal and purpose-bound.

## 10. Relationship to M27, M28, and M25

- M27 (`EXT-OBSERVABILITY`): enterprise-bound actions can be correlated with `OBS_SIGNAL` artifacts.
- M28 (`EXT-IAM-BRIDGE`): enterprise bindings can reference actions governed by IAM-mapped authority.
- M25 policy semantic interoperability profiles: adjacent and partially preparatory; **not completed** by this extension.

## 11. Registry entry

- `EXT-ENTERPRISE-BINDINGS` in `registry/extension_ids.json`.
