16. RFC: EXT-ENFORCEMENT — Blocking enforcement contour (Registered Extension)
EXT-ENFORCEMENT defines a protocol-level contour for blocking enforcement in mediated channels. It standardizes interoperable message invariants (roles, gating semantics, sanction coding, and mandatory message patterns) without defining any chat platform, mediator product, or enforcement product implementation.

16.1 Purpose (normative)
This extension applies when an AICP exchange is mediated by a third-party route/application point and delivery can be gated by enforcement verdicts.
Implementations adopting EXT-ENFORCEMENT MUST preserve hash-chain and message-binding invariants so a third-party verifier can independently confirm whether gated delivery respected verdict outcomes.
This RFC standardizes only protocol behavior and conformance checks; it does NOT standardize UI, moderation tooling, or host platform internals.

16.2 Roles and terms (normative)
- Mediator / ChatHost: The routing/application point that decides whether candidate content is delivered/applied.
- Enforcer / Moderator: The actor issuing enforcement verdicts.
The Mediator and Enforcer MAY be the same entity or different entities.

16.3 Contract configuration (extension-defined)
The enforcement policy SHOULD be carried in `contract.ext.enforcement` (primary location).
A secondary compatibility location MAY be used at `contract.extensions["EXT-ENFORCEMENT"]`.

Normative minimum fields:
- `mode`: `"blocking"` | `"advisory"`.
- `enforcers`: array of identity strings.
- `mediators`: array of identity strings (optional).
- `gated_message_types`: array of message_type strings requiring a verdict (minimum set includes `"CONTENT_MESSAGE"`).

This sprint focuses conformance semantics for `mode="blocking"`.

16.4 Mandatory message pattern (blocking mode)
16.4.1 Canonical 3-message flow
In blocking mode, the canonical gating flow is:
1) `CONTENT_MESSAGE`: sender proposes content.
2) `ENFORCEMENT_VERDICT`: enforcer emits `ALLOW`, `DENY`, or `INCONCLUSIVE` with reason codes and sanctions.
3) `CONTENT_DELIVER`: mediator emits a delivery wrapper embedding the original content message only when delivery is permitted.

16.4.2 Blocking rule (normative)
In blocking mode, the Mediator MUST NOT emit `CONTENT_DELIVER` unless there exists a valid `ENFORCEMENT_VERDICT` with `decision="ALLOW"` bound to the exact `target_message_hash` of the original `CONTENT_MESSAGE`.
If an applicable verdict has `decision="DENY"`, the Mediator MUST NOT emit `CONTENT_DELIVER` for that content.

16.4.3 Verdict payload (normative minimum)
`ENFORCEMENT_VERDICT` payload MUST include:
- `verdict_id` (string)
- at least one target binding: `target_message_hash` or `target_message_id`
- `decision`: `ALLOW` | `DENY` | `INCONCLUSIVE`
- `reason_codes`: array of strings (may be empty)
- `sanctions`: array (may be empty)
- `issued_at`: string

16.4.4 Delivery payload (normative minimum)
`CONTENT_DELIVER` payload MUST include:
- `delivery_id` (string)
- `original_message` (embedded AICP envelope)
- `original_message_hash` (string)
- `verdict_message_id` (string)
- `delivered_at` (string)

16.5 Sanctions and code extensibility
Each item in `ENFORCEMENT_VERDICT.payload.sanctions` MUST be an object with:
- `code` (required string)
- `duration_seconds` (optional number)
- `scope` (optional string)
- `message` (optional string)

Well-known sanction codes are maintained in `registry/enforcement_sanction_codes.json`.
To preserve interoperability while allowing vendor-defined semantics, custom sanction codes MUST be accepted when namespaced as either:
- `x-<vendor>.<name>` (example: `x-acme.shadowban`)
- `<vendor>:<name>` (example: `acme:shadowban`)

16.6 Security considerations
Verdict spoofing is a primary risk: mediators MUST authenticate verdict sender identity before applying a verdict.
Implementations SHOULD sign enforcement verdict messages and SHOULD verify signatures prior to applying blocking decisions.
For this sprint, signatures are not mandatory in conformance fixtures.


## Registry entry {#registry-entry}
This RFC defines the stable registry entry for this extension; compatibility-impacting changes require explicit migration notes and conformance updates.
