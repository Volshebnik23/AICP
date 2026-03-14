# RFC_EXT_ENTERPRISE_BINDINGS (EXT-ENTERPRISE-BINDINGS)

Status: Experimental  
AICP Version: 0.1

## 1. Purpose

`EXT-ENTERPRISE-BINDINGS` defines a transcript-native enterprise binding/reference layer so AICP workflows can map to existing enterprise API, retrieval, and policy surfaces without turning AICP into a runtime adapter or policy engine.

This extension standardizes machine-checkable references for:
- OpenAPI operation bindings for tool calls,
- OData retrieval target bindings,
- policy cross-references for ABAC/RBAC/OPA-oriented controls.

## 2. Scope boundaries (normative)

This extension is **not**:
- an OpenAPI client/runtime invoker,
- an OData parser/server/client implementation,
- an ABAC/RBAC/OPA engine,
- a vendor-specific governance connector.

Conformance MUST remain transcript-verifiable from schema + fixtures + deterministic checks.

## 3. Message surface (normative)

`EXT-ENTERPRISE-BINDINGS` uses extension objects on existing payloads:
- `CONTRACT_PROPOSE.payload.contract.ext.enterprise_bindings`
- `TOOL_CALL_REQUEST.payload.ext.enterprise_bindings`

No new core message family is required for this extension.

## 4. Contract enterprise-binding object (normative)

`contract.ext.enterprise_bindings` includes:
- `openapi_bindings` (MUST): one or more OpenAPI tool-operation binding objects.
- `odata_bindings` (MUST): one or more OData retrieval binding objects.
- `policy_xrefs` (MUST): one or more policy cross-reference objects.
- `requires_obs_correlation` (MAY): when true, at least one bound tool activity must correlate with `OBS_SIGNAL` evidence.

All binding identifiers and references MUST be deterministic, non-empty, and hash-friendly.

## 5. OpenAPI tool-operation binding semantics (normative)

Each `openapi_binding` object:
- `binding_id` (MUST): stable local binding identifier.
- `spec_ref` (MUST): stable reference to external API spec/version/digest.
- `operation_id` (MUST): external operation mapping identifier.
- `tool_id` (MUST): AICP tool target identifier.
- `projection_ref` (MAY): normalized projection/mapping reference for parameters/results.
- `auth_ref` / `policy_ref` (MAY): external control references.
- `binding_version` / `namespace` (MAY): versioning/segmentation metadata.

Rules:
- full OpenAPI document blobs MUST NOT be embedded in transcript payloads.
- binding objects MUST remain audit-friendly and transport-independent.

## 6. OData retrieval binding semantics (normative)

Each `odata_binding` object:
- `binding_id` (MUST): stable local binding identifier.
- `service_ref` (MUST): stable service/model reference token.
- `target_ref` (MUST): entity set / collection / retrieval target reference.
- `select_ref`, `filter_ref`, `orderby_ref`, `page_ref` (MAY): normalized query-shape references.
- `binding_version` / `namespace` (MAY): versioning/segmentation metadata.

Rules:
- this extension defines retrieval binding references, not a full OData grammar.
- transcript entries MUST stay compact and deterministic.

## 7. Policy cross-reference semantics (normative)

Each `policy_xref` object:
- `xref_id` (MUST): stable cross-reference identifier.
- `policy_kind` (MUST): one of `abac`, `rbac`, `opa`.
- `policy_ref` (MUST): stable reference to external policy artifact.
- `subject_ref`, `resource_ref`, `action_ref` (MAY): normalized policy dimension references.
- `opa_package_ref` (MAY): package/module reference when `policy_kind=opa`.

Rules:
- policy xrefs are descriptive bindings, not policy execution semantics.
- this extension MUST NOT claim completion of M25 semantic interoperability profiles.

## 8. Tool-call binding reference semantics (normative)

`TOOL_CALL_REQUEST.payload.ext.enterprise_bindings.binding_ref_id` MUST reference a declared `binding_id` from either:
- `openapi_bindings`, or
- `odata_bindings`.

References MUST be internally consistent and transcript-auditable.

## 9. Conformance expectations

Conformance MUST include checks for:
- OpenAPI binding shape and operation linkage,
- OData binding shape and retrieval target linkage,
- policy cross-reference presence and supported policy kinds,
- binding reference integrity from tool calls to declared binding objects,
- coherent enterprise-binding linkage with M28 IAM bridge actions,
- coherent enterprise-binding linkage with M26 approval-governed tool execution,
- observability correlation for enterprise-bound activity when required by contract.

## 10. Security considerations

- Example: if `TOOL_CALL_REQUEST.ext.enterprise_bindings.binding_ref_id` resolves to an unpinned or unknown binding, fail closed rather than inferring runtime mapping from tool name alone.

- Treat external `spec_ref`/`policy_ref`/`service_ref` values as sensitive governance metadata in high-assurance deployments.
- Validate all external references and identifiers at transcript ingestion boundaries.
- Keep binding IDs deterministic and non-guessable where correlation leakage is a concern.
- Bind enterprise references to signed/hash-chained transcript context to resist substitution/replay.

## 11. Privacy considerations

- Prefer stable references over raw enterprise payloads or policy documents.
- Avoid embedding sensitive query literals, credentials, or full policy text.
- Minimize subject/resource identifiers to least disclosure required for auditability.

## 12. Relationship to M27, M28, and M25

- M27 (`EXT-OBSERVABILITY`): M29 bindings can require transcript-level `OBS_SIGNAL` correlation for bound tool activity.
- M28 (`EXT-IAM-BRIDGE`): M29 policy/action xrefs can align with IAM bridge action references.
- M25 (policy semantic interoperability profiles): M29 provides cross-reference bindings only; it does not complete M25 semantic profile standardization.

## 13. Registry entry

- `EXT-ENTERPRISE-BINDINGS` in `registry/extension_ids.json`.
