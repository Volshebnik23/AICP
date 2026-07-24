# AICP UAT Checklist

Use this checklist when starting or reviewing a pilot adoption.

## 1) Read path

- [ ] Read `START_HERE_IMPLEMENTERS.md`.
- [ ] Read `docs/release/AICP_UAT_Release_Pack.md`.
- [ ] Read `docs/release/AICP_UAT_Architecture_Freeze.md`.
- [ ] Read `docs/architecture/AICP_Adoption_Core_and_Tiers.md`.
- [ ] Read `docs/profiles/Profile_Selection_Guide.md`.
- [ ] Read `docs/process/AICP_Repo_Truth_Baseline.md`.
- [ ] Read the relevant interop docs in `docs/interop/` before publishing compatibility claims.

## 2) Pick the smallest truthful baseline

- [ ] Start with `AICP-BASE@0.1`.
- [ ] Add `AICP-MEDIATED-BLOCKING@0.1` only if mediated governance is required.
- [ ] Add `AICP-RESUMABLE-SESSIONS@0.1` only if continuity/resume/resync is required.
- [ ] Add `AICP-DELEGATED-IDENTITY@0.1` only if delegated identity authority matters.
- [ ] Treat all other shipped overlays/profiles as optional unless your pilot actually needs them.
- [ ] Do not treat pilot feedback as permission to redefine the baseline during UAT; use the freeze policy.

## 3) Run the shipped commands

- [ ] `make validate`
- [ ] `make conformance`
- [ ] `make conformance-ext`
- [ ] `make conformance-bindings`
- [ ] `make conformance-profiles`
- [ ] `make test`
- [ ] `make quickstart-py` and/or `make quickstart-ts`
- [ ] `make template-smoke`
- [ ] `make prepr` before making a public compatibility claim

## 4) Verify before claiming compatibility

- [ ] The targeted profile ID is already shipped in repo truth.
- [ ] Required suites for that profile pass.
- [ ] Any relied-on report evidence is non-degraded for the claim being made.
- [ ] An external full-profile IUT target exists for an external product claim; internal
      profile reports alone do not qualify.
- [ ] Static binding fixtures are not described as live endpoint interoperability.
- [ ] Public wording stays profile-scoped (not vague “supports AICP”).
- [ ] Adjacent layers such as discovery, IAM internals, and payment rails are not misrepresented as standardized by AICP.

## 5) Package interop evidence

- [ ] Use `docs/interop/AICP_Public_Interop_Corpus.md` and `docs/interop/AICP_Interop_Submission_Playbook.md`.
- [ ] Run `python scripts/validate_interop_submission_examples.py`.
- [ ] Run `python scripts/validate_interop_submissions.py`.
- [ ] Run `python scripts/review_interop_submission.py interop/submissions/<submission_id>` for a real package.
- [ ] Use `make interop-dryrun` if you need to rehearse the workflow without creating fake external proof.

## 6) Report findings

- [ ] Open a GitHub issue or PR with exact commands, outputs, targeted profile/binding IDs, and reproduction notes.
- [ ] If the fix would widen semantics or baseline scope, record it for explicit post-UAT review rather than treating it as an in-UAT baseline change.
- [ ] If the finding is interop-evidence-related, include the relevant submission/review artifacts.
- [ ] Keep claims and defect reports evidence-backed and narrow.
