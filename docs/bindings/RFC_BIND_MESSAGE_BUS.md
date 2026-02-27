11. RFC: Transport bindings (Registered Extensions)

11.4 EXT-BIND-BUS — Message bus binding (normative)
Model: publish/subscribe over a message bus (Kafka/NATS/etc). Topic naming MUST be documented and stable. Consumers MUST handle duplicates and reordering.
Recommended topics (informative):
•	aicp.sessions.{session_id}.messages  (envelopes)
•	aicp.sessions.{session_id}.head      (state sync snapshots)
If the bus supports message keys/partitions, publishers SHOULD use message_id as the key to improve ordering per session partition (still not a semantic guarantee).
