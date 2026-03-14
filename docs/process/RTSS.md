# Repo-Truth Sync Sprint (RTSS)

## 1) What RTSS is

Repo-Truth Sync Sprint (RTSS) is a small recovery/alignment sprint (typically a focused PR) used when repository truth drifts. RTSS restores agreement between public `main`, roadmap/docs, registries/schemas/conformance, Makefile/CI executable surfaces, and remote-verifiable PR/branch state.

## 2) When to invoke RTSS

Invoke RTSS when one or more are true:
- public `main` does not reflect milestone state assumed by the working branch;
- roadmap/docs disagree with executable Makefile/CI/conformance surface;
- milestone shipped claims are ahead of landed executable artifacts;
- local work is green but PR/remote branch state is not provable;
- a sprint is blocked by repo-truth ambiguity rather than missing protocol design.

## 3) RTSS operating principles

- **Public main truth first.** Verify public `main` state before making local assumptions.
- **Recover before rewriting.** Search local branches/reflog/prior PR remnants before rebuilding from scratch.
- **Tests/suites/schema-routing first.** Before changing failing code, inspect:
  - failing suite;
  - fixture generator;
  - payload schema;
  - runner schema-routing/payload-schema lookup;
  - actual failing fixtures.
- **Smallest truthful PR.** Prefer minimal alignment fixes over broad refactors.
- **No false milestone advancement.** Do not mark milestones shipped without executable artifacts.
- **Local green != merged.** Passing local checks is not proof of landed remote state.
- **Remote-verifiable evidence matters.** PR/branch claims must be externally provable or explicitly blocked.

## 4) RTSS workflow

1. Re-read `ROADMAP.md`, `AGENTS.md`, `CONTRIBUTING.md`, and `docs/INDEX.md`.
2. Confirm public-`main` truth.
3. Compare local branch against public `main`.
4. Recover existing unmerged work before rewriting.
5. Reproduce the exact failing target locally.
6. Inspect suite + generator + schema + runner routing.
7. Apply the smallest correct fix.
8. Re-run the full verification gate.
9. Open a PR with exact verification output + remote-proof status.
10. Only then resume the next product milestone.

## 5) RTSS anti-patterns

Do not:
- code from memory when tests/suites disagree;
- claim a PR exists without remote-verifiable evidence;
- patch suite expectations to hide schema/routing bugs;
- start the next milestone while repo truth is unresolved;
- confuse milestone shipped state with extension stability wording.

## 6) RTSS outputs / exit criteria

RTSS is complete only when all are true:
- public-main truth is clear;
- roadmap/docs/Makefile/CI tell the same story;
- required verification commands are green;
- PR/branch state is remotely provable, or blocker is explicitly documented;
- no milestone is falsely advanced.

## 7) Standard verification gate

Run before opening an RTSS PR:
- `make validate`
- `make conformance`
- `make conformance-ext`
- `make conformance-bindings`
- `make test`
- `make quickstart-py`
- `make quickstart-ts`
- `cd sdk/typescript && npm ci && npm test && cd ../..`

## 8) Relationship to shipped-vs-stability wording

`ROADMAP.md` is the source of truth for milestone completion/shipped status. RFC labels such as `experimental` describe extension maturity/stability. These concepts are related but not identical.
