# RFC: Channel Properties (M22 Slice)

Channel properties define transport-level behavior negotiated via EXT-CAPNEG so message-layer behavior remains deterministic across bindings.

## Normative properties
- `CP-RELIABILITY-0.1`: `at_least_once` or `at_most_once`.
- `CP-ORDERING-0.1`: `ordered` or `unordered`.
- `CP-ACK-0.1`: `none` or `explicit`.
- `CP-REPLAY-WINDOW-0.1`: integer seconds (`>= 0`) indicating accepted replay tolerance.

## Vendor extensions
Implementations MAY include vendor extensions as `vendor:/...` keys. Unknown vendor keys MUST NOT be interpreted as standard CP-* semantics.

## CAPNEG selection validation (normative)
- `CAPABILITIES_DECLARE.payload.supported_channel_properties` advertises each party's support.
- `CAPABILITIES_PROPOSE.payload.negotiation_result.selected.channel_properties` MUST choose values supported by every participant in the negotiation.
- `selected.binding` MUST be a canonical registered transport binding ID.

## Registry entry {#registry-entry}
- Registry file: `registry/channel_properties.json`
- Type: `channel_properties`
- Initial IDs: `CP-RELIABILITY-0.1`, `CP-ORDERING-0.1`, `CP-ACK-0.1`, `CP-REPLAY-WINDOW-0.1`
