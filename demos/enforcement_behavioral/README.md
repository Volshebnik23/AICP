# Behavioral enforcement demo (mediated chat simulation)

This deterministic demo simulates two agents, a mediator (enforcement point), and an enforcer over AICP-style JSONL transcripts.

## What this demo proves
- Mediated blocking behavior (delivery only after ALLOW verdicts).
- Sanctioning behavior (`WARN`, `KICK`) via EXT-ENFORCEMENT semantics.
- Operational alerts via EXT-ALERTS (`POLICY_DENIED`, `SANCTION_APPLIED`, `POLICY_INCONCLUSIVE`, `RESYNC_REQUIRED`).
- Resume behavior via EXT-RESUME (`RESUME_REQUEST` / `RESUME_RESPONSE` with `UNKNOWN_SESSION` and `NEEDS_RESYNC`).
- Threat-driven expected-fail evidence (malicious mediator delivery, spoofed verdict sender, duplicate `message_id` replay).

## What this demo does NOT prove
- LLM truthfulness or model safety guarantees.
- Platform/network security hardening (e.g., DoS protection).
- Hosted product behavior (this is protocol-level scripted simulation only).

## Run the demo
```bash
python demos/enforcement_behavioral/scripts/run_demo.py
```

Outputs:
- Immutable run history under `demos/enforcement_behavioral/history/run_XXXX/`.
- Latest pointer at `demos/enforcement_behavioral/results/RESULTS.md`.

## Optional validation notes
- Baseline repository checks:
  - `make validate`
  - `make conformance-all`
- Demo generation convenience target:
  - `make demo-enforcement-behavioral`
- Demo conformance suite:
  - `python conformance/runner/aicp_conformance_runner.py --suite conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json --out conformance/report_demo_enforcement_behavioral.json`
