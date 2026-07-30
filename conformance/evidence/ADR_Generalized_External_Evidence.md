# ADR: Generalized provenance-bound external evidence

- **Status:** Accepted for M62
- **Decision date:** 2026-07-30
- **Scope:** external evidence for non-profile AICP targets

## Context

The existing external-IUT v1 architecture is profile-oriented and executes
`AICP-BASE@0.1` and `AICP-AUTHENTICATED-BASE@0.1` in `full-profile` mode. Strict portable
session-state projection v1 already had internal conformance and adapter operations, but
its smoke/overlay path could not produce strong, independently evaluated external
capability evidence.

## Decision

1. Keep `conformance/iut/iut_report_v1.schema.json`, adapter protocol 1.1 wrapper
   semantics, `AICP-IUT-TCK-1.0.0`, `AICP-IUT-TCK-1.1.0`, existing full-profile reports,
   and profile eligibility rules frozen. Existing Base and Authenticated Base submissions
   require no migration.
2. Add separate report format `2.0` with
   `report_type=aicp.external_evidence`. It carries one discriminated target object instead
   of requiring a product profile. The schema reserves `product_profile`, `capability`,
   and `binding`; only an exact registered executable target is eligible.
3. Reuse adapter protocol 1.1. Its open `result` object can carry
   `supported_aicp_capabilities`, so no wrapper revision is needed. Successful operation
   dispatch alone never implies capability support.
4. Register a separate deterministic release family,
   `AICP-EVIDENCE-TCK-1.0.0`, binding the report schema, target registry and catalog,
   runner/evaluator bundle, suites, input artifacts, vectors, mandatory cases, and expected
   mark. The release registry is not a certification authority.
5. Treat `AICP-Evidence-SESSION-STATE-PROJECTION-v1` as a capability evidence mark.
   Eligibility is independently recomputed from the complete external report; raw mark
   presence, internal reports, smoke runs, reference runs, and examples do not establish
   the claim.

## Rejected alternatives

- Reinterpreting report v1 or adding a synthetic profile was rejected because capability
  evidence must not weaken or silently migrate the frozen profile path.
- Adding capability semantics to `AICP-IUT-TCK` was rejected because its releases bind
  product-profile cases and eligibility.
- Revising the adapter wrapper was rejected because protocol 1.1 already supports every
  required operation and an open result payload.
- Treating internal marks, reference adapters, smoke results, or submitted mark strings as
  external proof was rejected because none establishes a complete eligible external
  subject and execution.
- Registering projection v2, Tier-1 profiles, live bindings, aggregate composition, or
  pairwise evidence was rejected as outside M62.

## Consequences

Future releases can register additional capability, product-profile, or binding targets
without changing the report family, provided each target has a deterministic catalog and
independently evaluated provenance. M62 proves that architecture with only
`aicp.session_state_projection@v1`. Capability and product-profile marks remain typed and
cannot cross-prove one another. Pairwise publication remains unavailable.
