# AICP Profiles (Normative)

## 1. Definition
An AICP **profile** is a named interoperability bundle consisting of:
1. required extension set (which protocol capabilities MUST be present), and
2. required canonical conformance suites (which executable checks MUST pass).

An implementation claiming profile conformance MUST satisfy all required suites for that profile. For adoption packaging guidance (core vs optional tiers), see [docs/architecture/AICP_Adoption_Core_and_Tiers.md](../architecture/AICP_Adoption_Core_and_Tiers.md); this document remains the canonical executable profile catalog.

## 2. Profile Catalog and Status

The generated table below is the canonical human-readable profile-status view. Repository
availability, registry maturity, internal evidence, external-IUT reachability, and independent
evidence are separate facts. The table and the structured status block in each profile section
are checked against `registry/aicp_profiles.json` and
`docs/process/repo_truth_status.json`.

<!-- BEGIN GENERATED PROFILE STATUS -->
| Profile | Repository availability | Registry maturity | Internal evidence | External-IUT target | Ordinary external mark | Independent external evidence |
|---|---|---|---|---|---|---|
| `AICP-AGENT-MEDIA@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-AUTHENTICATED-BASE@0.1` | Shipped | Experimental | Available | Yes | Reachable for an eligible external implementation | Absent |
| `AICP-BASE@0.1` | Shipped | Stable | Available | Yes | Reachable for an eligible external implementation | Absent |
| `AICP-BASE@0.2` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-BAZAAR-RECEPTION@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-COMMERCE-ACP@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-DELEGATED-IDENTITY@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-EXECUTION-INTEROP@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-MEDIATED-BLOCKING-OPS@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-MEDIATED-BLOCKING@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-POLICY-ABAC-RBAC@0.1` | Shipped | Stable | Available | No | No external-IUT target | Absent |
| `AICP-POLICY-LLM-SAFETY@0.1` | Shipped | Stable | Available | No | No external-IUT target | Absent |
| `AICP-POLICY-OPA-REGO@0.1` | Shipped | Stable | Available | No | No external-IUT target | Absent |
| `AICP-RECEPTION-CHAT@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-RESUMABLE-SESSIONS@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
| `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1` | Shipped | Experimental | Available | No | No external-IUT target | Absent |
<!-- END GENERATED PROFILE STATUS -->

### 2.1 Primary catalog entries

#### `AICP-BASE`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-BASE@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Stable.
- **Internal evidence:** Available.
- **External-IUT target:** Available.
- **Ordinary external mark:** Reachable for an eligible external implementation.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-BASE@0.1 -->
- **Required suites/extensions:** Core only.
- **Registry alignment note:** `registry/aicp_profiles.json` sets `required_extensions=[]` for this profile.
  - `conformance/core/CT_CORE_0.1.json`
- **Intent:** Minimal interoperable profile for AICP Core v0.1 behavior.
- **Canonical flow:** `docs/flows/AICP_Canonical_Flows.md#21-core-happy-path-signed-transcript`

#### `AICP-BASE@0.2`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-BASE@0.2 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-BASE@0.2 -->
- **Required suite:** `conformance/core/CT_CORE_0.2.json`.
- **Compatibility marks:** `AICP-Core-0.2` and `AICP-Profile-BASE-0.2`.
- **Intent:** Experimental post-UAT exact agreement on one contract artifact and active
  contract head.
- **Version boundary:** This profile is selected explicitly and does not reinterpret
  `AICP-BASE@0.1`.
- **Evidence boundary:** Internal conformance only in M60; no external-IUT target and no
  independent external evidence.
- **Signature/badge boundary:** Unsigned messages remain valid; every present signature
  must verify. Degraded or skipped suite/profile execution emits no compatibility mark.
- **State boundary:** Mandatory validation rejects a message before it can change proposal
  indexes, active head, agreement tuples, or conflict selection.
- **Security boundary:** Exact agreement does not authenticate senders or establish
  proposal/acceptance authority, quorum legitimacy, policy correctness, hidden-transcript
  non-equivocation, transport security, or legal enforceability.

### AICP-AUTHENTICATED-BASE

- **Identifier:** `AICP-AUTHENTICATED-BASE@0.1`.
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-AUTHENTICATED-BASE@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Available.
- **Ordinary external mark:** Reachable for an eligible external implementation.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-AUTHENTICATED-BASE@0.1 -->
- **Adoption note:** Post-UAT; it is not part of the frozen pilot center.
- **Required extensions:** none.
- **Required crypto profile:** `aicp.crypto.ed25519.v1`.
- **Required suites:** `CT_CORE_0.1.json` and
  `AUTH_AUTHENTICATED_MESSAGES_0.1.json`.
