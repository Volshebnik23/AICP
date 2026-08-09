# AICP Roadmap Items (repo-backed)

<!-- repo-truth-role: shipped-current-next -->

> Source of truth for shipped/current/next milestone status.
> `AICP_Backlog` is planning-only for remaining deliverables and should not duplicate shipped-history detail.

_Last updated: 2026-07-29_

## Current / Next

### ✅ M58 — Repo-Truth Rebaseline
<!-- milestone-status: M58 shipped -->
- **Status:** Shipped.
- **Problem:** planning, product, interoperability, security, governance, and release
  narratives do not consistently distinguish repository presence, internal verification,
  external testability, independent evidence, and future work.
- **Scope:** establish the canonical repository-truth baseline, reopen the remaining
  milestone sequence, add a mechanically checked profile/evidence map, and reconcile
  non-normative claims without changing protocol semantics.
- **Non-goals:** no new message, extension, profile, binding, wire requirement, cryptographic
  rule, or change to Core v0.1 / existing `@0.1` semantics.
- **Principal evidence gap:** the current repository has no single machine-checked status
  artifact covering profile IUT reachability, independent evidence, live bindings, security
  review, governance, release limits, and registered-message fixture gaps.
- **Dependencies:** merged M57 evidence hardening and the frozen UAT baseline.
- **Completion evidence:** every M58 Definition of Done passed under the mandatory
  validation set before the status changed to shipped. Canonical status:
  `docs/process/AICP_Repo_Truth_Baseline.md`.
- **Correction evidence:** profile maturity and external eligibility are now registry/mark
  derived; generated Markdown is byte-checked against JSON; visible milestone states are
  marker-bound; the message surface has 132 validated entries; and external security review
  completion requires a structured artifact contract. That correction did not itself start
  M59.

### ✅ M59 — Authenticated Base Evidence Reachability
<!-- milestone-status: M59 shipped -->
- **Status:** Shipped.
- **Problem:** the mandatory unavailable-crypto behavior probe passed only by copying its
  expected case-local degradation and skip into the top-level report, making the ordinary
  Authenticated Base mark structurally unreachable.
- **Scope:** introduce explicit case-local execution accounting, record schema-bound consumer
  observations, independently validate them as strong evidence, and register the changed TCK
  bytes under `AICP-IUT-TCK-1.1.0`.
- **Non-goals:** no change to authenticated wire requirements, Ed25519, message hashing,
  signing domains, profile required suites, adapter wire protocol, or identity/trust claims.
- **Dependencies:** M58 and the historical experimental `AICP-IUT-TCK-1.0.0` record.
- **Completion evidence:** all 37 mandatory Authenticated Base cases pass for a complete
  external-kind implementation; the expected `AUTH-CRYPTO-UNAVAILABLE` observation remains
  case-local; top-level degradation/skips remain empty; the exact ordinary mark is emitted;
  malformed, unexpected, forged, or genuinely degraded evidence fails closed.
- **Independent-evidence boundary:** the repository records no real eligible external
  submission; reachability is executable TCK capability, not external adoption evidence.

### ✅ M60 — Exact Contract Agreement Core
<!-- milestone-status: M60 shipped -->
- **Status:** Shipped.
- **Problem:** Core v0.1 can preserve a valid message chain while acceptance remains
  ambiguous about the exact proposal, contract bytes, and resulting active head.
- **Scope:** add a separate experimental post-UAT Core v0.2 surface, exact contract
  references, proposal/acceptance/conflict state reduction, `AICP-BASE@0.2`, deterministic
  fixtures, Python/TypeScript helpers, and versioned quickstarts.
- **Non-goals:** no Core v0.1/UAT reinterpretation, Authenticated Base 0.2, projection-v1
  composition, external-IUT target, merge/patch dialect, identity/authority/quorum, or
  transport-security claim.
- **Dependencies:** M58/M59 repository-truth and evidence boundaries; existing AICP
  object-hash algorithm.
