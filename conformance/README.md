# Conformance — AICP (Agent Interaction Content Protocol)

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

Conformance artifacts for AICP live here.

- `core/CT_CORE_0.1.json` — Core v0.1 suite catalog.
- `extensions/*.json` — extension suite catalogs.
- `bindings/*.json` — binding suite catalogs.
- `runner/aicp_conformance_runner.py` — conformance CLI.
- `conformance_report_schema.json` — machine-readable report schema.
- `conformance_spec.md` — pass criteria and usage.

Run:

```bash
make conformance
make conformance-ext
make conformance-bindings
```

`make conformance` generates `conformance/report.json` locally (ignored/untracked by git).

`make test` runs Python reference tests from `reference/python/tests`.
