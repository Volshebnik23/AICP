11. RFC: Transport bindings (Registered Extensions)

11.2 BIND-MCP-0.1 — Binding over MCP (normative)
Model: an MCP server ("aicp-bridge") exposes tools and resources to exchange AICP envelopes. The bridge MAY be local (sidecar) or remote. If privacy_mode disallows relay visibility, payload MUST be protected before passing through a remote bridge.
Required MCP tools (normative minimum):
•	aicp.sendMessage(envelope) -> {accepted, error_envelope?, head_version?, cursor?}
•	aicp.pollMessages(session_id, after_cursor?, limit?) -> {messages[], next_cursor?}
•	aicp.getHead(session_id) -> {session_state, branch_heads, active_head_version?, final_head_version?}
•	aicp.getObject(object_hash) -> {status, object_type?, object_json?, artifact_ref?}
Recommended MCP resources (informative): aicp://sessions/{session_id}/head, aicp://objects/{object_hash}, aicp://sessions/{session_id}/messages?after=...
Delivery semantics: at-least-once is assumed. Receivers MUST be idempotent by message_id. Ordering MUST NOT be assumed; use contract_ref/base_version and message hash chaining when available.

Productized artifacts (M7.4):
- Binding schema: `schemas/bindings/bind-mcp.schema.json`
- Binding fixtures: `fixtures/bindings/mcp/TB-MCP-01_sendMessage.json`, `fixtures/bindings/mcp/TB-MCP-02_getHead.json`, `fixtures/bindings/mcp/TB-MCP-03_getObject.json`
- Binding conformance suite: `conformance/bindings/TB_MCP_0.1.json`

Verification command:
- `make conformance-bindings`


Compatibility note: `EXT-BIND-MCP` is a deprecated alias retained only for backward compatibility. New negotiations and evidence MUST use `BIND-MCP-0.1`.


## BIND-MCP stable compatibility notes {#bind-mcp-stable}
- `BIND-MCP-0.1` is the canonical stable identifier for MCP transport negotiation and compatibility evidence.

## EXT-BIND-MCP deprecation notes {#bind-mcp-compatibility-note}
- `EXT-BIND-MCP` is a deprecated alias retained only for backward compatibility during migration.
