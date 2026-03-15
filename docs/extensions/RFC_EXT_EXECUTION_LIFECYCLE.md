# RFC_EXT_EXECUTION_LIFECYCLE (EXT-EXECUTION-LIFECYCLE)

## 1. Summary

`EXT-EXECUTION-LIFECYCLE` defines a minimal, transcript-native execution interoperability surface for portable run/thread lifecycle metadata and hash-bound store/memory references.

This extension is optional and transport-independent. It standardizes auditable metadata semantics; it does **not** standardize a hosted runtime, scheduler, or store API.

## 2. Scope boundaries (normative)

This extension is:
- content-layer,
- transport-agnostic,
- optional by profile/deployment,
- designed for deterministic conformance checking from transcript evidence.

This extension is **not**:
- an execution engine protocol,
- a workflow scheduler API,
- a hosted store/memory service protocol,
- a replacement for `EXT-RESUME` and `EXT-OBJECT-RESYNC` recovery semantics.

## 3. Message types (normative) {#message-types-normative}

- `RUN_CREATE`
- `RUN_UPDATE`
- `RUN_CANCEL`
- `RUN_COMPLETE`
- `THREAD_CREATE`
- `THREAD_APPEND`
- `THREAD_CLOSE`

## 4. Payload model (normative)

### 4.1 Run lifecycle objects
All run lifecycle messages MUST include `run_id`.

`RUN_CREATE` MUST initialize a run lifecycle.
`RUN_UPDATE` MAY mutate non-terminal run metadata before terminal state.
`RUN_CANCEL` sets terminal canceled state.
`RUN_COMPLETE` sets terminal completed state.

### 4.2 Thread lifecycle objects
All thread lifecycle messages MUST include `thread_id`.

`THREAD_CREATE` MUST initialize thread lifecycle.
`THREAD_APPEND` MAY append thread events before close.
`THREAD_CLOSE` sets terminal closed state.

### 4.3 Portable store/memory references
`store_ref` and `memory_ref` are portable, hash-bound references and MUST NOT be interpreted as vendor-specific API handles.

Reference object MUST include:
- `ref_id`
- `object_hash`
- `object_type`
- `access` constraint object

`access` MUST include machine-checkable constraints (for example access mode, policy/access constraint, and whether object-resolution evidence is required).

## 5. Lifecycle semantics (normative)

### 5.1 Run ordering and terminal behavior
- `RUN_UPDATE`, `RUN_CANCEL`, and `RUN_COMPLETE` MUST reference a previously created `run_id`.
- `RUN_UPDATE` MUST fail if emitted before `RUN_CREATE`.
- A terminal run state (`RUN_CANCEL` or `RUN_COMPLETE`) MUST be unique per `run_id`.
- Any run mutation after terminal state MUST fail.

### 5.2 Thread ordering and close behavior
- `THREAD_APPEND` and `THREAD_CLOSE` MUST reference a previously created `thread_id`.
- `THREAD_APPEND` MUST fail after `THREAD_CLOSE`.
- Repeated `THREAD_CLOSE` for a closed thread MUST fail.

### 5.3 Cross-binding coherence
When run and thread identifiers are cross-bound in payloads (for example `RUN_CREATE.thread_id` or `THREAD_CREATE.run_id`), declared bindings MUST remain coherent through subsequent lifecycle events.

## 6. Recovery/resync/tooling mapping guidance

- `EXT-RESUME`: interruption/reconnect metadata SHOULD map to `run_id`/`thread_id` continuity and head hash checkpoints.
- `EXT-OBJECT-RESYNC`: `store_ref`/`memory_ref` object retrieval SHOULD use `OBJECT_REQUEST`/`OBJECT_RESPONSE` by `object_hash`.
- `EXT-TOOL-GATING`: optional pairing for side-effecting execution approvals/policy gates; not required for baseline execution interop profile.

## 7. Conformance expectations (normative)

Conformance suite MUST include:
- pass run lifecycle ordering,
- pass thread lifecycle ordering,
- pass hash-bound store/memory reference with object-resync evidence,
- expected-fail run mutation before create,
- expected-fail post-terminal mutation,
- expected-fail append after thread close,
- expected-fail dangling unresolved store/memory reference.

## 8. Security considerations

- Prevent stale-state replay by validating lifecycle ordering and terminal-state immutability.
- Prevent cross-thread/run confusion by enforcing declared identifier bindings.
- Prevent dangling-reference abuse by requiring hash-bound references and resolution evidence when policy demands it.
- Avoid post-terminal mutation acceptance.
- Avoid leaking unauthorized store access details in plaintext payload fields.

## 9. Privacy considerations

- Use hash references and policy-constrained access objects instead of embedding raw sensitive store content.
- Avoid exposing vendor-internal access tokens/handles in transcript payloads.

## 10. Registry entry {#registry-entry}

`EXT-EXECUTION-LIFECYCLE` is registered in `registry/extension_ids.json`, with corresponding lifecycle message types in `registry/message_types.json`.
