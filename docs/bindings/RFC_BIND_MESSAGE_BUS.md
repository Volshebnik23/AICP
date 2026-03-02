# RFC: BIND-BUS-0.1 — Message bus transport binding

## Overview
`BIND-BUS-0.1` defines interoperable semantics for AICP envelope exchange over message bus infrastructures (for example Kafka/NATS-like transports).

## Normative behavior
- Producers MUST publish complete AICP envelopes; consumers MUST validate envelopes at boundary.
- Implementations MUST document stable topic/subject naming for message and head/state propagation.
- Consumers MUST tolerate duplicate delivery and potential reordering unless ordering is explicitly guaranteed by the deployment.
- Publishers SHOULD key/partition by `session_id` or `message_id` to improve ordering locality, but protocol correctness MUST NOT depend on broker-specific ordering quirks.
- Replay handling MUST be explicit and bounded per deployment policy.

Channel Properties integration (experimental):
- Negotiated `selected.channel_properties` from EXT-CAPNEG SHOULD be used to configure reliability, ordering, ack, and replay behavior per session.
- If negotiated channel properties cannot be enforced on a bus route, implementations MUST reject the negotiation outcome for that route.

## Registry entry {#registry-entry}
- Binding ID: `BIND-BUS-0.1`
- Registry: `registry/transport_bindings.json`
- Status: experimental

## Security considerations
- Bus topics/subjects MUST enforce authorization boundaries to prevent unauthorized publish/consume actions.
- Deployments SHOULD protect against replay storms and duplicate amplification.
- Consumer groups SHOULD validate hash/signature invariants before acting on payload effects.

## Deprecated alias notes
- Deprecated alias: `EXT-BIND-BUS`.
- Implementations MAY accept deprecated alias values for backward compatibility in declarations.
- Deprecated aliases MUST NOT be emitted as canonical negotiated values; canonical selection MUST use `BIND-BUS-0.1`.
