# OPS Hardening Guide (Protocol-Level)

## Scope and non-scope
AICP is a protocol and does not provide hosted DDoS mitigation or runtime admission control. DoS/abuse protection is primarily a platform/host responsibility. AICP can still define safe defaults and deterministic transcript checks that expose obvious abuse patterns.

## 1) RESUME abuse (probing / forced loops)
**Why it matters:** repeated resume probes can enumerate sessions and consume mediator resources.

**Recommended behavior:**
- Limit resume attempts per `session_id` and participant at platform layer.
- For `UNKNOWN_SESSION`, return minimal details to reduce enumeration leakage.
- Prefer `ALERT` code/action guidance over verbose free-text explanations.

## 2) OBJECT_RESYNC amplification
**Why it matters:** large state/object responses can amplify traffic and memory pressure.

**Recommended behavior:**
- Cap response sizes and use pagination/chunking at platform layer.
- Require authorization for resync requests in policy (for example `tool_access`/`auditability`).
- Prefer `ALERT` code `RESYNC_REQUIRED` guidance rather than bulk state dumps.

## 3) ALERT verbosity leakage
**Why it matters:** verbose operational text can leak secrets or sensitive context.

**Recommended behavior:**
- Keep `message` concise; prefer code + action IDs.
- Avoid raw secrets/full content in `details`.
- Use deterministic lint checks for maximum field sizes.

## 4) ENFORCEMENT escalation safety
**Why it matters:** inconsistent sanction messaging and repeated verdict emission can cause ambiguity and amplification.

**Recommended behavior:**
- Ensure `KICK`/`BAN` paths include `DISCONNECT` guidance.
- Deduplicate verdict emission per `target_message_hash` to avoid verdict storms.

## Deterministic transcript-level detection (conformance-suitable)
Conformance can check deterministic evidence only:
- loop patterns and repeated no-progress requests,
- repeated probing-style requests,
- overly large fields (lint-like size caps),
- duplicate/ambiguous references (for example multiple verdicts for one target hash).

## Suggested defaults (guidance, not MUST)
- max consecutive `NEEDS_RESYNC` cycles: **2**
- max `ALERT.message` length: **256** chars
- max `ALERT.details` canonical JSON size: **4 KB**
- max verdicts per `target_message_hash`: **1**

## Related RFCs and checks
- `docs/extensions/RFC_EXT_RESUME.md`
- `docs/extensions/RFC_EXT_ALERTS.md`
- `docs/extensions/RFC_EXT_ENFORCEMENT.md`
- `docs/extensions/RFC_EXT_OBJECT_RESYNC.md`
- `conformance/extensions/RS_RESUME_0.1.json`
- `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
- `conformance/ops/OPS_HARDENING_0.1.json`
