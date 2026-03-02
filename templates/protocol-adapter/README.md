# Protocol Adapter Template (Python)

## < 15 min run
1. `python templates/protocol-adapter/adapter.py fixtures/core/minimal_core_happy.jsonl`
2. Inspect mapped events.

## < 1 hour onboarding path
1. Add schema + hash verification at ingress.
2. Add CAPNEG negotiation filters from config.
3. Persist event mapping to your internal event bus/store.
4. Add CI checks below.

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
