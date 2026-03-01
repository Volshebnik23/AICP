# Error and Recovery Playbook (Deterministic)

This document centralizes operational recovery behavior for common AICP failure categories.

For canonical term definitions, see [docs/GLOSSARY.md](../GLOSSARY.md).

## Action taxonomy alignment (EXT-ALERTS)

Use registered `recommended_actions` values from EXT-ALERTS for consistent behavior:

- `RETRY`
- `REMEDIATE`
- `DISCONNECT`
- `ESCALATE`
- `ACK_REQUIRED`
- `NO_ACTION`

## Failure categories and recommended actions

| Category | Typical detection signal | Retryable? | Recommended actions |
|---|---|---|---|
| Schema invalid | `CT-SCHEMA-JSONL-01`, payload schema failures | Usually no (until fixed) | `REMEDIATE`, `DENY` delivery/effect, `ESCALATE` if persistent |
| Hash-chain mismatch | `CT-HASH-CHAIN-01`, prev-hash inconsistency | No | `DISCONNECT`, `ESCALATE`, require transcript repair/resync |
| `message_hash` mismatch | `CT-MESSAGE-HASH-01` | No | `DENY` delivery/effect, `ESCALATE`, quarantine offending sender |
| Signature verify failure | `CT-SIGNATURE-VERIFY-01` | No | `DENY` delivery/effect, `ESCALATE`, optional `DISCONNECT` |
| Unknown `message_type` | registry check failures | No (unless upgraded intentionally) | `REMEDIATE`, `DENY`, controlled capability negotiation |
| CAPNEG downgrade/inconsistency | `CN-DOWNGRADE-01` | No | `ESCALATE`, `REMEDIATE`, reject negotiated result |
| Resume loop/probing detected | `RS-LOOP-01`, `RS-PROBING-01` | Conditionally | `REMEDIATE`; then `DISCONNECT`/`ESCALATE` if repeated |

## Fatal vs retryable guidance

- **Fatal** (security/integrity failure): hash mismatch, signature failure, chain corruption, malicious downgrade.
  - Preferred default: deny effect/delivery and escalate.
- **Retryable** (transient/operational): mediator unavailable, timeout, recoverable resume state.
  - Preferred default: bounded retry, then remediation.

## Canonical references

- EXT-ALERTS RFC: [docs/extensions/RFC_EXT_ALERTS.md](../extensions/RFC_EXT_ALERTS.md)
- Security ops hardening guide: [security_review/OPS_HARDENING_GUIDE.md](../../security_review/OPS_HARDENING_GUIDE.md)
- Canonical flows (alerts/resume): [docs/flows/AICP_Canonical_Flows.md](../flows/AICP_Canonical_Flows.md)
- Signed-path security evidence suite (M9.7): [conformance/security/SIG_SIGNED_PATHS_0.1.json](../../conformance/security/SIG_SIGNED_PATHS_0.1.json)
