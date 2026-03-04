# RFC: EXT-ADMISSION (experimental)

## Message types (normative) {#message-types-normative}
ADMISSION_REQUEST, ADMISSION_OFFER, ADMISSION_ACCEPT, ADMISSION_REJECT, ADMISSION_RENEW, ADMISSION_REVOKE.

## Normative behavior
If admission is required, participants MUST NOT be accepted before ADMISSION_ACCEPT evidence.

## Security considerations
Admission artifacts MUST be authenticated/revocable.

## Registry entry {#registry-entry}
`EXT-ADMISSION` experimental.
