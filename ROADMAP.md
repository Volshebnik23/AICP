# AICP Roadmap Items (repo-backed)

> Source of truth for shipped/current/next milestone status.
> `AICP_Backlog` is planning-only for remaining deliverables and should not duplicate shipped-history detail.

_Last updated: 2026-03-14_

## Current / Next

### ✅ M16b — RFC8785 float canonicalization
- **Progress:** Finite-float canonicalization landed with cross-language vector parity coverage and updated conformance/docs.

### ✅ M17 — Stability graduation (first promotions)
- **Progress:** `EXT-ENFORCEMENT` and `EXT-POLICY-EVAL` promoted to stable with anchored spec refs and productization coverage.

### ✅ M18 — Release discipline (changelog + compatibility policy + errata cadence)
- **Progress:** Errata cadence documented and validator wired into `make validate`.

### ✅ M19 — Protocol Adapter / Gateway quickstart kit (CI-first onboarding)
- **Progress:** Adapter/gateway artifacts are present and roadmap state is now aligned to shipped repo reality.

### ✅ M42–M46 — Developer-facing documentation architecture pass
- **Progress:** Canonical docs front door (`docs/INDEX.md`) shipped with role/goal navigation and cross-links across overview, profiles, architecture, playbooks, and flows.
- **Progress:** Ecosystem positioning, profile selection guide, session topology cookbook, and enforcement models docs shipped with explicit protocol-vs-adjacent-layer boundaries.
- **Progress:** Solution playbooks for reception/support, enterprise orchestration, personal-agent coordination, agent media feeds, and commerce-assisted purchase shipped with profile and dependency guidance.
- **Next concrete step:** gather implementer feedback from first integration cohorts and tighten examples/diagrams without changing protocol semantics.

### ✅ M39 — Productization hygiene: Core/template/reference/CI alignment
- **Progress:** Core narrative now explicitly matches shipped `ERROR` message set and clarifies narrative/spec/schema/conformance/reference boundaries.
- **Progress:** Python reference validator now enforces non-first `prev_msg_hash`, signature `object_hash == message_hash`, and consistent signer/`kid` key selection checks.
- **Progress:** TS agent + protocol-adapter templates are aligned to actual commands/output and now preserve onboarding-safe audit metadata.
- **Progress:** CI/test coverage now includes deterministic smoke checks for shipped onboarding templates.
- **Next concrete step:** expand template smoke checks into profile-specific onboarding packs without increasing default CI runtime significantly.

### ✅ M22 — Transport bindings and channel properties (completed)
- **Shipped:** replay-window hardening now includes additional deterministic replay evidence (`TB-HTTP-18`) plus session-scoped replay checks in runner enforcement.
- **Shipped:** multi-session interoperability is now conformance-backed with secondary-session create/send/replay coverage (`TB-HTTP-19`/`20`/`21`) and session-scope coherence checks across path/body/top-level references.
- **Shipped:** reconnect/churn coverage now includes multi-step SSE reconnect evidence (`TB-HTTP-22` chaining from `TB-HTTP-17`) with deterministic cursor continuity checks.
- **Shipped:** HTTP/WS binding RFC guidance now maps replay/idempotency/session-scope/reconnect behavior directly to shipped conformance cases.
- **Next concrete step:** keep M22 executable transport/binding surface stable while expanding enterprise controls on top of that baseline.

### ✅ M20 — Trust anchors & issuer attestations (completed)
- **Shipped:** normative M20 RFC defines canonical `trust_anchor_list` and `issuer_attestation` objects with baseline verification model and explicit M21 deferrals.
- **Shipped:** trust-signal and attestation-type registries are now in-repo and validator-enforced (`registry/trust_signal_types.json`, `registry/attestation_types.json`).
- **Shipped:** M20 schemas + deterministic fixtures + conformance suite (`TA-TRUST-ATTESTATIONS-0.1`) verify hash integrity, registry linkage, signature binding, and trust-chain resolution including untrusted-signer negative case.
- **Next concrete step:** begin M21 (Revocation/status channel) to layer revocation/status freshness onto this baseline trust model.


