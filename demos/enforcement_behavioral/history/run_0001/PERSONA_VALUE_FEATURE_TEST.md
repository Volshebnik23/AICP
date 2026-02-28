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
- **EXT-ENFORCEMENT**: blocking gate + sanctions + authorized enforcer identities.
- **EXT-ALERTS**: alert codes + recommended actions.
- **EXT-RESUME**: resume handshake semantics (`UNKNOWN_SESSION`, `NEEDS_RESYNC`).
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

4. **Post-sanction resume attempt**
   - Kicked actor sends `RESUME_REQUEST`.
   - Mediator returns deterministic `RESUME_RESPONSE(status=UNKNOWN_SESSION)` with disconnect guidance.

5. **Inconclusive decision branch**
   - Verdict `INCONCLUSIVE` blocks delivery and emits `ALERT(POLICY_INCONCLUSIVE)` with `ESCALATE` guidance.

6. **Resume needs-resync branch**
   - `RESUME_REQUEST` behind current head returns `RESUME_RESPONSE(status=NEEDS_RESYNC)`.
   - Emits `ALERT(RESYNC_REQUIRED)` with `RETRY/REMEDIATE` actions.

7. **Threat-driven expected-fail: malicious mediator gate bypass**
   - `DENY` verdict followed by `CONTENT_DELIVER` must fail `ENF-GATE-01`.

8. **Threat-driven expected-fail: spoofed verdict sender**
   - Non-authorized sender emits verdict and mediator delivers; must fail `ENF-AUTH-01`.

9. **Threat-driven expected-fail: duplicate `message_id` replay**
   - Duplicate identifier must fail core invariants (`CT-INVARIANTS-01`).
