# AICP Operational Hardening Guide (DoS / Amplification / Abuse)

This guide provides implementer-first hardening guidance for mediated channels using RESUME, OBJECT_RESYNC, ALERTS, and ENFORCEMENT flows.

## Scope and non-scope

- **Scope:** protocol-aligned safe defaults and deterministic transcript checks that catch obvious abuse patterns.
- **Non-scope:** AICP is not a hosted anti-DoS platform. Rate limiting, traffic shaping, abuse scoring, and tenant isolation remain platform/operator responsibilities.
- **Goal:** reduce easy-to-abuse failure modes while keeping checks externally verifiable via in-repo fixtures and conformance artifacts.

## 1) RESUME abuse (probing / forced loops)

### Why it matters
Repeated resume attempts can be used to enumerate live sessions or force agents into expensive recovery loops.

### Recommended behavior
- Limit resume attempts per `session_id` and participant at the platform boundary.
- Return minimal `UNKNOWN_SESSION` responses; avoid giving session-state hints.
- Prefer structured ALERT/RESUME codes over verbose free text.
- Treat repeated `UNKNOWN_SESSION` probes across many distinct `session_id` values as abuse candidates.

Related checks:
- `RS-LOOP-01` in `conformance/extensions/RS_RESUME_0.1.json`
- `RS-PROBING-01` in `conformance/ops/OPS_HARDENING_0.1.json`

## 2) OBJECT_RESYNC amplification

### Why it matters
Resync flows can amplify payload size and mediator work if clients trigger large-state dumps repeatedly.

### Recommended behavior
- Cap resync response sizes and require platform pagination/chunking for large state.
- Require explicit authorization for resync requests in policy (`tool_access` / auditability controls).
- Prefer `ALERT` with `RESYNC_REQUIRED` over dumping full state when authorization or context is insufficient.

Related references:
- `docs/extensions/RFC_EXT_OBJECT_RESYNC_v0.1.md`
- `conformance/extensions/OR_OBJECT_RESYNC_0.1.json`

## 3) ALERT verbosity leakage

### Why it matters
Verbose alert payloads increase leakage risk and can be abused for log flooding.

### Recommended behavior
- Keep `message` short and operational.
- Prefer stable codes and action IDs (`registry/alert_codes.json`, `registry/alert_recommended_actions.json`).
- Never include raw secrets or full protected content in `details`.

Related check:
- `AL-VERBOSITY-01` in `conformance/ops/OPS_HARDENING_0.1.json`

## 4) ENFORCEMENT escalation safety

### Why it matters
Escalation signals can trigger disconnect-like behavior and can be abused via duplicate verdict emission.

### Recommended behavior
- Ensure KICK/BAN-style sanctions are paired with DISCONNECT guidance in implementation policy.
- Dedupe repeated verdict emissions for the same `target_message_hash` at platform layer.
- Prefer one authoritative verdict per target hash to reduce ambiguity.

Related checks:
- `ENF-GATE-01` in `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
- `ENF-VERDICT-STORM-01` in `conformance/ops/OPS_HARDENING_0.1.json`

## Deterministic transcript-level detection (conformance-friendly)

Conformance can reliably check these transcript-only patterns (no wall-clock heuristics):
- loop patterns (`RS-LOOP-01`)
- repeated identical resume probing without progress (`RS-PROBING-01`)
- overly large alert fields (`AL-VERBOSITY-01`)
- duplicate/ambiguous verdict references (`ENF-VERDICT-STORM-01`)

## Suggested defaults (guidance, not protocol MUST)

Conservative operational defaults:
- max consecutive `NEEDS_RESYNC` cycles: **2**
- max `ALERT.message` length: **256 chars**
- max `ALERT.details` canonical JSON size: **4 KB**
- max verdicts per `target_message_hash`: **1** (safe preference)  
  (Alternative policy: latest-wins, but only with explicit dedupe and audit log.)

## Evidence links

- Ops hardening suite: `conformance/ops/OPS_HARDENING_0.1.json` (badge is ops evidence, not a Core compatibility claim)
- Run: `make conformance-ops`
- Expected-fail fixtures: `fixtures/ops/`
- Existing extension suites:
  - `conformance/extensions/RS_RESUME_0.1.json`
  - `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
  - `conformance/extensions/AL_ALERTS_0.1.json`
  - `conformance/extensions/OR_OBJECT_RESYNC_0.1.json`
