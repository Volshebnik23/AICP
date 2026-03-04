# RFC: EXT-QUEUE-LEASES (experimental)

## Message types (normative) {#message-types-normative}
QUEUE_ENQUEUE, QUEUE_LEASE_GRANT, QUEUE_ACK, QUEUE_NACK, QUEUE_RELEASE, OVERLOAD_SIGNAL, THROTTLE_UPDATE.

## Normative behavior
Lease terms include `lease_id`,`ttl_seconds`,`max_msgs`,`max_bytes`,`max_attachments`,`allowed_message_types`,`allowed_mime_types`,`allowed_formats`.
If lease-required by contract, mediator MUST deny/delay content not covered by active lease.

## Security considerations
Bounded lease windows and explicit overload signaling are required.

## Registry entry {#registry-entry}
`EXT-QUEUE-LEASES` experimental.