- **Completion evidence:** `CT_CORE_0.2` passes 9 positive and 41 exact expected-fail
  transcripts. Every negative verifies failure classification plus post-rejection
  state/head/proposal/selection; Python and TypeScript consume shared vectors. Present
  optional signatures are verified, and invalid messages cannot advance state.
  Non-degraded complete execution emits `AICP-Core-0.2`, while
  `PF_AICP_BASE_0.2` also emits the internal `AICP-Profile-BASE-0.2` mark; degraded or
  skipped execution emits neither. Frozen v0.1 artifacts remain digest-guarded.
- **Independent-evidence boundary:** Base 0.2 has no external-IUT target or independent
  external evidence in M60.

### ✅ M61 — Multi-Profile Composition and CAPNEG v2
<!-- milestone-status: M61 shipped -->
- **Status:** Shipped.
- **Problem:** deployment guidance recommends combinations of registered product profiles,
  while stable CAPNEG v0.1 can select only one product profile.
- **Scope:** add a separately selected experimental CAPNEG v0.2 surface for canonical
  Core v0.1-family profile sets, deterministic registry-derived requirement union,
  declarations/supersession, proposal revisions, full-participant acceptance, independent
  composition/result hashes, Authenticated Base Ed25519 acceptance, contract binding,
  session-state projection v2, and Python/TypeScript parity.
- **Non-goals:** no CAPNEG v0.1, Core, product-profile catalog/mark, UAT, or IUT semantic
  change; no Core v0.2 composition; no dynamic profile/aggregate badge; no identity,
  authority, policy, transport, or external-conformance claim.
- **Dependencies:** shipped M60 result, stable CAPNEG v0.1, the 16 registered product
  profiles, and existing Core v0.1 hashing/envelope semantics.
- **Completion evidence:** `CN_CAPNEG_0.2` passes 20 positive and 104 exact expected-fail
  cases from a reducer-independent reviewed oracle; projection v2 passes four positive
  and nine negative temporal cases. Executable mutation controls traverse the real suite
  evaluator/comparator; message catalogs, semantic oracles, cross-language manifests, and
  projection manifests are single-source. Python/TypeScript vectors and direct tests match
  exact error origin/multiplicity, selection rules, replay/rejection/supersession behavior,
  one accepted root per context, fail-closed no-crypto reduction, contract binding,
  temporal projection, and final multi-negotiation state. Non-degraded
  execution emits only `AICP-EXT-CAPNEG-0.2`; missing schema/crypto dependencies skip
  content-derived cases, suppress the mark, and report degradation explicitly.
- **Independent-evidence boundary:** CAPNEG v0.2 and projection v2 are shipped experimental
  internal surfaces. Component profile evidence remains separate, the public submission
  schema rejects unsupported composition claims, and M62 does not register generalized
  external composition evidence.

### ✅ M62 — Generalized External Evidence Framework
<!-- milestone-status: M62 shipped -->
- **Status:** Shipped.
- **Problem:** external-IUT report v1 is bound to two product profiles, while non-profile
  capabilities had no complete target-oriented external evidence and public claim path.
- **Scope:** add a separate generalized report v2, deterministic target/TCK registries,
  independent report evaluation, typed public capability claims, and one complete
  `full-capability` target for `aicp.session_state_projection@v1`.
- **Non-goals:** no reinterpretation of profile IUT v1, Core, CAPNEG, product profiles,
  UAT, or the adapter wrapper; no projection-v2, Tier-1 profile, live binding, aggregate
  composition, real external submission, certification, or pairwise target.
- **Completion evidence:** byte-frozen `AICP-EVIDENCE-TCK-1.0.0` is historical and
  superseded; `AICP-EVIDENCE-TCK-1.1.0` binds report v2, the registry and schema, exact
  capability target/catalog/handler, generated import-closure bundle, owning suite,
  answer-isolated neutral producer scenario, canonicalization vector, and all 12
  projection-v1 consumers. A complete non-degraded
  external-kind test implementation reaches
  `AICP-Evidence-SESSION-STATE-PROJECTION-v1`; reference, smoke, incomplete, forged,
  degraded, skipped, wrong-subject, and provenance-mismatched evidence does not.
- **Public evidence boundary:** capability manifests require exact `capability_refs`,
  `implements_capability`, `capability_report`, and reproducible evidence. Capability and
  profile marks are independently computed and cannot cross-prove. The repository contains
  no real external capability submission, and pairwise publication remains fail-closed.