- **Compatibility mark:** `AICP-Profile-AUTHENTICATED-BASE-0.1`, emitted only after a
  complete non-degraded profile pass with no skipped required crypto check.

Every transcript message claiming this profile MUST have a recomputable `message_hash` and
a non-empty `signatures` array. Every signature entry MUST use `object_type="message"`,
MUST bind `signature.object_hash` to the envelope `message_hash`, MUST resolve `signer` and
`kid` unambiguously to supplied Ed25519 verification material, and MUST verify. At least
one valid signature MUST have `signer` exactly equal to the envelope `sender`. Extra
co-signatures are allowed, but one invalid entry invalidates the claim.

Missing key material is failure, not compatibility evidence. If the crypto backend is
unavailable, structural checks may pass in degraded mode, but the compatibility mark MUST
be suppressed outside the TCK's explicit case-local unavailable-backend probe. That probe
tests truthful unavailable behavior and does not weaken normal authenticated verification.
Key discovery, custody, rotation, revocation, transport security, and
identity issuance are outside this profile. When CAPNEG is used, its selected AICP profile
and crypto profile must satisfy these exact requirements; CAPNEG is not itself a static
dependency of this profile.

This profile proves only a cryptographic binding between the declared envelope sender and
that message hash. It does not establish real-world identity, account ownership,
acting-on-behalf-of authority, delegation scope, issuer trust, revocation freshness,
non-equivocation, witnessing, policy/moderation correctness, or universal trust.

| Surface | What it establishes | What it does not replace |
|---|---|---|
| `AICP-BASE@0.1` | Core structure, hashing, and transcript integrity; signatures remain optional | Sender authentication |
| `AICP-AUTHENTICATED-BASE@0.1` | Ed25519 sender-to-message authentication | Real-world or delegated identity |
| `AICP-DELEGATED-IDENTITY@0.1` | Acting-on-behalf-of issuer, scope, and expiry semantics | Message authentication; it may be composed with authenticated base |
| `EXT-IDENTITY-LC` and trust/status extensions | Identity/key lifecycle, trust anchors, revocation or status | Authenticated-base message binding |
| `EXT-TRANSCRIPT-WITNESS` | External checkpoint/witness evidence and anti-equivocation signals | Sender authentication |
| `AICP-MEDIATED-BLOCKING@0.1` | Policy-evaluation and delivery-gating semantics | Sender authentication |

#### `AICP-MEDIATED-BLOCKING`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-MEDIATED-BLOCKING@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-MEDIATED-BLOCKING@0.1 -->
- **Required suites/extensions:**
- **Registry alignment note:** `registry/aicp_profiles.json` requires `EXT-CAPNEG`, `EXT-POLICY-EVAL`, and `EXT-ENFORCEMENT` only.
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-CAPNEG: `conformance/extensions/CN_CAPNEG_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - EXT-ENFORCEMENT: `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
- **Intent:** Deterministic mediated blocking flow with policy evaluation + enforcement gate semantics.
- **Canonical flows:**
  - Enforcement: `docs/flows/AICP_Canonical_Flows.md#24-mediated-blocking-enforcement-ext-enforcement`
  - Operational alerts (optional in current profile): `docs/flows/AICP_Canonical_Flows.md#25-operational-alerts-ext-alerts`

#### `AICP-MEDIATED-BLOCKING-OPS`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-MEDIATED-BLOCKING-OPS@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-MEDIATED-BLOCKING-OPS@0.1 -->
- **Required suites/extensions:**
- **Registry alignment note:** `registry/aicp_profiles.json` requires `EXT-CAPNEG`, `EXT-POLICY-EVAL`, `EXT-ENFORCEMENT`, `EXT-ALERTS`, and `EXT-RESUME`.
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-CAPNEG: `conformance/extensions/CN_CAPNEG_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - EXT-ENFORCEMENT: `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
  - EXT-ALERTS: `conformance/extensions/AL_ALERTS_0.1.json`
  - EXT-RESUME: `conformance/extensions/RS_RESUME_0.1.json`
- **Intent:** Operations-hardened mediated blocking profile for deterministic enforcement with alerts and resume continuity.
- **Canonical flows:**
  - Alerts: `docs/flows/AICP_Canonical_Flows.md#25-operational-alerts-ext-alerts`
  - Resume: `docs/flows/AICP_Canonical_Flows.md#26-session-resume-ext-resume`

