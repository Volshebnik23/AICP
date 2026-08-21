# AICP Repository-Truth Baseline

<!-- repo-truth-status: docs/process/repo_truth_status.json -->
<!-- repo-truth-current-version: 0.1.0-rc.1 -->

This is the canonical human-readable status baseline for the current checkout. Its
machine-checked companion is
[`repo_truth_status.json`](repo_truth_status.json). `ROADMAP.md` owns
shipped/current/next milestone status; `AICP_Backlog` owns detailed remaining work.
Normative protocol truth remains in the existing Core, extension, binding, schema, registry,
fixture, and conformance artifacts.

Refresh the structured status and all generated sections with
`python scripts/repo_truth.py --write`; `scripts/validate_planning_docs.py` compares tracked
generated content byte-for-byte with the machine companion.

Recomputed on 2026-07-27 from repository catalogs and the commands listed in
[Verification basis](#verification-basis). “Shipped” below means present in the repository;
it does not mean externally adopted, independently interoperable, certified, or production
mature.

## Status taxonomy

- **Shipped:** present in the current published repository surface.
- **Stable:** explicitly treated as a compatibility baseline that must not change silently.
- **Experimental:** testable, versioned surface outside the frozen adoption baseline.
- **Internally verified:** repository-owned runners, fixtures, and reference code pass
  repository-owned tests.
- **Externally testable:** a documented test-only adapter or harness can evaluate an
  independent implementation.
- **Externally demonstrated:** eligible evidence from at least one genuine independent
  external implementation is present.
- **Pairwise demonstrated:** two named independent implementations completed one bound joint
  execution and consumed one another’s required artifacts.
- **Known gap:** intended claims and executable evidence do not yet align.
- **Deferred:** intentionally assigned to a later versioned milestone.

<!-- BEGIN GENERATED REPO-TRUTH FACTS -->
## Machine-bound repository facts

| Fact | Current value | Machine evidence |
|---|---|---|
| Version / release phase | `0.1.0-rc.1` / `release-candidate-with-unreleased-post-rc-changes` | `VERSION`, `repo_truth_status.json` |
| Registered profiles | 16 (4 stable, 12 experimental) | `registry/aicp_profiles.json` |
| Profile IUT v1 targets | 2: `AICP-AUTHENTICATED-BASE@0.1`, `AICP-BASE@0.1` | `conformance/iut/cases.json` |
| Generalized profile evidence v2.1 targets | 3: `AICP-DELEGATED-IDENTITY@0.1`, `AICP-MEDIATED-BLOCKING@0.1`, `AICP-RESUMABLE-SESSIONS@0.1` | `conformance/evidence/targets.json` |
| Total external profile targets | 5: `AICP-AUTHENTICATED-BASE@0.1`, `AICP-BASE@0.1`, `AICP-DELEGATED-IDENTITY@0.1`, `AICP-MEDIATED-BLOCKING@0.1`, `AICP-RESUMABLE-SESSIONS@0.1` | profile IUT v1 plus generalized evidence v2.1 |
| Ordinary external marks currently reachable | 5: `AICP-AUTHENTICATED-BASE@0.1`, `AICP-BASE@0.1`, `AICP-DELEGATED-IDENTITY@0.1`, `AICP-MEDIATED-BLOCKING@0.1`, `AICP-RESUMABLE-SESSIONS@0.1` | profile catalogs and registered external target mechanisms |
| External capability targets | 1 | `conformance/evidence/targets.json` |
| Reachable external capability marks | 1 | evidence target registry and TCK provenance |
| Externally demonstrated capabilities | 0 | eligible capability-specific `eligible_targets` only |
| External binding targets | 2 | `conformance/evidence/targets.json` |
| Reachable external binding marks | 2 | evidence target registry and TCK 1.5 provenance |
| Externally demonstrated bindings | 0 | eligible binding-specific `computed_binding_marks` only |
| Real submission packages | 0 | `interop/interop_matrix.json` |
| Eligible external submissions | 0 | public interop eligibility plus typed computed profile/capability/binding evidence |
| Rejected/ineligible real packages | 0 | `interop/interop_matrix.json` |
| Externally demonstrated profiles | 0: None | eligible profile-specific `computed_profile_marks` only |
| Pairwise publication / demonstration | No / No | joint-evidence validator status |
| Live binding paths | 2: `BIND-HTTP@0.1`, `BIND-MCP@0.1` | binding evidence map |
| Independent external security review | No | `security_review/external_reviews/README.md` |
| Governance model / maturity | `maintainer_steward` / `known_gap` | `GOVERNANCE.md` |
| Registered message surface | 132 entries; 11 IDs use version-selected payload schemas; 17 missing positive fixtures | `message_surface.entries` |
| CAPNEG v0.2 | shipped / experimental / internally verified; external composition evidence=false | `conformance/extensions/CN_CAPNEG_0.2.json`, `capneg_v0_2` |
| Session-state projection v1 | shipped / experimental / internally verified / externally testable; current TCK=AICP-EVIDENCE-TCK-1.5.0; evidence target=true; reachable mark=true | `conformance/evidence/targets.json`, `capability_evidence` |
| Session-state projection v2 | shipped / experimental / internally verified; ordinary mark=false | `conformance/extensions/OR_SESSION_STATE_PROJECTION_V2.json`, `capability_evidence` |

### Milestone summary

| ID | Status | Title | Owning document |
|---|---|---|---|
| M58 | shipped | Repo-Truth Rebaseline | `ROADMAP.md` |
| M59 | shipped | Authenticated Base Evidence Reachability | `ROADMAP.md` |
| M60 | shipped | Exact Contract Agreement Core | `ROADMAP.md` |
| M61 | shipped | Multi-Profile Composition and CAPNEG v2 | `ROADMAP.md` |
| M62 | shipped | Generalized External Evidence Framework | `ROADMAP.md` |
| M63 | shipped | Tier-1 External Profile TCK | `ROADMAP.md` |
| M64 | shipped | Live Transport and Binding Interoperability | `ROADMAP.md` |
| M65 | planned | Registered Message Surface Completion | `AICP_Backlog` |
| M66 | planned | Clean-Room Pairwise Interop Harness | `AICP_Backlog` |
| M67 | planned | Security Coverage Closure | `AICP_Backlog` |
| M68 | planned | Governance and Standard Maturity | `AICP_Backlog` |
| M69 | planned | Release Engineering and RC Repackaging | `AICP_Backlog` |
| M70 | planned | External Plugfest Readiness | `AICP_Backlog` |

## Repository-truth evidence table

| Surface | Repository truth | Independent-evidence boundary | Planned gap |
|---|---|---|---|
| Profiles | 16 shipped catalogs; 5 external targets (2 `profile_iut_v1`, 3 `generalized_evidence_v2_1`) | 0 externally demonstrated profiles | M70 |
| Capability evidence | 1 external targets; 1 reachable marks | 0 externally demonstrated capabilities | M70 |
| External submissions | 0 real packages; 0 eligible | Only valid `artifact_kind=submission` rows with `evidence_validation_status=eligible` and typed expected marks/targets count | M70 |
| Pairwise | publication=false, demonstrated=false | A valid eligible joint-execution result is required | M66 |
| Bindings | 25 static cases; 2 external targets; 4 live role paths; 2 reachable marks | 0 externally demonstrated bindings; reference evidence is not external evidence | M70 |
| Security review | internal self-review=true, external completed=false | Only contracted artifacts under `security_review/external_reviews/completed/` may support completion | M67 |
| Governance | `maintainer_steward` | No external standards body is recorded | M68 |
| Message surface | 132 machine-mapped entries; 17 positive-fixture gaps | Aggregates are derived from entries | M65 |
| Profile composition | CAPNEG v0.2 is a shipped experimental internal surface | Component evidence remains separate; generalized external composition evidence is unavailable | Deferred |
| Release | `release-candidate-with-unreleased-post-rc-changes` | Repository metadata is not external adoption or GA evidence | M69 |
<!-- END GENERATED REPO-TRUTH FACTS -->

## Known discrepancies and routed work

1. **Authenticated evidence boundary:** M59 makes the ordinary Authenticated Base mark
   reachable through explicit case-local accounting. No real eligible external submission
   currently demonstrates that profile.
2. **Exact contract agreement boundary:** M60 ships separate experimental Core v0.2 exact
   artifact/head agreement. It does not reinterpret Core v0.1, authenticate senders, add an
   external-IUT target, or join projection v1 to the new reference shape.
3. **Profile composition evidence:** M61 ships internal CAPNEG v0.2 multi-profile
   composition, but it does not award component marks or provide generalized external
   composition evidence. That external target remains deferred.
4. **External evidence breadth:** two of 16 registered profiles have full external-IUT
   targets, and three Tier-1 profiles have generalized report-2.1 targets. M62 added one
   projection-v1 capability target; M63's corrected current release is
   `AICP-EVIDENCE-TCK-1.4.0`. Exact 1.1.0 projection reports remain strong-eligible, while
   frozen 1.0.0, 1.2.0, and 1.3.0 cannot support a strong claim for their documented defects.
5. **Transport evidence:** binding suites validate static case artifacts, not live endpoints.
   Routed to M64.
6. **Registered message surface:** the following experimental registered types have no
   positive conformance-referenced fixture:
   `AGENDA_DECLARE`, `AGENDA_UPDATE`, `AGENT_MIGRATION`, `ARBITRATION_REQUEST`,
   `ARBITRATION_RESULT`, `AWARD_DECLINE`, `BID_UPDATE`, `BID_WITHDRAW`, `CLAIM_BREACH`,
   `DELEGATION_REVOKE`, `KEY_REVOKE`, `PARTICIPANT_LEAVE`, `POLICY_DECISION_ATTEST`,
   `RESPONSIBILITY_REVOKE`, `RUN_CANCEL`, `SUBJECT_BINDING_REVOKE`, and `TURN_REVOKE`.
   Routed to M65; no lifecycle semantics are added here.
7. **Pairwise evidence:** publication is intentionally unavailable until one joint-run format
   binds builds, directions, and consumed artifacts. Routed to M66.
8. **Security:** the repository contains self-review and partial threat coverage, not an
   independent external review. Routed to M67.
9. **Governance and release engineering:** current lightweight governance and RC tooling are
   functional but not standard-mature or repackaged for a new RC. Routed to M68/M69.
10. **External adoption:** no real external submission is present. Plugfest readiness is
    routed to M70 without claiming product completion.

## Verification basis

The initial audit ran the repository-owned commands before assigning the statuses above.
The final sprint gate reruns them after all edits. Local Windows execution required an
explicit Python executable, CI-equivalent `jsonschema`/`pytest` dependencies, and Git Bash
as Make’s shell; that environment limitation is not counted as repository evidence.

- `make validate`
- `make conformance-all`
- `make conformance-profiles`
- `make test`
- `make conformance-iut-smoke`
- `make conformance-iut-full-reference`
- `python scripts/validate_planning_docs.py`
- `python scripts/validate_interop_submission_examples.py`
- `python scripts/validate_interop_submissions.py`
- `make interop-matrix`
- `make release-check`

See `ROADMAP.md` and `AICP_Backlog` for the M58–M70 sequence and completion criteria.