- **Next concrete step:** M63 ships the first generalized product-profile targets; M64
  remains planned for live transport and binding interoperability.

### ✅ M63 — Tier-1 External Profile TCK
<!-- milestone-status: M63 shipped -->
- **Status:** Shipped.
- **Problem:** the Tier-1 mediated-blocking, resumable-sessions, and delegated-identity
  profiles had internal conformance catalogs but no complete generalized external target.
- **Scope:** register exactly those three `product_profile` targets on report 2.1; freeze
  the audited 1.2.0 result and use corrected current `AICP-EVIDENCE-TCK-1.3.0` with one reusable handler, neutral producer scenarios,
  independent transcript evaluation, and all 69 required-suite consumer cases.
- **Completion evidence:** 10/9/13 deterministic producer scenarios cover the three
  profiles; full test-only external runs reach their exact ordinary profile marks, while
  reference, smoke, degraded, forged, incomplete, semantically invalid, and
  provenance-mismatched evidence remains ineligible. Public `suite_refs` are the exact
  required-suite union and reports are independently re-evaluated. Release-specific
  registry snapshots preserve eligible 1.1.0 projection reports; every producer-suite
  check is machine-accounted, and exact artifact-ID multiplicity is fail-closed.
- **Compatibility boundary:** product-profile IUT v1 and projection report 2.0 remain
  valid; Evidence TCK 1.0, 1.1, and 1.2 records are frozen. No target is added for other
  profiles, composition, live bindings, or pairwise interoperability.
- **Next concrete step:** M64 remains planned for live transport and binding
  interoperability.

## Planned milestones

Detailed remaining-work scope, non-goals, dependencies, evidence gaps, and completion
criteria live in `AICP_Backlog`.

<!-- BEGIN GENERATED PLANNED MILESTONES -->
| ID | Status | Title | Planning record |
|---|---|---|---|
| M64 | Planned | Live Transport and Binding Interoperability | `AICP_Backlog` |
| M65 | Planned | Registered Message Surface Completion | `AICP_Backlog` |
| M66 | Planned | Clean-Room Pairwise Interop Harness | `AICP_Backlog` |
| M67 | Planned | Security Coverage Closure | `AICP_Backlog` |
| M68 | Planned | Governance and Standard Maturity | `AICP_Backlog` |
| M69 | Planned | Release Engineering and RC Repackaging | `AICP_Backlog` |
| M70 | Planned | External Plugfest Readiness | `AICP_Backlog` |
<!-- END GENERATED PLANNED MILESTONES -->

## Shipped history

### ✅ M57 — Post-UAT protocol hardening and evidence truthfulness
- **Shipped:** smoke and full-profile IUT execution are distinct; smoke emits no ordinary
  product-profile mark, while full external coverage requires 21 mandatory BASE cases or
  37 mandatory authenticated-base cases from the registered TCK release.
- **Shipped:** strong external evidence is schema-, coverage-, subject-, mark-, and
  provenance-driven; incomplete, forged, degraded, skipped, reference-corpus, or
  digest-mismatched reports are rejected.
- **Shipped:** strong profile claims require reproducible external-IUT evidence;
  self-attested, legacy, instructional, and hand-shaped raw marks are never promoted by the
  matrix.
- **Shipped:** consumer result fields fail closed, adapter-reported skips are always processed,
  and full producer output is bound to scenario identity/crypto inputs plus a repeated
  canonical-digest determinism check.
- **Shipped:** full-profile capability overlays fail before adapter launch; strict session
  projection remains a separately reported capability until overlay provenance is modeled.
- **Shipped:** adapter requests use opaque challenges and neutral producer scenarios, and
  one monotonic deadline now bounds stdin, stdout/stderr, process completion, cleanup, and
  child reaping.
- **Shipped:** real pairwise publication fails closed with
  `PAIRWISE_JOINT_EVIDENCE_REQUIRED`; examples remain instructional until a dedicated
  joint-execution format exists.
- **Shipped:** ordinary conformance/profile commands retain the frozen legacy report shape;
  provenance-rich conformance/profile v1 and IUT v1 are additive post-UAT artifacts.
- **Preserved:** experimental strict portable session-state projection,
  `AICP-AUTHENTICATED-BASE@0.1`, Unicode code-point parity, sandbox signature validation,
  legacy object-resync behavior, and all existing `@0.1` profile semantics.
