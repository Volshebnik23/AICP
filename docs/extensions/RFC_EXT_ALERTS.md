# RFC: EXT-ALERTS — Operational alerts and recovery semantics (Registered Extension)

## 1. Purpose (normative)
EXT-ALERTS defines interoperable operational alerts for mediated and direct AICP channels.
It standardizes machine-readable alert codes, severity, and recommended recovery actions so implementations can provide consistent UX/ops behavior.

This extension is protocol-only. Platforms, mediators, and enforcers MAY enforce local policy on top of these signals.

## 2. Roles and emission rules (normative)
- Any sender MAY emit `ALERT` messages.
- A Mediator MAY emit system-level `ALERT` messages when channel/session state requires recovery.
- An Enforcer MAY emit policy-related `ALERT` messages.

## 3. Message type and payload binding (normative)
- Message type: `ALERT`.
- Payload schema: `schemas/extensions/ext-alerts-payloads.schema.json#/$defs/ALERT`.
- `ALERT` payload MUST include:
  - `alert_id`
  - `code` (registered in `registry/alert_codes.json`)
  - `severity` (`WARNING` or `FATAL`)
  - `recommended_actions` (array; each action MUST be registered in `registry/alert_recommended_actions.json`)
  - `issued_at`
- `ALERT` payload MAY include target bindings:
  - `target_message_hash`
  - `target_message_id`

Target fields bind the alert to a specific message/action when available. System-wide alerts MAY omit both target fields.

## 4. Severity and recovery actions (normative)
Severity levels are:
- `WARNING`: operation can continue, but remediation/retry is recommended.
- `FATAL`: operation cannot continue without explicit recovery or disconnect.

Recommended action taxonomy is registry-defined and MUST use action IDs from `registry/alert_recommended_actions.json`.
Baseline action IDs:
- `RETRY`
- `REMEDIATE`
- `DISCONNECT`
- `ESCALATE`
- `ACK_REQUIRED`
- `NO_ACTION`

## 5. Privacy and security notes (normative)
- `ALERT` payloads SHOULD prefer stable codes over verbose text.
- Human-readable `message` and `details` fields, when used, MUST avoid secrets and unnecessary sensitive content.
- Operational metadata should remain auditable while minimizing data disclosure.

## 6. Relationship to EXT-ENFORCEMENT (normative)
EXT-ALERTS is orthogonal to EXT-ENFORCEMENT:
- Enforcement sanctions are moderation actions.
- Alerts are protocol/operational signals.

They MAY be used together in the same flow. For example, an enforcer may apply a sanction and emit an alert describing required remediation/recovery.
