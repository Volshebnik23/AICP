# AICP Core Python Drop-in

Copy this folder into any Python project to generate deterministic Core JSONL messages.

1. Run: `python generate_minimal_core_transcript.py --out ./out/minimal_core.jsonl`
2. Output: `out/minimal_core.jsonl` (3-message Core happy path)
3. Core helper functions are in `aicp_core.py`.

Assets shipped for copy-folder validation:
- `assets/schemas/core/*.schema.json`
- `assets/registry/message_types.json`

This drop-in is protocol-only and works alongside non-AICP chats (AICP is optional).
To validate output, run the AICP sandbox validator or conformance runner, e.g.:
- `python sandbox/run.py out/minimal_core.jsonl --no-signature-verify`
- `python conformance/runner/aicp_conformance_runner.py --suite conformance/core/CT_CORE_0.1.json --out conformance/report.json`
