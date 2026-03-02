## AICP — Agent Interaction Content Protocol

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

## Roadmap and current status (repo-backed)

This roadmap reflects the **actual repository artifacts**, not only content embedded in the Suite index.
It separates: (A) Spec authoring (text), and (B) Productization (executable, enforceable deliverables).

### Legend
- ✅ **Shipped**: exists in-repo as a standalone artifact and is runnable/usable.
- 🟡 **Current**: active milestone in progress.
- 🔜 **Next**: next milestone to execute.
- ⏳ **Later**: planned.

---

## ✅ Shipped foundations
- ✅ Core schemas/registries/fixtures + conformance runner
- ✅ Reference implementations + drop-ins
- ✅ Anti-drift gates (coverage + dropins assets) + snapshot discipline
- ✅ Plugfest kit + interop matrix + errata workflow note
- ✅ Profiles catalog + profile conformance runner

---

## ✅ Shipped ecosystem-facing protocol profiles (platform-optional; protocol-only work)
- ✅ M11 Reception Chat Profile shipped (`AICP-RECEPTION-CHAT@0.1`, plus `RC-RECEPTION-CHAT-SEMANTICS-0.1` suite).
- ✅ M12 Delegated Identity & Acting-on-behalf-of Binding shipped (`EXT-DELEGATED-IDENTITY`, `DI-DELEGATED-IDENTITY-0.1`, `AICP-DELEGATED-IDENTITY@0.1`).
- ✅ M13 Workflow Orchestration & Delegation Profile shipped (`AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1`).

---

## ✅ Shipped productization milestone
- ✅ M14 Profile packaging shipped (added and wired multiple conformance profiles into `make conformance-profiles`).

---

## ⏳ Website & messaging (docs-only)
- ⏳ M15 Convert ecosystem user stories into website-ready marketing use cases
  - Source: `docs/marketing/ecosystem_use_cases.md`

---

## 🟡 M16 Numeric canonicalization & safe number policy (current; closes OQ-0001)
**Why:** numbers/float appear in real payloads; cross-language numeric behavior is a major interop risk.

- ✅ Part 1 shipped: float rejection parity across reference + dropins + numeric guardrail suite
  - `conformance/core/CT_NUMERIC_GUARDRAILS_0.1.json`
  - `fixtures/core/numeric/NUM-01_float_in_payload_expected_fail.jsonl`
- 🔜 Part 2 next: RFC8785 numeric canonicalization + safe-integer policy + cross-language numeric fixtures

---

## ⏳ M17 Anti-drift alignment + stability graduation program
### M17.1 ID & compatibility-mark alignment (anti-drift)
- Align extension IDs ↔ suite IDs ↔ compatibility marks ↔ profile required_extensions.
- Fix known drift:
  - EXT-SECURITY-ALERT (registry) vs SECURITY-ALERTS (suite/marks naming).
  - RC reception semantics suite uses `AICP-EXT-*` mark but is not a registered extension.
- Add anti-drift validator:
  - if a suite mark starts with `AICP-EXT-...`, the corresponding `EXT-...` MUST exist in `registry/extension_ids.json`.

### M17.2 experimental → stable graduation policy
- Define and enforce criteria to promote entries from experimental → stable.
- Promote a minimal baseline set after interop evidence.

---

## ⏳ M18 Release discipline + adoption packaging (changelog, compatibility, legal)
- Fill `RELEASE_NOTES.md` with repo-backed changes + compatibility notes.
- Add:
  - `docs/ops/COMPATIBILITY_POLICY.md`
  - `docs/ops/RELEASE_CHECKLIST.md`
  - `VERSIONING.md`, `DEPRECATION.md`
- Legal packaging for adoption:
  - `LICENSE`, spec license statement, `TRADEMARK.md`
- Error & Recovery canonicalization:
  - fix `docs/ops/ERROR_AND_RECOVERY.md` (“DENY” is not an action id)
  - declare canonical relationship between RFC and ops guide (RFC canonical).

---

## ⏳ M19 Protocol Adapter / Gateway quickstart kit (CI-first onboarding)
- Standardize adapter-first integration path (validate+hash+sig, CAPNEG filter, map to internal events).
- Provide a minimal deployable skeleton + CI templates.

---

## ⏳ M20 Trust anchors and issuer attestations (internet-scale trust)
## ⏳ M21 Revocation/status channel (OCSP/CRL analog)
## ⏳ M22 Transport bindings & channel properties (HTTP/WS + anti-replay + quotas)
## ⏳ M23 Confidentiality & selective disclosure modes
## ⏳ M24 Redaction standard + retention/deletion policies
## ⏳ M25 Policy semantic interoperability profiles (OPA/Rego, ABAC/RBAC, LLM-safety)
## ⏳ M26 Human-in-the-loop primitive (approval / step-up)
## ⏳ M27 Production attributes: tracing, SLA signals, metering
## ⏳ M28 IAM bridge (OAuth/OIDC mapping)
## ⏳ M29 Enterprise domain bindings (OpenAPI/OData/OPA/ABAC)

---

## Immediate next step
1) **M16 Part 2**: RFC8785 numeric canonicalization + safe-integer policy + cross-language fixtures.
2) Then **M17.1**: ID/marks anti-drift alignment (SECURITY-ALERT(S), reception semantics suite mark classification).