- **Verification:** `make prepr` (170 Python tests and 16 TypeScript tests),
  `make compatibility-gate`, `make release-check`, planning validation, full reference IUT,
  positive external-kind fake IUT, and required negative fake-adapter paths all passed on
  2026-07-22.

### M49 - Verification gate taxonomy alignment
- **Shipped:** `make prepr` is now the PR/onboarding gate and runs full conformance through `make conformance-all`, reference tests, quickstarts, template smoke, and TypeScript SDK tests.
- **Shipped:** `make compatibility-gate` and `make release-gate` now give compatibility/badge evidence and release hygiene distinct one-command entrypoints.
- **Shipped:** CI now runs `make conformance-all` instead of a partial conformance surface, so demos, ops, and security evidence suites stay aligned with PR verification.
- **Next concrete step:** keep verification-gate taxonomy stable while later structural work changes runner internals.

### M50 - Cross-platform docs path casing cleanup
- **Shipped:** removed the case-only duplicate `docs/index.md` so case-insensitive filesystems can check out the canonical `docs/INDEX.md` without dirtying the working tree.
- **Shipped:** `make validate` now includes a case-unique tracked-path guard to prevent future case-only collisions.
- **Next concrete step:** continue conformance runner modularity with behavior-preserving check-handler extraction.

### M51 - Conformance catalog metadata extraction
- **Shipped:** conformance suite/profile input-output mappings are now centralized in `conformance/runner/_suite_catalog.py` and consumed by `aicp_batch_runner.py` through named `--catalog` targets.
- **Shipped:** Makefile conformance targets now delegate to the catalog instead of carrying long duplicate `suite::report` lists.
- **Shipped:** `make validate` now checks that catalog inputs exist and report outputs are unique.
- **Next concrete step:** continue extracting focused runner check-handlers from `aicp_conformance_runner.py` without changing report semantics.

### M52 - Core transcript check-handler extraction
- **Shipped:** basic Core transcript checks now live in `conformance/runner/_runner_core_checks.py`, reducing `run_suite(...)` inline responsibilities while preserving the public runner entrypoint.
- **Shipped:** runner modularity tests cover the extracted helper failure shape.
- **Next concrete step:** continue extracting extension-specific check families behind similarly narrow helper tests.

### M53 - Enforcement transcript check-handler extraction
- **Shipped:** enforcement sanction-code and verdict-storm checks now live in `conformance/runner/_runner_enforcement_checks.py`, leaving contract-dependent enforcement checks in the main runner until they can be extracted safely.
- **Shipped:** runner modularity tests cover the extracted enforcement helper failure shape and ordering.
- **Next concrete step:** continue extracting low-coupling extension check families without changing report semantics.

### M54 - Alert transcript check-handler extraction
- **Shipped:** alert registry/action and verbosity checks now live in `conformance/runner/_runner_alert_checks.py`, with canonical JSON sizing passed in explicitly by the runner.
- **Shipped:** runner modularity tests cover the extracted alert helper failure shape and ordering.
- **Next concrete step:** extract another low-coupling extension check family or stop runner extraction once marginal risk exceeds readability gain.

### M55 - Execution lifecycle check-handler extraction
- **Shipped:** execution lifecycle run/thread/store-ref checks now live in `conformance/runner/_runner_execution_checks.py`, reducing `run_suite(...)` inline extension-specific responsibilities while preserving report semantics.
- **Shipped:** runner modularity tests cover the extracted execution helper failure shape and ordering.
- **Next concrete step:** stop low-coupling runner extraction here unless another family can be moved with similarly narrow behavioral proof.