### ✅ M21 — Revocation/status channel (completed)
- **Shipped:** normative M21 RFC defines canonical `status_query` and `status_assertion` objects with baseline status-as-of/cache semantics and revocation-as-of checks.
- **Shipped:** minimal status and revocation-reason registries are in-repo and validator-enforced (`registry/status_assertion_codes.json`, `registry/revocation_reason_codes.json`).
- **Shipped:** M21 schema + deterministic fixtures + conformance suite (`SC-STATUS-CHANNEL-0.1`) verify hash integrity, registry linkage, trust-chain signature checks, target binding consistency, and temporal/cache validity for GOOD/REVOKED assertions.
- **Next concrete step:** maintain M21 operational reliability while enterprise control milestones advance.


### ✅ M30 — Tool/Resource/Prompt supply-chain security (immutable manifests + pinning + anti-shadowing)
- **Shipped:** normative M30 baseline RFC defines canonical artifact manifests (`tool`/`resource`/`prompt`), issuer-scoped anti-shadowing identity, contract pinning, and explicit deferrals (`docs/rfc/RFC_Artifact_Manifests_and_Pinning.md`).
- **Shipped:** baseline schema support landed for artifact manifests and contract pinning plus `TOOL_CALL_REQUEST.payload.manifest_ref` binding fields (`schemas/extensions/ext-artifact-manifests-pinning.schema.json`, `schemas/extensions/ext-tool-gating-payloads.schema.json`).
- **Shipped:** deterministic M30 fixtures and extension conformance suite verify valid pinned baseline, rug-pull expected-fail, shadowing expected-fail, and valid upgrade via explicit `CONTEXT_AMEND` renegotiation (`fixtures/extensions/tool_supply_chain/*`, `conformance/extensions/AM_ARTIFACT_MANIFESTS_PINNING_0.1.json`).
- **Next concrete step:** preserve M30 supply-chain baseline while adjacent enterprise/privacy milestones ship.


### ✅ M23 — Confidentiality & selective disclosure modes (enterprise/on-prem)
- **Current repo reality:** confidentiality RFC/schema/fixtures/suite artifacts are present and runnable in extension conformance (`docs/extensions/RFC_EXT_CONFIDENTIALITY.md`, `schemas/extensions/ext-confidentiality-artifacts.schema.json`, `conformance/extensions/CF_CONFIDENTIALITY_0.1.json`).
- **Shipped:** confidentiality binding semantics, canonical privacy modes, deterministic fixtures, and executable extension conformance are in-repo and wired through `make conformance-ext`.
- **Next concrete step:** complete M24 and then advance to next enterprise controls milestone.

### ✅ M24 — Redaction standard + retention/deletion policies
- **Shipped:** `CONTENT_REDACTED` redaction declaration, policy/proof binding, contract retention/deletion policy standardization, vault-neutral `pii_ref` pattern, deterministic fixtures, and executable extension conformance are now in-repo.
- **Shipped:** retention/deletion policy-category standardization (`retention_deletion`) is registry-backed and conformance-checked.
- **Next concrete step:** proceed to M26 (Human-in-the-loop primitive).

### ✅ M26 — Human-in-the-loop primitive (approval / step-up)
- **Shipped:** `EXT-HUMAN-APPROVAL` with canonical approval/intervention message types, strict schema, deterministic fixtures, and executable extension conformance (`HA-HUMAN-APPROVAL-0.1`).
- **Shipped:** challenge target/scope/TTL binding, signer/approver checks, anti-reuse and expiry checks, and intervention required/complete linkage are machine-checkable from transcript evidence.
- **Next concrete step:** maintain M26 baseline while M27 observability and M28 IAM bridge remain executable and aligned with CI.

### ✅ M28 — IAM bridge (OAuth/OIDC mapping for delegation/tool gating/human approval)
- **Exit:** Normative mapping guidance + examples + security notes.

### ⏳ M31 — Anti-equivocation & transparency witnessing (optional, internet-scale)
- **Exit:** Witness checkpoints + gossip + inclusion proofs + conformance for required-witness deployments.

### ⏳ M32 — Agent execution interoperability profile (optional): Runs / Threads / Stores
- **Exit:** Optional extension + profile + fixtures/conformance.