#### `AICP-RESUMABLE-SESSIONS`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-RESUMABLE-SESSIONS@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-RESUMABLE-SESSIONS@0.1 -->
- **Required suites/extensions:**
- **Registry alignment note:** `registry/aicp_profiles.json` requires `EXT-RESUME` and `EXT-OBJECT-RESYNC`.
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-RESUME: `conformance/extensions/RS_RESUME_0.1.json`
  - EXT-OBJECT-RESYNC: `conformance/extensions/OR_OBJECT_RESYNC_0.1.json`
- **Intent:** Continuity-focused profile for session resume and deterministic object rehydration across reconnects.
- **Canonical flows:**
  - Resume: `docs/flows/AICP_Canonical_Flows.md#26-session-resume-ext-resume`
  - Object resync: `docs/flows/AICP_Canonical_Flows.md#23-object-resync-ext-object_resync`

#### `AICP-RECEPTION-CHAT`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-RECEPTION-CHAT@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-RECEPTION-CHAT@0.1 -->
- **Required suites/extensions:**
- **Registry alignment note:** `registry/aicp_profiles.json` requires `EXT-CAPNEG`, `EXT-PARTICIPANTS`, `EXT-POLICY-EVAL`, `EXT-ENFORCEMENT`, `EXT-SECURITY-ALERT`, and `EXT-DISPUTES`.
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-CAPNEG: `conformance/extensions/CN_CAPNEG_0.1.json`
  - EXT-PARTICIPANTS: `conformance/extensions/PA_PARTICIPANTS_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - EXT-ENFORCEMENT: `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
  - EXT-SECURITY-ALERT: `conformance/extensions/SA_SECURITY_ALERT_0.1.json`
  - EXT-DISPUTES: `conformance/extensions/DS_DISPUTES_0.1.json`
  - Cross-suite reception semantics: `conformance/extensions/RC_RECEPTION_CHAT_SEMANTICS_0.1.json`
- **Intent:** Reception/chat profile for mediated blocking conversations with participant control and incident/dispute handling.
- **Canonical flows:**
  - Mediated blocking enforcement: `docs/flows/AICP_Canonical_Flows.md#24-mediated-blocking-enforcement-ext-enforcement`
  - Participant governance: `docs/extensions/RFC_EXT_PARTICIPANTS.md`
  - Security alerts and disputes references: `docs/extensions/RFC_EXT_SECURITY_ALERTS.md`, `docs/extensions/RFC_EXT_DISPUTES.md`


#### `AICP-DELEGATED-IDENTITY`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-DELEGATED-IDENTITY@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-DELEGATED-IDENTITY@0.1 -->
- **Required suites/extensions:**
- **Registry alignment note:** `registry/aicp_profiles.json` requires `EXT-CAPNEG`, `EXT-IDENTITY-LC`, and `EXT-DELEGATED-IDENTITY`.
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-CAPNEG: `conformance/extensions/CN_CAPNEG_0.1.json`
  - EXT-IDENTITY-LC: `conformance/extensions/ID_IDENTITY_LC_0.1.json`
  - EXT-DELEGATED-IDENTITY: `conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json`
- **Intent:** Bind agent senders to issuer-attested account identities with explicit scope/expiry/revocation checks for acting-on-behalf-of semantics.
- **Canonical refs:** `docs/extensions/RFC_EXT_DELEGATED_IDENTITY.md`, `docs/extensions/RFC_EXT_IDENTITY_LIFECYCLE.md`

### 2.2 Additional catalog entries

#### `AICP-AGENT-MEDIA`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-AGENT-MEDIA@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-AGENT-MEDIA@0.1 -->
- **Canonical executable catalog:** `conformance/profiles/PF_AICP_AGENT_MEDIA_0.1.json`.
- **Scope pointer:** channels, subscriptions, and publications requirements are defined by
  the registry-backed profile catalog and their existing extension suites.

#### `AICP-BAZAAR-RECEPTION`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-BAZAAR-RECEPTION@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-BAZAAR-RECEPTION@0.1 -->
- **Canonical executable catalog:** `conformance/profiles/PF_AICP_BAZAAR_RECEPTION_0.1.json`.
- **Scope pointer:** reception, admission, queue-lease, policy, and enforcement requirements
  are defined by the registry-backed profile catalog and existing extension suites.