### M56 - Media delivery check-handler extraction
- **Shipped:** channel, subscription, publication, and inbox delivery checks now live in `conformance/runner/_runner_media_checks.py`, with policy reason-code and namespaced-identifier dependencies passed in explicitly.
- **Shipped:** runner modularity tests cover the extracted media delivery helper failure shape and ordering.
- **Next concrete step:** stop behavior-preserving runner extraction unless a later refactor adds equivalent focused coverage for the remaining higher-coupling check families.

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
- **Progress:** adoption framing is now explicitly packaged via an Adoption Core and tier model so readers can distinguish the must-implement center from optional governance and ecosystem overlays without adding protocol surface.
- **Next concrete step:** gather implementer feedback from first integration cohorts and tighten examples/diagrams without changing protocol semantics.
- **Progress:** public interop corpus docs, compatibility-claims guidance, lightweight submission schema, example/template packages, and example-validation wiring now exist so profile-scoped interop evidence can be packaged without reintroducing adoption-core scope.
- **Progress:** submitter playbook, real-submission intake validation, evidence-status vocabulary, and matrix semantics now make it clearer how future external implementers can package truthful submissions without implying endorsement or fake ecosystem proof.
- **Progress:** matrix output now treats template placeholder evidence as instructional warnings while keeping real missing evidence invalid, which keeps starter packs discoverable without overstating readiness.
- **Progress:** a small interop submission builder now assembles `submission.json` plus copied `reports/` evidence from explicit CLI inputs, helping external implementers package truthful submissions without inventing metadata.
- **Progress:** optional `bundle-integrity.json` support now seals packaged submission files with SHA-256 digests so copied evidence bundles are easier to transport and review without silent drift, while remaining explicitly non-signature and non-endorsement metadata.
- **Progress:** maintainer-facing interop review workflow guidance, submitter intake templates, and a small reviewer-summary helper now make it clearer how real external submissions should be reviewed before matrix publication without overstating ecosystem maturity.
- **Progress:** a repo-owned dry-run submission package plus `make interop-dryrun` now rehearse package validation, reviewer summary output, and matrix regeneration without fabricating real external interoperability proof.
- **Progress:** a concise UAT release pack and implementer checklist now package the already-shipped Adoption Core, pilot baseline, validation path, and defect-reporting entrypoints for pilot adopters without expanding protocol surface.
- **Progress:** a dedicated UAT architecture/support freeze doc now defines the pilot-phase frozen baseline, bugfix/errata-only change envelope, and post-UAT deferral rule for findings that would widen semantics or move compatibility goalposts.

### ✅ M39 — Productization hygiene: Core/template/reference/CI alignment
### ✅ M40 — External protocol transaction bridge (protocol-neutral; ACP mapping informative-only)
- **Shipped:** `EXT-EXTERNAL-TRANSACTION` baseline is now in-repo with normative RFC surface for declaration/result linkage, irreversible-step gating, policy/approval evidence binding, receipt digest anchoring, and privacy boundaries.
- **Shipped:** extension payload schema + registry updates + deterministic pass/fail fixtures + executable conformance suite (`ET_EXTERNAL_TRANSACTION_0.1`) are wired into existing extension CI commands.
- **Next concrete step:** execute M41 as a separate optional commerce-ready profile without expanding M40 into payment or checkout protocol semantics.

### ✅ M41 — Commerce-ready profile (AICP↔ACP optional bridge profile + conformance)
- **Shipped:** optional `AICP-COMMERCE-ACP@0.1` profile is now registry-backed with normative profile documentation and profile-runner catalog wiring.
- **Shipped:** executable cross-extension commerce semantics suite (`CM_COMMERCE_ACP_PROFILE_0.1`) and deterministic profile fixtures cover CAPNEG selection, policy/approval gating, enforcement coherence, external-step anchoring, and PII-safe receipt handling.
- **Next concrete step:** treat profile hardening/expansion as future optional profile revisions without redefining AICP as a payment/checkout protocol.

### ✅ M48 — Runner modularity hardening
- **Shipped:** conformance runner schema/pointer validator helpers are now split into a private helper module while `aicp_conformance_runner.py` remains the stable CLI and `run_suite(...)` entrypoint.
- **Shipped:** compatibility shims keep the historical helper symbols available from `aicp_conformance_runner.py`, reducing missing-symbol regression risk for internal imports/tests.
- **Shipped:** repo-path resolution, report writing, and status-line formatting are now centralized in a private runner IO helper and reused by the suite, batch, and profile CLIs without changing report semantics.
- **Shipped:** suite/binding report-record assembly is now centralized in a private reporting helper instead of being duplicated inline in the monolithic runner.
- **Next concrete step:** keep runner internals maintainable with similarly narrow extractions only when behavior-preserving coverage exists.

