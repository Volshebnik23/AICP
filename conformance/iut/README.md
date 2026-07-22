# AICP IUT Adapter Protocol 1.0

This directory defines a language-neutral, test-only adapter between the AICP TCK runner and an Implementation Under Test (IUT). It is not an AICP wire-protocol requirement and implementations do not need to expose it in production.

The runner starts the adapter as an external process without a shell. Requests and responses are one JSON object per line on stdin/stdout. Every response repeats `adapter_protocol_version`, `request_id`, and `operation`, and includes `success`; protocol diagnostics belong in the structured response or stderr, never as unframed stdout text.

Supported operations are:

- `describe`: returns `implementation_kind` (`external_implementation` or `reference_adapter`), `implementation_id`, `implementation_version`, `implementation_digest` or immutable build identifier, exact supported AICP profiles, supported crypto profiles, and adapter protocol version.
- `canonicalize_hash`: returns canonical JSON and the AICP object hash for `object_type` and `object`.
- `validate_transcript`: returns `accepted`, machine-readable `errors`, `degraded`, and `degraded_reasons` for the supplied target and public test-key material.
- `generate_case`: deterministically returns the artifact for a canonical case ID and parameters.
- `project_session_state`: returns the strict portable projection and `session_state_hash` for explicit transcript/as-of/head context.

`aicp_iut_runner.py` enforces a timeout, byte limits, exact JSONL response correlation, metadata stability across two `describe` calls, producer and consumer cases, checked-in suite/vector digests, and mark suppression for degraded or reference-adapter runs. Use `--cmd-json` for commands containing platform-specific paths; `--cmd` is parsed into an argument vector and is never passed to a shell.

The in-repo reference adapter is smoke-test infrastructure. Its reports use `execution_subject.kind=reference_corpus` and cannot substantiate a public claim for an external product.
