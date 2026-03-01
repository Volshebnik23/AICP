# Implementer Guide: Agent Developers

This guide is for agent application teams integrating AICP quickly. For canonical term definitions, see [docs/GLOSSARY.md](../GLOSSARY.md).

## Quick path

- Start from drop-ins (copy folder): [dropins/aicp-core/](../../dropins/aicp-core/)
- Or use TypeScript SDK utilities: [sdk/typescript/](../../sdk/typescript/)
- Run quickstarts:
  - `make quickstart-py`
  - `make quickstart-ts`
- Validate results:
  - `make validate`
  - `make conformance-all`

## Minimal hello session

Baseline sequence:

1. `CONTRACT_PROPOSE`
2. `CONTRACT_ACCEPT`
3. `CONTEXT_AMEND`

This gives a minimal, auditable session lifecycle you can extend safely.

## Mediated blocking channels: practical behavior

- Send `CONTENT_MESSAGE`.
- Expect enforcer outcomes (`ENFORCEMENT_VERDICT`) and possibly `ALERT`.
- If `DENY` or `INCONCLUSIVE`:
  - do not assume delivery,
  - follow recommended remediation,
  - retry only when guidance/policy permits.

## Claiming compatibility

- Run `make conformance-all`.
- Interpret profile and suite marks from generated reports.
- Treat degraded mode as non-badge-eligible until missing checks are available.

## Pointers

- Start Here: [START_HERE_IMPLEMENTERS.md](../../START_HERE_IMPLEMENTERS.md)
- Profiles: [docs/profiles/AICP_Profiles.md](../profiles/AICP_Profiles.md)
- Enforcement demo transcripts/suite: [conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json](../../conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json)
- Sandbox validator: [sandbox/run.py](../../sandbox/run.py)