### ✅ M47 — Adjacent protocol integration patterns and ecosystem stack guidance
- **Shipped:** ecosystem architecture guidance is now strengthened with clearer replace/complement/reference/orthogonal boundaries and operational “use AICP when / not when” selection guidance.
- **Shipped:** informative `docs/adjacent/A2A_Integration_Pattern.md` added with layered composition model and practical rendezvous/bootstrap, specialist handoff, relay/fallback, and failure-continuity guidance.
- **Shipped:** docs front-door/guides/playbooks now cross-link adjacent integration guidance for faster architect discovery without changing protocol semantics.
- **Next concrete step:** collect implementer feedback and iterate examples while preserving strict non-normative adjacent-layer boundaries.
- **Progress:** foreign-runtime interoperability hardening guidance now exists as a concise playbook covering truthful adapter claims, deterministic CAPNEG rejection, approval-boundary separation, delegated-identity ambiguity, and resume-vs-resync limits for heterogeneous external runtimes without implying vendor support.
- **Progress:** EXT-CAPNEG conformance now also checks deterministic profile-rejection reason semantics so unsupported-vs-unacceptable profile mismatches produce machine-checkable rejection evidence instead of only generic failure.
- **Next concrete step:** add a small cross-extension dry-run that combines CAPNEG rejection, delegated identity, approval, and resume/resync stress in one adapter-mediated interop rehearsal.

- **Progress:** Core narrative now explicitly matches shipped `ERROR` message set and clarifies narrative/spec/schema/conformance/reference boundaries.
- **Progress:** Python reference validator now enforces non-first `prev_msg_hash`, signature `object_hash == message_hash`, and consistent signer/`kid` key selection checks.
- **Progress:** Python and TypeScript transcript chain helpers now symmetrically enforce Core `prev_msg_hash` semantics for non-first records, including missing/empty-field rejection and deterministic mismatch errors.
- **Progress:** shared helper parity is now documented explicitly across the Python reference layer and TypeScript SDK, with fixture-backed regression coverage for canonicalization/hash/chain overlap and a Unicode code-point key-order fix in the TS canonicalizer.
- **Progress:** Core conformance now includes an expected-fail transcript for schema-admissible empty `contract_id` envelopes plus direct regression coverage for multi-step hash-chain corruption, reinforcing the permissive-boundary/strict-semantic split without widening Core schemas.
- **Progress:** TS agent + protocol-adapter templates are aligned to actual commands/output and now preserve onboarding-safe audit metadata.
- **Progress:** CI/test coverage now includes deterministic smoke checks for shipped onboarding templates.
- **Next concrete step:** add similarly targeted Core regressions for contract/version-reference semantics and replay-like identity linkage edge cases without broadening runtime behavior.

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

### ✅ M31 — Anti-equivocation & transparency witnessing (optional, internet-scale)
- **Shipped:** `EXT-TRANSCRIPT-WITNESS` now provides transcript-native checkpoint commitments, witness submit/receipt evidence, head exchange artifacts, and inclusion-proof declarations with deterministic pass/expected-fail conformance.
- **Shipped:** equivocation detection (conflicting heads for same session/sequence), receipt linkage validation, and optional non-repudiation strengthening checks are executable in extension runner semantics.
- **Next concrete step:** keep M31 witness semantics stable while M32 execution interoperability remains operationally aligned.

### ✅ M32 — Agent execution interoperability profile (optional): Runs / Threads / Stores
- **Shipped:** `EXT-EXECUTION-LIFECYCLE` now provides transcript-native run/thread lifecycle metadata (`RUN_*`, `THREAD_*`) plus hash-bound `store_ref`/`memory_ref` objects with deterministic pass/expected-fail conformance.
- **Shipped:** `AICP-EXECUTION-INTEROP@0.1` profile now bundles Core + `EXT-EXECUTION-LIFECYCLE` + `EXT-RESUME` + `EXT-OBJECT-RESYNC` for portable execution metadata and recovery/resync interoperability.
- **Next concrete step:** keep M32 execution metadata semantics stable while progressing M33 legal readiness artifacts.