### ✅ M27 — Production attributes: tracing, SLA signals, metering
- **Shipped:** `EXT-OBSERVABILITY` RFC + schema + deterministic fixtures + executable extension conformance (`OB-OBSERVABILITY-0.1`) are in-repo and wired through `make conformance-ext`.
- **Shipped:** transcript-level `OBS_SIGNAL` artifacts now cover trace correlation, standardized SLA/error signals, and normalized metering events with machine-checkable negative vectors.
- **Next concrete step:** keep M27 observability stable while enterprise binding integrations advance under M29.

### ✅ M29 — Enterprise domain bindings (OpenAPI/OData/OPA/ABAC)
- **Shipped:** `EXT-ENTERPRISE-BINDINGS` RFC + strict payload schema + deterministic generator-backed fixtures + executable extension conformance (`EB-ENTERPRISE-BINDINGS-0.1`) are in-repo and wired through `make conformance-ext`.
- **Shipped:** enterprise binding surface now standardizes OpenAPI operation mapping, OData retrieval target mapping, and ABAC/RBAC/OPA policy cross-references as transcript-auditable references.
- **Next concrete step:** stabilize M29 contract/tool binding references while adjacent M34 security/playbook hardening progresses.

### ✅ M34 — Security & implementer playbooks (MCP-level doc completeness)
- **Shipped:** Implementer-facing security best-practices baseline plus production cookbooks for mediated blocking, OAuth bridge mapping, tool catalog pinning, and adjacent fresh-content operation are in `docs/playbooks/`.
- **Shipped:** extension-level security-considerations coverage now includes concrete implementation warnings across shipped enterprise-control and supply-chain-adjacent RFCs.
- **Next concrete step:** keep M34 guidance operationally current as extension suites and deployment patterns evolve.

### ✅ M35 — Bazaar admission & congestion control (leases, queues, anti-spam hooks)
- **Shipped:** `EXT-ADMISSION` and `EXT-QUEUE-LEASES` now provide transcript-native request/offer/accept/reject/revoke, lease grant/ack/nack/release, and overload/throttle evidence with deterministic extension conformance.
- **Shipped:** crowd-control sanction paths are machine-readable (no-silent-drop), with reason-code hooks and trust/attestation references for anti-Sybil policy integration.
- **Next concrete step:** stabilize M35 operational patterns while M36 coordination/marketplace surfaces advance.

### ✅ M36 — Multi-agent marketplace & coordination (RFW/Bids/Auction + blackboard + subchats)
- **Shipped:** `EXT-MARKETPLACE` now provides transcript-native RFW/bid/update/withdraw/award lifecycle, auction open/close modes, blackboard coordination, and subchat routing artifacts with deterministic conformance fixtures.
- **Shipped:** marketplace orchestration paths now include admission-gated participation checks, routing-attestation evidence hooks, and observability correlation vectors.
- **Next concrete step:** advance M37 provenance/responsibility transfer while keeping M36 coordination semantics operationally stable.

### ⏳ M37 — Service-chaining accountability (provenance graph + responsibility transfer + escrowed actions)
- **Exit:** EXT-PROVENANCE-GRAPH + EXT-RESPONSIBILITY + escrowed action flow binding to TOOL_GATING/M26, with audit-ready conformance.

### ⏳ M38 — Agent media & brand reception feeds (channels/topics, subscriptions, content-level CDN, group policies)
- **Exit:** EXT-CHANNELS + EXT-SUBSCRIPTIONS + EXT-FEEDS + CDN/inbox primitives + profiles for brand receptions and agent-media distribution.

## Suggested dependency order (high level)
1) M16 → M17.1 → M17 → M18 → M33
2) Interop hardening: M22 + M19
3) Trust & tooling: M20 + M21
4) Enterprise controls: M23 + M24 + M26 + M28
5) Crowd-ready bazaars: M35 (shipped baseline; keep hardening with ops playbooks)
6) Coordination & service chaining: M36 + M37
7) Internet-scale audit (recommended before large public feeds): M31
8) Agent media & brand reception feeds: M38
9) Optional platform interop: M32
10) Ops + docs completeness: M34 (with M27 and M29 executable enterprise-control surfaces shipped)