#### `AICP-WORKFLOW-ORCHESTRATION-DELEGATION`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1 -->
- **Required suites/extensions:**
- **Registry alignment note:** `registry/aicp_profiles.json` requires `EXT-CAPNEG`, `EXT-POLICY-EVAL`, `EXT-TOOL-GATING`, `EXT-DELEGATION`, `EXT-WORKFLOW-SYNC`, `EXT-OBJECT-RESYNC`, `EXT-RESUME`, `EXT-ALERTS`, and `EXT-SECURITY-ALERT`.
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-CAPNEG: `conformance/extensions/CN_CAPNEG_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - EXT-TOOL-GATING: `conformance/extensions/TG_TOOL_GATING_0.1.json`
  - EXT-DELEGATION: `conformance/extensions/DL_DELEGATION_0.1.json`
  - EXT-WORKFLOW-SYNC: `conformance/extensions/WF_WORKFLOW_SYNC_0.1.json`
  - EXT-OBJECT-RESYNC: `conformance/extensions/OR_OBJECT_RESYNC_0.1.json`
  - EXT-RESUME: `conformance/extensions/RS_RESUME_0.1.json`
  - EXT-ALERTS: `conformance/extensions/AL_ALERTS_0.1.json`
  - EXT-SECURITY-ALERT: `conformance/extensions/SA_SECURITY_ALERT_0.1.json`
- **Intent:** Platform-moderated workflow chaining with delegated authority propagation, policy evaluation, and deterministic recovery/security signaling.
- **Platform note:** Platform runtimes may enforce additional orchestration guardrails (rate limits, step approvals, environment policies).
- **Pairing note:** To require acting-on-behalf-of subject binding, pair with `AICP-DELEGATED-IDENTITY@0.1`.




#### `AICP-POLICY-OPA-REGO`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-POLICY-OPA-REGO@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Stable.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-POLICY-OPA-REGO@0.1 -->
- **Required suites/extensions:**
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - OPA/Rego semantic profile suite: `conformance/extensions/PE_PROFILE_OPA_REGO_0.1.json`
- **Intent:** Deterministic same-bundle/same-context OPA/Rego decision interoperability.
- **Canonical spec:** `docs/profiles/AICP_Policy_Semantic_Profiles.md#aicp-policy-opa-rego-01`

#### `AICP-POLICY-ABAC-RBAC`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-POLICY-ABAC-RBAC@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Stable.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-POLICY-ABAC-RBAC@0.1 -->
- **Required suites/extensions:**
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - ABAC/RBAC semantic profile suite: `conformance/extensions/PE_PROFILE_ABAC_RBAC_0.1.json`
- **Intent:** Deterministic subject/action/resource policy dimension interpretation.
- **Canonical spec:** `docs/profiles/AICP_Policy_Semantic_Profiles.md#aicp-policy-abac-rbac-01`

#### `AICP-POLICY-LLM-SAFETY`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-POLICY-LLM-SAFETY@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Stable.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-POLICY-LLM-SAFETY@0.1 -->
- **Required suites/extensions:**
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - LLM-safety semantic profile suite: `conformance/extensions/PE_PROFILE_LLM_SAFETY_0.1.json`
- **Intent:** Deterministic transcript boundary for LLM-safety decisions with evidence-bound semantics.
- **Canonical spec:** `docs/profiles/AICP_Policy_Semantic_Profiles.md#aicp-policy-llm-safety-01`

#### `AICP-EXECUTION-INTEROP`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-EXECUTION-INTEROP@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-EXECUTION-INTEROP@0.1 -->
- **Required suites/extensions:**
- **Registry alignment note:** `registry/aicp_profiles.json` requires `EXT-EXECUTION-LIFECYCLE`, `EXT-RESUME`, and `EXT-OBJECT-RESYNC`.
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-EXECUTION-LIFECYCLE: `conformance/extensions/EX_EXECUTION_LIFECYCLE_0.1.json`
  - EXT-RESUME: `conformance/extensions/RS_RESUME_0.1.json`
  - EXT-OBJECT-RESYNC: `conformance/extensions/OR_OBJECT_RESYNC_0.1.json`
- **Intent:** Portable run/thread/store metadata interoperability with deterministic recovery/resync semantics across platforms.
- **Pairing note:** `EXT-TOOL-GATING` is recommended for side-effecting execution and approval-sensitive deployments, but is not required by this profile.



