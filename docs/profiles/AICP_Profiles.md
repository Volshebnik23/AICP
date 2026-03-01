# AICP Profiles (Normative)

## 1. Definition
An AICP **profile** is a named interoperability bundle consisting of:
1. required extension set (which protocol capabilities MUST be present), and
2. required canonical conformance suites (which executable checks MUST pass).

An implementation claiming profile conformance MUST satisfy all required suites for that profile.

## 2. Profile Catalog and Status

### 2.1 Available now

#### `AICP-BASE`
- **Status:** Available now.
- **Required suites/extensions:** Core only.
  - `conformance/core/CT_CORE_0.1.json`
- **Intent:** Minimal interoperable baseline for AICP Core v0.1 behavior.
- **Canonical flow:** `docs/flows/AICP_Canonical_Flows.md#21-core-happy-path-signed-transcript`

#### `AICP-MEDIATED-BLOCKING`
- **Status:** Available now.
- **Required suites/extensions:**
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-CAPNEG: `conformance/extensions/CN_CAPNEG_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - EXT-ENFORCEMENT: `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
- **Intent:** Deterministic mediated blocking flow with policy evaluation + enforcement gate semantics.
- **Canonical flows:**
  - Enforcement: `docs/flows/AICP_Canonical_Flows.md#24-mediated-blocking-enforcement-ext-enforcement`
  - Operational alerts (optional in current baseline): `docs/flows/AICP_Canonical_Flows.md#25-operational-alerts-ext-alerts`

### 2.2 Planned (draft)

#### `AICP-MEDIATED-BLOCKING-OPS`
- **Status:** Planned (draft).
- **Dependencies:** Mediated blocking baseline plus standardized alerting/recovery operations artifacts.
  - EXT-ALERTS: `conformance/extensions/AL_ALERTS_0.1.json`

#### `AICP-RECEPTION-CHAT`
- **Status:** Planned (draft).
- **Dependencies:** Reception/chat flow catalog and associated conformance suite definitions.

#### `AICP-DELEGATED-IDENTITY`
- **Status:** Planned (draft).
- **Dependencies:** Delegated identity claims container extension and verification suite.

#### `AICP-WORKFLOW-ORCHESTRATION`
- **Status:** Planned (draft).
- **Dependencies:** Workflow orchestration semantics, message types, and conformance suites.

#### `AICP-RESUMABLE-SESSIONS`
- **Status:** Planned (draft).
- **Dependencies:** Session resumption semantics and deterministic continuation conformance tests.
  - EXT-RESUME: `conformance/extensions/RS_RESUME_0.1.json`
  - EXT-OBJECT-RESYNC (optional companion): `conformance/extensions/OR_OBJECT_RESYNC_0.1.json`

## 3. Conformance Badge Semantics
A **conformance badge** is a profile-level compatibility mark issued when all required suites for the profile pass.

Normative rules:
- Badge computation MUST be derived from machine-readable conformance reports.
- Badge issuance MUST NOT be self-asserted without report evidence.
- If any required suite fails, the profile badge MUST NOT be granted.

Profile runners MAY include child suite compatibility marks in profile reports for transparency, but profile-level pass/fail is determined by all required suites.

## 4. Profile Declaration & Negotiation (EXT-CAPNEG)

Platforms MAY require explicit AICP product profiles during capability negotiation.

- Declaration path: `CAPABILITIES_DECLARE.payload.required_aicp_profiles`
- Selection path: `CAPABILITIES_PROPOSE.payload.negotiation_result.selected.aicp_profile`
- Rejection path: `CAPABILITIES_REJECT` with registered `reason_code` (for example, `DOWNGRADE_NOT_ALLOWED`, `PROFILE_NOT_ACCEPTABLE`).

Operational guidance:
- A platform that requires `AICP-MEDIATED-BLOCKING@0.1` SHOULD declare it in `required_aicp_profiles` and reject proposals selecting weaker profiles.
- Product profile claims negotiated in CAPNEG are runtime claims; conformance/profile badges are separate evidence artifacts and MUST still be produced from suite/profile runners.
- Downgrade attempts are expected to be detectable deterministically via CAPNEG conformance checks.
