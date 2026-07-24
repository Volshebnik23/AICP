# Contributing

Thanks for helping improve AICP.

## Process

- Follow the repository `AGENTS.md` for Agent-First SDD rules.
- Keep PRs small, focused, and verifiable.
- If normative meaning changes, update matching schemas/fixtures/conformance in the same PR.
- Do not hand-edit golden transcripts; regenerate deterministically and document how.

## Before starting any sprint

Quick pre-flight checklist:

- Re-read `ROADMAP.md` and `AGENTS.md`.
- Confirm current verification targets in `Makefile` and `.github/workflows/ci.yml`.
- If working on an extension milestone, confirm discoverability/IDs in `registry/` and related extension docs.
- Read `docs/process/AICP_Repo_Truth_Baseline.md` when the work depends on current evidence,
  external-IUT coverage, interop, security-review, governance, or release status.

## When to do a Repo-Truth Sync Sprint (RTSS)

If local assumptions, public `main`, roadmap/docs, and executable CI surfaces drift out of sync, pause feature work and run a small **Repo-Truth Sync Sprint (RTSS)** PR first. See `docs/process/RTSS.md` for the canonical RTSS definition and workflow. A clean working tree is not proof there is nothing to PR—always compare against public `main` and verify remote branch/PR state.

## Local checks

Run before opening a PR:

- `make prepr`

Use individual targets below while isolating failures:

- `make validate`
- `make conformance`
- `make conformance-ext`
- `make conformance-bindings`
- `make conformance-profiles`
- `make conformance-all`
- `make test`
- `make quickstart-py`
- `make quickstart-ts`
- `make template-smoke`
- `cd sdk/typescript && npm ci && npm test && cd ../..`

Run `make compatibility-gate` when making compatibility or badge claims. Run `make release-gate` before release hygiene PRs.

Use the PR template and include risk and compatibility impact.

Reminder: reproduce the exact failing CI/local target first before editing (for example run `make conformance-ext` before touching extension code), then trace suite + generator + schema + runner routing from executable artifacts.

## Contribution licensing and sign-off

AICP uses a **DCO 1.1 sign-off workflow** and does **not** require a separate CLA for ordinary repository contributions.

By contributing, you agree that your contribution is accepted under the repository license terms that apply to the files you change:

- Apache-2.0 for code and software-oriented materials covered by [`LICENSE`](LICENSE)
- CC BY 4.0 for docs, specs, schemas, fixtures, examples, and other reference artifacts covered by [`LICENSE-docs`](LICENSE-docs)

Read the canonical DCO text in [`DCO`](DCO).

### How to sign off commits

Use `git commit -s` so Git adds a `Signed-off-by:` trailer automatically, or add the trailer manually in the exact form below:

```text
Signed-off-by: Your Name <your.email@example.com>
```

Examples:

```bash
git commit -s -m "docs: clarify legal readiness pack"
```

```bash
git commit -m "docs: clarify legal readiness pack"
# then add:
# Signed-off-by: Your Name <your.email@example.com>
```

### DCO / CLA policy

- **DCO required:** yes
- **CLA required:** no
- **Inbound = repository licensing:** yes

If you cannot certify the DCO for a contribution, please do not submit it until the issue is resolved.

## Patent and trademark notes

- If you know of patent claims you own or control that may be necessarily infringed by a proposed normative change, disclose that context in the PR or issue thread. See [`PATENTS.md`](PATENTS.md).
- Do not imply project endorsement, certification, or official compatibility beyond what you can substantiate from shipped repository artifacts and conformance evidence. See [`TRADEMARKS.md`](TRADEMARKS.md).
