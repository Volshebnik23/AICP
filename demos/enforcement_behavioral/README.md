# Behavioral enforcement demo (mediated chat simulation)

This deterministic demo simulates two agents, a mediator (enforcement point), and an enforcer over AICP-style JSONL transcripts.

## What this demo proves
- Mediated blocking behavior (delivery only after ALLOW verdicts).
- Sanctioning behavior (`WARN`, `KICK`) via EXT-ENFORCEMENT semantics.
- Operational alerts via EXT-ALERTS (`POLICY_DENIED`, `SANCTION_APPLIED`).
- Resume behavior via EXT-RESUME (`RESUME_REQUEST` / `RESUME_RESPONSE`).
- A clearly labeled expected-fail protocol misuse transcript.

## What this demo does NOT prove
- LLM truthfulness or model safety guarantees.
- Platform/network security hardening (e.g., DoS protection).
- Hosted product behavior (this is protocol-level scripted simulation only).

## Run the demo
```bash
python demos/enforcement_behavioral/scripts/run_demo.py
```

Outputs:
- Transcripts: `demos/enforcement_behavioral/transcripts/*.jsonl`
- Human-readable outcomes: `demos/enforcement_behavioral/results/RESULTS.md`

## Optional validation notes
- Baseline repository checks:
  - `make validate`
  - `make conformance-all`
- Demo generation convenience target (if present):
  - `make demo-enforcement-behavioral`
