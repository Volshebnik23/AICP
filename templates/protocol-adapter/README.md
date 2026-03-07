# Protocol Adapter Template (Python)

This template is a **demo projection** for onboarding. It is not a full gateway runtime by itself.
Use it to bootstrap mapping logic while preserving audit-critical envelope fields.

## < 15 min run
1. `python templates/protocol-adapter/adapter.py fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl`
2. Inspect mapped events and the embedded `audit_envelope`.

## Mapping posture (safe default)
The adapter keeps these fields in the event projection for auditability/verifiability:
- `message_hash`, `prev_msg_hash`
- `signatures`
- `contract_ref`
- compact relation/extension metadata (`audit_envelope.relation_meta`)

The mapping is still intentionally partial for product onboarding. Keep the original AICP envelope in immutable storage for authoritative replay.

## < 1 hour onboarding path
1. Add schema + hash verification at ingress.
2. Add signature verification + key resolution before business-side dispatch.
3. Add CAPNEG negotiation filters from config.
4. Persist both full envelope and projected event to your internal event bus/store.
5. Add CI checks below.

## GitHub Actions snippet
```yaml
name: aicp-gateway-checks
on: [push, pull_request]
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: make validate
      - run: make conformance-profiles
```
