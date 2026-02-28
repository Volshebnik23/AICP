# Persona → Value → Feature → Test mapping (Behavioral enforcement demo)

## A) Personas
- **P0 Platform/Mediator Developer**
- **P1 Agent Developer (brand/personal agent)**
- **P2 Enterprise AI Orchestrator (compliance/IAM-friendly)**
- **P3 Auth/Identity Provider**
- **P4 Vibe-coder / Multi-agent Builder**

## B) Values
- Brand safety
- Compliance / privacy (PII handling)
- Security hygiene (anti prompt-injection / tool misuse posture)
- Interop & auditability (verifiable transcripts, consistent semantics)
- Operational recovery (alerts + recommended actions)
- Low onboarding friction (profiles/badges/deterministic examples)

## C) Features exercised
- **EXT-ENFORCEMENT**: blocking gate + sanctions.
- **EXT-ALERTS**: alert codes + recommended actions.
- **EXT-RESUME**: resume handshake semantics.
- **EXT-OBJECT-RESYNC**: noted as follow-up path; not required in this demo.

## D) Behavioral test cases and expected outcomes
1. **Happy path**
   - Content is allowed and delivered (`CONTENT_MESSAGE` → `ENFORCEMENT_VERDICT(ALLOW)` → `CONTENT_DELIVER`).

2. **Policy violation matrix**
   - Safe placeholder markers trigger `DENY + WARN` and no delivery.
   - Emits `ALERT` with `code=POLICY_DENIED`, `severity=WARNING`, `recommended_actions=[REMEDIATE, ACK_REQUIRED]`.

3. **Repeat violation escalation**
   - First violation by same actor: `DENY + WARN + ALERT(POLICY_DENIED)`.
   - Second violation by same actor in same session: `DENY + KICK + ALERT(SANCTION_APPLIED, FATAL, [DISCONNECT])`.
   - Actor is blocked from further participation in that scenario.

4. **Post-sanction resume attempt**
   - Kicked actor sends `RESUME_REQUEST`.
   - Mediator returns deterministic `RESUME_RESPONSE(status=UNKNOWN_SESSION)` with disconnect guidance.

5. **Protocol misuse expected-fail**
   - Demonstrates duplicate `message_id` replay in transcript.
   - Marked as expected-fail evidence (not counted as pass demonstration).
