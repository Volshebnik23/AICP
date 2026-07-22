13. RFC: EXT-OBJECT-RESYNC — Object retrieval and state resync (Registered Extension)
EXT-OBJECT-RESYNC provides a transport-independent recovery mechanism to fetch missing objects by object_hash and to resynchronize minimal session state. It is essential for real deployments with reordering, partial replication, offline operation, and third-party observation.
13.1 Message types (normative)
•	OBJECT_REQUEST — request one or more objects by object_hash.
•	OBJECT_RESPONSE — return objects or statuses for requested hashes.
•	STATE_SYNC_REQUEST — request minimal session state (heads, closed status, hints).
•	STATE_SYNC_RESPONSE — return minimal session state and replication hints.
13.2 OBJECT_REQUEST payload (normative minimum)
•	request_id (MUST): identifier for idempotency and correlation.
•	objects (MUST): list of {object_hash (MUST), want_type (MAY), max_bytes (MAY)}.
•	allow_redaction (SHOULD): whether REDACTED responses are acceptable.
•	allow_encrypted (MAY): whether encrypted objects are acceptable (binding/profile dependent).
•	max_total_bytes (MAY): receiver may cap response size.
13.3 OBJECT_RESPONSE payload (normative minimum)
OBJECT_RESPONSE MUST include request_id and entries[]. Each entry MUST include: object_hash, status, and (if status=FOUND) object_type and object_json (or artifact_ref).
status MUST be one of: FOUND | NOT_FOUND | ACCESS_DENIED | TOO_LARGE | REDACTED | ERROR.
If status=FOUND and object_json is provided, the receiver MUST ensure that re-hashing the object_json under the declared object_type yields object_hash.
13.4 STATE_SYNC_* payloads (normative minimum)
STATE_SYNC_REQUEST MUST include: request_id (MUST), known_heads (MAY), known_message_hash (MAY), want_closed_status (MAY).
STATE_SYNC_RESPONSE MUST include: request_id (MUST), session_state (MUST), branch_heads (MUST), active_head_version (MAY), final_head_version (MAY), replication_hints (MAY).
13.5 Security and privacy considerations (normative intent)
•	Implementations SHOULD mitigate DoS/amplification (rate limits, max bytes, chunking via artifact_ref, and TOO_LARGE responses).
•	Object existence leakage is a security concern; implementations MAY respond with ACCESS_DENIED instead of NOT_FOUND based on policy.
•	Redaction MUST be explicit (status=REDACTED) and SHOULD include redaction_note. Receivers MUST NOT silently alter objects.
13.6 Conformance suite (OR-*) (normative minimum)
•	OR-01: UNKNOWN_BASE_REF -> ERROR with recover_action=FETCH_OBJECT; OBJECT_REQUEST/RESPONSE resolves it.
•	OR-02: HASH_MISMATCH on FOUND object -> reject and raise CRYPTO error.

## Strict portable session-state projection v1

This section defines an experimental, additive shape selected only when
`STATE_SYNC_RESPONSE.payload.session_state.projection_version` is
`aicp.session_state_projection.v1`. It does not change the legacy
`EXT-OBJECT-RESYNC@0.1` session-state form and does not strengthen
`AICP-RESUMABLE-SESSIONS@0.1`. Legacy values remain legacy evidence and are not eligible
for the strict-projection compatibility mark.

The strict projection is an externally portable claim about protocol-visible state. It is
not an internal database, reducer, event-sourcing model, moderation-counter schema, queue,
billing record, or hidden host configuration. A platform MAY compute it by any method.
Chat/mediator, policy, enforcer, and transcript/state functions MAY be co-located,
federated, or distributed; their deployment topology does not alter this wire artifact.

### Projection object

The JSON object MUST conform to `SessionStateProjectionV1` in
`schemas/extensions/ext-object-resync-payloads.schema.json`. It has the following required
members:

- `projection_version`: exactly `aicp.session_state_projection.v1`;
- `session_id` and `contract_id`: the identifiers from the response envelope;
- `as_of_message_hash`: the transcript/head commitment to which the claim applies;
- `session_status`: one of `OPEN`, `SUSPENDED`, `CONFLICTED`, `CLOSED`, or `UNKNOWN`.

The optional members are strict references or registered identifiers:
`active_contract_ref`, `selected_aicp_profile`, `active_extensions`, `participant_refs`,
`policy_refs`, `unresolved_conflict_refs`, `authority_refs`, `evidence_refs`, and
namespaced `extension_data`. Reference arrays MUST contain unique, non-empty references;
large or sensitive state SHOULD remain behind references rather than be copied into the
projection.

### Independent hash binding

The response MUST carry `payload.session_state_hash` outside `session_state`, computed as:

```text
session_state_hash = object_hash("session_state_projection", session_state)
```

`session_state_projection` is a registered hash domain. Keeping the hash outside the
object avoids recursive hashing.

### Checkable invariants

A strict-projection consumer MUST reject the response when any of these checks fails:

- projection `session_id` or `contract_id` differs from the envelope;
- `session_state_hash` does not recompute exactly;
- `as_of_message_hash` is malformed or is not equal to a locally known transcript hash or
  an explicitly declared `branch_heads[].message_hash`;
- `active_contract_ref` is non-canonical or its contract/head contradicts the projected
  envelope/head;
- `active_head_version` contradicts the active contract reference or declared active head;
- `selected_aicp_profile` does not resolve to one exact registered profile ID/version;
- `active_extensions` contains a duplicate, an unregistered identifier, or a value that is
  not an explicitly allowed namespaced identifier;
- a reference is empty, duplicated, points to a future locally ordered transcript message,
  or an evidence reference cannot be resolved where the transcript makes resolution
  checkable;
- `CLOSED` contradicts a different final head, `CONFLICTED` has no unresolved conflict, or
  a non-conflicted status declares unresolved conflicts.

The `as_of_message_hash` need not already be locally materialized: resync may advertise a
remote/missing branch head which the consumer retrieves later. This definition creates no
new ordering, leader, consensus, or finality rule.

### Trust, security, and privacy boundary

The projection hash proves integrity of the projection bytes, not who is authoritative.
Trust in the producer comes from the selected authentication, delegated-identity, trust,
status, or witness profile/evidence. Implementations SHOULD minimize references, apply
access control, and avoid placing private internal state in `extension_data`.

Strict support is tested by `OR_SESSION_STATE_PROJECTION_V1.json`; a complete,
non-degraded pass may emit `AICP-Evidence-SESSION-STATE-PROJECTION-v1`.