### ✅ M27 — Production attributes: tracing, SLA signals, metering
- **Shipped:** `EXT-OBSERVABILITY` RFC + schema + deterministic fixtures + executable extension conformance (`OB-OBSERVABILITY-0.1`) are in-repo and wired through `make conformance-ext`.
- **Shipped:** transcript-level `OBS_SIGNAL` artifacts now cover trace correlation, standardized SLA/error signals, and normalized metering events with machine-checkable negative vectors.
- **Next concrete step:** keep M27 observability stable while enterprise binding integrations advance under M29.


### ✅ M25 — Policy semantic interoperability profiles (OPA/Rego, ABAC/RBAC, LLM-safety)
- **Shipped:** three optional semantic profiles (`AICP-POLICY-OPA-REGO@0.1`, `AICP-POLICY-ABAC-RBAC@0.1`, `AICP-POLICY-LLM-SAFETY@0.1`) now have normative profile docs, profile registry entries, and executable conformance profile catalogs.
- **Shipped:** deterministic fixtures and semantic conformance suites now cover same-bundle/same-context determinism, registered language/binding enforcement, reason-code determinism, ABAC/RBAC interpretation consistency, and LLM-safety evidence-bound boundaries.
- **Shipped:** key policy registries (`policy_languages`, `policy_bindings`, selected `policy_reason_codes`) are promoted to stable with compatibility notes anchored to shipped M25 normative/profile artifacts.
- **Next concrete step:** expand vendor-pair interoperability submissions against the shipped M25 profile suites without widening protocol surface.

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
- **Shipped (RTSS closeout):** conformance runner now enforces M35 admission/queue-lease semantics explicitly (renewal linkage, attestation/stake reference validity, no-silent-drop, bounded lease usage, overload/backpressure checks) and shipped-coverage validation includes expected-fail/reject+revoke guardrails.
- **Next concrete step:** keep M35 operational patterns stable while M36 coordination/marketplace surfaces continue hardening.

### ✅ M36 — Multi-agent marketplace & coordination (RFW/Bids/Auction + blackboard + subchats)
- **Shipped:** `EXT-MARKETPLACE` now provides transcript-native RFW/bid/update/withdraw/award lifecycle, auction open/close modes, blackboard coordination, and subchat routing artifacts with deterministic conformance fixtures.
- **Shipped:** marketplace orchestration paths now include admission-gated participation checks, routing-attestation evidence hooks, and observability correlation vectors.
- **Shipped (RTSS closeout):** canonical M36 message family (`RFW_POST`, `BID_*`, `AWARD_*`, `AUCTION_*`, `BLACKBOARD_*`, `SUBCHAT_*`) is now consistently enforced across schema/registry/suite/generator/runner, including explicit expected-fail `MP-AWARD-01` coverage for award/work-order linkage coherence.
- **Next concrete step:** advance M37 provenance/responsibility transfer while keeping M36 coordination semantics operationally stable.

### ✅ M37 — Service-chaining accountability (provenance graph + responsibility transfer + escrowed actions)
- **Shipped:** `EXT-PROVENANCE` now ships executable DAG + append-only linkage semantics with deterministic pass/expected-fail conformance vectors.
- **Shipped:** `EXT-RESPONSIBILITY` now ships explicit assign/accept/revoke transfer lifecycle plus `CHAIN_FAILURE_ATTEST` classification/retry/rollback evidence checks.
- **Shipped:** `EXT-ACTION-ESCROW` now ships executable prepare/approve/commit enforcement with required hash-binding checks and negative conformance vectors.
- **Next concrete step:** keep M37 accountability surfaces operationally stable while closing out M38 channel/subscription/publication delivery semantics.

### ✅ M38 — Agent media & brand reception feeds (channels/topics, subscriptions, publication delivery, inbox policies)
- **Shipped:** canonical M38 model uses `EXT-CHANNELS` + `EXT-SUBSCRIPTIONS` + `EXT-PUBLICATIONS` + `EXT-INBOX` (feeds terminology is treated as publication-surface alias, not a separate extension ID).
- **Shipped:** channel hierarchy/state, subscription cursor semantics, publication update/retract reason-code and must-reach delivery proof hooks, and inbox queue/admission linkage are executable with pass + expected-fail extension conformance.
- **Next concrete step:** advance M42 content-origin disclosure while keeping M38 distribution semantics operationally stable.

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
