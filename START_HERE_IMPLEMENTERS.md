# Start Here for Implementers (AICP in < 1 hour)

AICP is a **protocol** for verifiable agent-to-agent content exchange (hashes, chains, schemas, conformance). It is **not** a hosted chat/enforcer platform. For the public packaging model of what to adopt first, see `docs/architecture/AICP_Adoption_Core_and_Tiers.md`. For the pilot-facing package of what is in scope for UAT, see `docs/release/AICP_UAT_Release_Pack.md`, `docs/release/AICP_UAT_Architecture_Freeze.md`, and `docs/release/AICP_UAT_Checklist.md`.

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
5. Optional PR/onboarding gate: `make prepr`.

## Fastest path (Python)

1. Copy [`dropins/aicp-core/python/`](dropins/aicp-core/python/) into your project.
2. Run the generator (from repo root): `make quickstart-py`.
3. Inspect output: `out/quickstart/py/minimal_core.jsonl`.
4. Validate output: `python sandbox/run.py out/quickstart/py/minimal_core.jsonl --no-signature-verify`.
5. Optional PR/onboarding gate: `make prepr`.

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


## Protocol Adapter / Gateway path

If you are integrating AICP with an existing platform gateway, start with:
- Guide: `docs/guides/Protocol_Adapter_Gateway.md`
- Template: `templates/protocol-adapter/`

Recommended CI baseline: `make prepr` (includes validation, full conformance via `make conformance-all`, reference tests, quickstarts, template smoke, and TypeScript SDK tests).

For compatibility or badge evidence, run `make compatibility-gate` so validation, `make conformance-all`, and snapshot generation stay aligned.


## Template smoke commands (shipped onboarding)

- `mkdir -p out/template-ts-agent`
- `node templates/ts-agent/agent.js > out/template-ts-agent/thread.jsonl`
- `python sandbox/run.py out/template-ts-agent/thread.jsonl --no-signature-verify`
- `python templates/protocol-adapter/adapter.py fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl`


## Choose your enforcement model

AICP supports multiple enforcement deployment models (host-owned, third-party, federated, distributed/quorum, ledger-anchored option).
Use this guide to choose based on trust, privacy, and operational constraints:
- `docs/architecture/Enforcement_Models.md`

## Pilot/UAT entrypoint

If you are evaluating AICP for a pilot or UAT-style rollout, use:
- `docs/release/AICP_UAT_Release_Pack.md`
- `docs/release/AICP_UAT_Architecture_Freeze.md`
- `docs/release/AICP_UAT_Checklist.md`

Then continue with the role-specific and quickstart paths below.

## Further reading

- `docs/INDEX.md`
- `docs/architecture/AICP_in_the_Ecosystem.md`
- `docs/profiles/Profile_Selection_Guide.md`
- `docs/playbooks/Session_Topologies.md`
- `docs/guides/MEDIATED_BLOCKING_PRODUCTION.md`
