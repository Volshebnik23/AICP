# AICP Repository-Truth Baseline

<!-- repo-truth-status: docs/process/repo_truth_status.json -->
<!-- repo-truth-current-version: 0.1.0-rc.1 -->

This is the canonical human-readable status baseline for the current checkout. Its
machine-checked companion is
[`repo_truth_status.json`](repo_truth_status.json). `ROADMAP.md` owns
shipped/current/next milestone status; `AICP_Backlog` owns detailed remaining work.
Normative protocol truth remains in the existing Core, extension, binding, schema, registry,
fixture, and conformance artifacts.

Recomputed on 2026-07-24 from repository catalogs and the commands listed in
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

## Current release and baseline

- **Version:** `0.1.0-rc.1`, from [`VERSION`](../../VERSION). The repository contains
  post-RC work that is not represented as another published release; see
  [`RELEASE_NOTES.md`](../../RELEASE_NOTES.md) and [`CHANGELOG.md`](../../CHANGELOG.md).
- **Release phase:** release candidate, not GA. The snapshot discipline still uses
  `AICP-SNAPSHOT-0.1.0-dev`; that packaging mismatch is recorded for M69 rather than fixed
  in this sprint. Evidence:
  [`generate_snapshot_manifest.py`](../../scripts/generate_snapshot_manifest.py) and
  [`AICP_SNAPSHOT_0.1.0-dev.json`](../../dist/releases/snapshots/AICP_SNAPSHOT_0.1.0-dev.json).
- **Frozen UAT/adoption baseline:** Core v0.1 plus the conservative pilot profile center
  (`AICP-BASE`, mediated blocking, resumable sessions, delegated identity). This is a support
  envelope, not a statement that all four profiles have stable registry status. Evidence:
  [`AICP_UAT_Architecture_Freeze.md`](../release/AICP_UAT_Architecture_Freeze.md) and
  [`AICP_UAT_Release_Pack.md`](../release/AICP_UAT_Release_Pack.md).
- **Post-UAT experiments:** `AICP-AUTHENTICATED-BASE@0.1`, strict
  `aicp.session_state_projection.v1`, provenance-rich report formats, and the external-IUT
  TCK are additive experiments. Evidence:
  [`AICP_UAT_Architecture_Freeze.md`](../release/AICP_UAT_Architecture_Freeze.md),
  [`tck_releases.json`](../../conformance/iut/tck_releases.json), and
  [`conformance/iut/README.md`](../../conformance/iut/README.md).

## Recomputed repository facts

| Fact | Current value | Evidence |
|---|---:|---|
| Registered product profiles | 15 (4 stable, 11 experimental) | [`registry/aicp_profiles.json`](../../registry/aicp_profiles.json) |
| Internal profile catalogs | 15; all passed `make conformance-profiles` in this audit | [`_suite_catalog.py`](../../conformance/runner/_suite_catalog.py) and verification output |
| External-IUT profile targets | 2: `AICP-BASE@0.1`, `AICP-AUTHENTICATED-BASE@0.1` | [`cases.json`](../../conformance/iut/cases.json) |
| Ordinary external profile mark reachable | 1 target: `AICP-BASE@0.1`, for a complete non-degraded external-implementation run | [`aicp_iut_runner.py`](../../conformance/iut/aicp_iut_runner.py) and [`test_iut_evidence_remediation.py`](../../reference/python/tests/test_iut_evidence_remediation.py) |
| Authenticated full-profile target | 37 mandatory cases; passes behaviorally but its required unavailable-crypto probe degrades and suppresses the mark | [`cases.json`](../../conformance/iut/cases.json), [`conformance/iut/README.md`](../../conformance/iut/README.md), and the tracked full reference report |
| Strict state projection | Internal suite plus separate smoke/capability IUT path; no full-profile overlay or ordinary mark | [`OR_SESSION_STATE_PROJECTION_V1.json`](../../conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json) and [`aicp_iut_runner.py`](../../conformance/iut/aicp_iut_runner.py) |
| Real independent external submissions | 0 | [`interop_matrix.json`](../../interop/interop_matrix.json) |
| Pairwise publication | unavailable; real pairwise claims fail with `PAIRWISE_JOINT_EVIDENCE_REQUIRED` | [`interop_submission_validation.py`](../../scripts/interop_submission_validation.py) |
| Live transport interoperability | none demonstrated; HTTP/WS/SSE has 21 static case files and MCP has 3 | [`TB_HTTP_WS_0.1.json`](../../conformance/bindings/TB_HTTP_WS_0.1.json) and [`TB_MCP_0.1.json`](../../conformance/bindings/TB_MCP_0.1.json) |
| Registered message types | 132; all have payload-schema and suite mapping, but 17 have no positive conformance-referenced fixture | [`registry/message_types.json`](../../registry/message_types.json), conformance catalogs, and the mechanically checked companion |
| Independent external security review | not completed; only an internal self-review and review scaffolding are present | [`SELF_REVIEW.md`](../../security_review/SELF_REVIEW.md), [`security_review/README.md`](../../security_review/README.md), and the template-only remediation log |
| Governance | current maintainer/steward model is usable but does not define a mature external standards body or voting process | [`GOVERNANCE.md`](../../GOVERNANCE.md) |

