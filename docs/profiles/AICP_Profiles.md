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

#### `AICP-MEDIATED-BLOCKING`
- **Status:** Available now.
- **Required suites/extensions:**
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-CAPNEG: `conformance/extensions/CN_CAPNEG_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - EXT-ENFORCEMENT: `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
- **Intent:** Deterministic mediated blocking flow with policy evaluation + enforcement gate semantics.

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

## 3. Conformance Badge Semantics
A **conformance badge** is a profile-level compatibility mark issued when all required suites for the profile pass.

Normative rules:
- Badge computation MUST be derived from machine-readable conformance reports.
- Badge issuance MUST NOT be self-asserted without report evidence.
- If any required suite fails, the profile badge MUST NOT be granted.

Profile runners MAY include child suite compatibility marks in profile reports for transparency, but profile-level pass/fail is determined by all required suites.
