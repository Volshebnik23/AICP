# RFC: EXT-FACILITATION (experimental)

## Message types (normative) {#message-types-normative}
AGENDA_DECLARE, AGENDA_UPDATE, TURN_REQUEST, TURN_GRANT, TURN_REVOKE, DIGEST_REQUEST, DIGEST_DELIVER, MODERATOR_DIRECTIVE.

## Normative behavior
When facilitation requires turns, content SHOULD request/grant turns first and platforms MAY enforce MUST.

## Security considerations
Directives and grants must be authenticated and auditable.

## Registry entry {#registry-entry}
`EXT-FACILITATION` experimental.
