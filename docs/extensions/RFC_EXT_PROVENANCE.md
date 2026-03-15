# RFC_EXT_PROVENANCE (EXT-PROVENANCE)

## 1. Summary

`EXT-PROVENANCE` defines transcript-native provenance DAG artifacts for multi-agent chains.
The goal is auditable append-only lineage across agents, tools, workflow hops, and derived artifacts.

## 2. Scope and non-goals

This extension standardizes provenance declarations and append operations.
It does not define trust-anchor PKI, legal liability semantics, or external workflow engines.

## 3. Message types (normative) {#message-types-normative}

- `PROVENANCE_DECLARE`
- `PROVENANCE_APPEND`

## 4. Payload semantics (normative)

### 4.1 PROVENANCE_DECLARE
`payload` MUST include:
- `graph_id`
- `nodes` (non-empty array)

Each node MUST include:
- `node_id`
- `node_type` ∈ `artifact_node | transform_node | decision_node`

Node references MUST be transcript-auditable (hash refs, artifact refs, workflow refs, policy refs).

### 4.2 PROVENANCE_APPEND
`payload` MUST include:
- `graph_id` (must reference prior `PROVENANCE_DECLARE`)
- `node` (single node append)

`PROVENANCE_APPEND` is append-only:
- node IDs MUST NOT be reused within a graph,
- parent linkage references MUST resolve to known prior nodes.

## 5. Conformance expectations (normative)

Conformance suites for `EXT-PROVENANCE` MUST include:
- pass transcript with multi-agent DAG linkage,
- expected-fail transcript for missing/incoherent linkage,
- expected-fail transcript for append context violations.

## 6. Security considerations

- Prefer hash-bound references for artifact/workflow/policy objects.
- Provenance nodes should avoid embedding sensitive raw content where references suffice.
- Append-only linkage should be enforced by policy and conformance tooling.

## 7. Registry entry {#registry-entry}

`EXT-PROVENANCE` in `registry/extension_ids.json`.
