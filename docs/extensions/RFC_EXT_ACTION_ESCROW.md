# RFC: EXT-ACTION-ESCROW (experimental)

## Message types (normative) {#message-types-normative}
ACTION_PREPARE, ACTION_APPROVE, ACTION_COMMIT.

## Normative behavior
ACTION_COMMIT MUST bind tool_call_request_hash + approval_hash + policy_context_hash.

## Registry entry {#registry-entry}
`EXT-ACTION-ESCROW` experimental.