#### `AICP-COMMERCE-ACP`
<!-- BEGIN GENERATED PROFILE TRUTH: AICP-COMMERCE-ACP@0.1 -->
- **Repository availability:** Shipped.
- **Registry maturity:** Experimental.
- **Internal evidence:** Available.
- **External-IUT target:** Not available.
- **Ordinary external mark:** No external-IUT target.
- **Independent external evidence:** Absent.
<!-- END GENERATED PROFILE TRUTH: AICP-COMMERCE-ACP@0.1 -->
- **Required suites/extensions:**
- **Registry alignment note:** `registry/aicp_profiles.json` requires `EXT-CAPNEG`, `EXT-ENFORCEMENT`, `EXT-POLICY-EVAL`, `EXT-EXTERNAL-TRANSACTION`, `EXT-HUMAN-APPROVAL`, and `EXT-REDACTION`.
  - Core: `conformance/core/CT_CORE_0.1.json`
  - EXT-CAPNEG: `conformance/extensions/CN_CAPNEG_0.1.json`
  - EXT-POLICY-EVAL: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
  - EXT-ENFORCEMENT: `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
  - EXT-EXTERNAL-TRANSACTION: `conformance/extensions/ET_EXTERNAL_TRANSACTION_0.1.json`
  - EXT-HUMAN-APPROVAL: `conformance/extensions/HA_HUMAN_APPROVAL_0.1.json`
  - EXT-REDACTION: `conformance/extensions/RD_REDACTION_0.1.json`
  - Cross-extension commerce semantics: `conformance/extensions/CM_COMMERCE_ACP_PROFILE_0.1.json`
- **Intent:** Optional commerce-ready transcript interoperability profile for ACP-bridged orchestration while keeping checkout/payment rails external.
- **Canonical profile spec:** `docs/profiles/AICP_Commerce_ACP_Profile.md`

## 3. Conformance Badge Semantics
A **conformance badge** is a profile-level compatibility mark issued when all required suites for the profile pass.

Repository-owned profile runner results are internal conformance evidence. They do not prove
an independent implementation. An ordinary external product-profile mark additionally
requires an eligible full-profile external-IUT report. The current external runner targets
only Base and Authenticated Base. Both marks are reachable for complete eligible external
implementations; the repository currently contains no independent external evidence for
either profile.

Normative rules:
- Badge computation MUST be derived from machine-readable conformance reports.
- Badge issuance MUST NOT be self-asserted without report evidence.
- If any required suite fails, the profile badge MUST NOT be granted.
- If a required check is skipped or a report is degraded, profile compatibility marks MUST
  NOT be granted.

Profile runners MAY include child suite compatibility marks in profile reports for transparency, but profile-level pass/fail is determined by all required suites.

## 4. Profile Declaration & Negotiation (EXT-CAPNEG)

Platforms MAY require explicit AICP product profiles during capability negotiation.

Stable CAPNEG v0.1 is the single-profile surface:

- Declaration path: `CAPABILITIES_DECLARE.payload.required_aicp_profiles`
- Selection path: `CAPABILITIES_PROPOSE.payload.negotiation_result.selected.aicp_profile`
- Rejection path: `CAPABILITIES_REJECT` with registered `reason_code` (for example, `DOWNGRADE_NOT_ALLOWED`, `PROFILE_NOT_ACCEPTABLE`).

Experimental CAPNEG v0.2 is selected by exact payload field
`"capneg_version": "0.2"` on every CAPNEG message. It negotiates
`negotiation_result.profile_composition`, a canonical set of exact registered profile
pairs. Composition validity and derived Core/extensions/suites/marks are defined by
`registry/aicp_profile_composition_rules.json`; the resolver does not award the listed
component marks.

Operational guidance:
- A platform that requires `AICP-MEDIATED-BLOCKING@0.1` SHOULD declare it in `required_aicp_profiles` and reject proposals selecting weaker profiles.
- Product profile claims negotiated in CAPNEG are runtime claims; conformance/profile badges are separate evidence artifacts and MUST still be produced from suite/profile runners.
- Downgrade attempts are expected to be detectable deterministically via CAPNEG conformance checks.
- CAPNEG v0.1 remains stable and selects one `selected.aicp_profile`; it is not implicitly
  upgraded by a v0.2-capable peer.
- CAPNEG v0.2 composition is available only for profiles in the Core v0.1 family.
  `AICP-BASE@0.2` remains a separate Core v0.2 experiment and is explicitly
  non-negotiable in M61.
- Profile combinations elsewhere in the documentation are deployment guidance unless they
  appear in one fully accepted CAPNEG v0.2 composition.
- CAPNEG v0.2 internal evidence and all component profile reports are distinct artifacts.
  No dynamic aggregate profile compatibility mark or public external composition claim is
  defined.


## See also

- `docs/profiles/Profile_Selection_Guide.md`
- `docs/profiles/AICP_Personas_Stories_Features_Profiles.md`
- `docs/playbooks/`
- `docs/playbooks/Session_Topologies.md`
