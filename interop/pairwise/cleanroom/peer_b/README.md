# Clean-room peer B

This directory contains the standalone Node.js side of the M66 pairwise test.
It has its own canonical JSON, typed hashing, Core transcript handling, MCP
JSON-RPC mailbox, historical pairwise control, Pairwise 1.2 client-driver, and atomic
server role-descriptor implementation. The client authors its own MCP requests and
constructs replies from messages actually consumed through polling. It imports no AICP
implementation or fixture-answer code from the repository.