## Repository-truth evidence table

| Surface | Repository status | Internal executable evidence | External test path | Independent evidence | Known limitation | Planned milestone |
|---|---|---|---|---|---|---|
| Core v0.1 | Shipped, stable UAT baseline | `CT_CORE_0.1`, schemas, fixtures, reference tests | `AICP-BASE@0.1` full-profile IUT | None present | No real external submission | M70 |
| `AICP-BASE@0.1` | Shipped, stable, internally verified, externally testable | Profile catalog/report and 21-case full target | Full-profile external IUT; ordinary mark reachable for an eligible external subject | None present | Reference runs never prove an external product | M70 |
| `AICP-AUTHENTICATED-BASE@0.1` | Shipped, experimental, internally verified, externally testable | Profile/security suites and 37-case full target | Full-profile external IUT | None present | Mandatory degraded probe makes the ordinary mark unreachable | M59 |
| Strict session-state projection | Shipped, experimental, internally verified, externally testable | Dedicated suite and reference projection helper | Separate smoke/capability run | None present | Cannot be combined with full-profile evidence; no strong capability report | M62 |
| Mediated blocking | Shipped, experimental, internally verified | Profile and extension suites | No full-profile IUT target | None present | Internal profile evidence only | M63 |
| Resumable sessions | Shipped, experimental, internally verified | Profile, RESUME, and OBJECT_RESYNC suites | No full-profile IUT target | None present | Internal profile evidence only | M63 |
| Delegated identity | Shipped, experimental, internally verified | Profile, CAPNEG, identity-lifecycle, and delegated-identity suites | No full-profile IUT target | None present | Internal profile evidence only | M63 |
| CAPNEG/profile composition | Shipped single-profile negotiation; internally verified | `CN_CAPNEG_0.1` and profile suites | No composition-specific external target | None present | Selection carries one `aicp_profile`; documented combinations are not negotiated composition | M61 |
| HTTP/WS/SSE binding | Shipped static semantics and internally verified fixtures | 21 static case files, 14 checks | No live independent harness | None present | Static evidence does not demonstrate live network interoperability | M64 |
| MCP binding | Shipped static semantics and internally verified fixtures | 3 static case files, 1 check | No live independent harness | None present | Static evidence does not demonstrate live MCP interoperability | M64 |
| External IUT | Shipped, experimental, externally testable | Reference adapter smoke/full runs | Test-only JSONL adapter for 2 exact profiles | None present | Not generalized to the other 13 profiles or capability overlays | M62, M63 |
| Public interop corpus | Shipped packaging and validation tooling | Examples, template, and one dry run | PR intake for eligible external reports | No real submissions | Examples/dry runs are non-promotable | M70 |
| Pairwise interoperability | Known gap, fail-closed | Negative validator tests | None until joint format exists | None present | Two independent reports are insufficient | M66 |
| External security review | Deferred | Internal self-review, threat map, negative tests | Review package only | No external report | Two coverage-map rows remain partial; no independent reviewer artifact | M67 |
| Governance maturity | Current maintainer/steward model; known gap | Repository process and PR gates | Not applicable | No external standards body recorded | Roles, voting, appeals, and standard-maturity path are underspecified | M68 |
| Release readiness | RC metadata checks pass; post-RC work unreleased | `make release-check`, snapshot validator | Not applicable | No release/publication proof beyond repository metadata | Dev-named snapshot, mixed tracked generated reports, local dependency/shell bootstrap gaps | M69 |

## Known discrepancies and routed work

1. **Authenticated evidence reachability:** the required degraded probe suppresses the
   authenticated ordinary mark. Routed to M59.
2. **Exact contract agreement:** Core allows optional `contract_ref`, but the repository has
   no dedicated exact contract-version/hash agreement claim or suite. Any semantic design is
   deferred to M60.
3. **Profile composition:** CAPNEG selects one product profile while product guidance
   recommends combinations. Combination guidance is deployment composition, not implemented
   multi-profile negotiation. Routed to M61.
4. **External evidence breadth:** only two of 15 registered profiles have full external-IUT
   targets; strict projection uses a separate weaker capability path. Routed to M62/M63.
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
