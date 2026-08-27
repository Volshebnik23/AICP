# M67 Security Coverage Closure

## Scope and result

M67 is an internal repository-security coverage milestone. The canonical
[`threat_coverage.json`](threat_coverage.json) expands the prior manually maintained map from
13 rows (11 `Strong`, 2 `Partial`) to 36 components with final states of 24 `covered`,
12 `deferred`, and 0 `partial`. The generated [`COVERAGE_MAP.md`](COVERAGE_MAP.md) is the
human-readable projection of that authority.

Covered rows must resolve to real registered checks and, for suite evidence, to cases and
fixtures actually referenced by the suite. Protocol-observable rows cannot be closed with
documentation alone. Deferred rows identify a permitted deployment or ecosystem class,
specific rationale, owner, and residual boundary. The semantic validator rejects fake checks,
unreferenced fixtures, partial final state, and unsupported external-review or adoption claims.

## Added protocol-observable cases

- `SP-03`: a byte-identical valid prefix of the signed mediated path, rejected only for the
  suite-declared required-flow truncation check.
- `CN-13`: a later declaration removes the mediated profile and a stale proposal attempts to
  select it, rejected only by the CAPNEG profile-negotiation check.
- `ENF-03`, `ENF-04`, and `ENF-05`: target mismatch, wrong verdict reference, and unauthorized
  verdict cases with exact owning failures.
- `OR-03`, `OR-04`, and `OR-05`: positive `ACCESS_DENIED`, `TOO_LARGE`, and `REDACTED`
  mechanisms; `OR-06`: object-hash mismatch with an exact owning failure.

The associated cases are also consumed by the applicable Tier-1 evidence targets so ordinary
conformance and evidence evaluation share the same behavior.

## Evidence authority

`AICP-EVIDENCE-TCK-1.11.0` is the current strong-eligible Evidence TCK. It retains report
schema 2.2 and live trace v4, carries six targets, and expands consumer coverage for the M67
cases. Exact Evidence TCK 1.10 remains historical and strong-eligible. Its release record,
snapshot, runner-bundle manifest, and bundle digest are frozen by regression tests.

M67 does not modify the Product-IUT or Pairwise TCK release lines. Pairwise TCK 1.3 remains
the current publication-eligible pairwise authority, and no Pairwise TCK 1.4 is introduced.

## Assurance boundary

This closure records executable internal coverage and explicit deferrals. It does not claim
that the arbitrary-secret classification problem, operational rate/size policy, key custody,
endpoint security, product correctness, ecosystem adoption, or an independent security review
has been solved. The canonical repository-truth fields remain
`external_independent_review_completed: false`, an empty external-review artifact list, and
zero externally demonstrated pairwise relations.

Future independent work starts from [`EXTERNAL_REVIEW_HANDOFF.md`](EXTERNAL_REVIEW_HANDOFF.md)
and must satisfy [`external_reviews/README.md`](external_reviews/README.md).
