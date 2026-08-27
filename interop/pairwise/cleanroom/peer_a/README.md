# Clean-room peer A

Repository-owned Python test implementation for M66 harness verification. It
implements its own canonicalization, hashing, Core validation, producer,
MCP server/client, historical pairwise-control, versioned Pairwise 1.3 client-driver, and atomic
server role-descriptor logic. The Pairwise client authors MCP requests and retains peer
artifacts only after consuming server poll responses. The 1.3 driver preserves run-global
visibility and exact continuation cursors. It is not an external adoption
artifact and does not claim organizational independence.
