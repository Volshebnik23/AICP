# Start Here for Implementers (AICP in < 1 hour)

AICP is a **protocol** for verifiable agent-to-agent content exchange (hashes, chains, schemas, conformance). It is **not** a hosted chat/enforcer platform.

## Choose your role

| Role | What you build | Smoke-check finish line |
|---|---|---|
| Agent developer | Send schema-valid AICP messages | Generate a minimal Core transcript and validate it locally |
| Mediator/Host developer | Gate and deliver messages in mediated channels | Validate transcripts with chain + message-type registry checks |
| Enforcer/Moderator developer | Emit verdicts/alerts tied to policy evidence | Run extension/demo conformance suites and verify expected pass/fail |

## Fastest path (TypeScript)

1. Copy [`dropins/aicp-core/typescript/`](dropins/aicp-core/typescript/) into your project.
2. Run the generator (from repo root): `make quickstart-ts`.
3. Inspect output: `out/quickstart/ts/minimal_core.jsonl`.
4. Validate output: `python sandbox/run.py out/quickstart/ts/minimal_core.jsonl --no-signature-verify`.
5. Optional full checks: `make validate && make conformance`.

## Fastest path (Python)

1. Copy [`dropins/aicp-core/python/`](dropins/aicp-core/python/) into your project.
2. Run the generator (from repo root): `make quickstart-py`.
3. Inspect output: `out/quickstart/py/minimal_core.jsonl`.
4. Validate output: `python sandbox/run.py out/quickstart/py/minimal_core.jsonl --no-signature-verify`.
5. Optional full checks: `make validate && make conformance`.

## Role-specific first steps

### Agent developer
1. Start from `dropins/aicp-core/python/` or `dropins/aicp-core/typescript/`.
2. Keep required envelope fields: `session_id`, `message_id`, `timestamp`, `sender`, `message_type`, `contract_id`, `payload`.
3. `contract_id` is required on all messages.
4. Compute `message_hash` from message body.
5. Chain `prev_msg_hash` from the previous message.
6. Validate with [sandbox/run.py](sandbox/run.py).

### Mediator/Host developer
1. Reuse the drop-in message builder to ensure deterministic hashes.
2. Keep transcript ordering deterministic and immutable.
3. Validate message_type registration and chain integrity with `make conformance`.
4. Add extension suites (`make conformance-ext`) for enforcement/alerts/resume flows.

### Enforcer/Moderator developer
1. Keep decisions as protocol artifacts (`ENFORCEMENT_VERDICT`, `ALERT`) instead of ad hoc logs.
2. Validate against extension suites in [conformance/extensions/](conformance/extensions/).
3. Use demo suite for behavioral verification: `conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json`.
4. Treat degraded reports as non-badge-eligible.

## What if validation fails?

- Error and recovery playbook: [docs/ops/ERROR_AND_RECOVERY.md](docs/ops/ERROR_AND_RECOVERY.md)
- Security hardening guidance: [security_review/OPS_HARDENING_GUIDE.md](security_review/OPS_HARDENING_GUIDE.md)
