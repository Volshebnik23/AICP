# ADR: Generalized provenance-bound external evidence

- **Status:** Accepted for M62; extended by M63
- **Decision date:** 2026-08-08
- **Scope:** target-oriented external evidence for capabilities and exact product profiles

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
4. Preserve `AICP-EVIDENCE-TCK-1.0.0` as a byte-frozen historical experimental record.
   Its producer request disclosed the ready-made projection, so supersession metadata
   makes it ineligible for current strong claims. No real external submission depended on
   that release. `AICP-EVIDENCE-TCK-1.1.0` binds the answer-isolated scenario and schema,
   target registry and registry schema, catalog, handler, evaluator, generated import-
   closure bundle, suites, reviewed inputs, mandatory cases, and expected mark.
5. Treat `AICP-Evidence-SESSION-STATE-PROJECTION-v1` as a capability evidence mark.
   Eligibility is independently recomputed from the complete external report; raw mark
   presence, internal reports, smoke runs, reference runs, and examples do not establish
   the claim.
6. Keep product IUT v1 frozen for `AICP-BASE@0.1` and
   `AICP-AUTHENTICATED-BASE@0.1`. Add report 2.1 and Evidence TCK 1.2.0 for exactly
   `AICP-MEDIATED-BLOCKING@0.1`, `AICP-RESUMABLE-SESSIONS@0.1`, and
   `AICP-DELEGATED-IDENTITY@0.1`; projection v1 remains on report 2.0/TCK 1.1.0.
7. Use one registered `product_profile_v01` handler. Producer challenges contain neutral
   facts, never case IDs, fixture paths, golden messages/hashes, or expected marks. The
   runner validates returned transcripts independently in memory, including cryptographic
   and lifecycle semantics, without golden-byte equality.
8. A report proves one exact target. Public profile claims accept either frozen profile-IUT
   v1 or generalized report 2.1 only after independent evaluation, and `suite_refs` must
   exactly identify the claimed profiles' required-suite union.

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
- Registering every profile, a multi-profile composition, projection v2, live bindings, or
  pairwise evidence was rejected. M63 deliberately selects only the three Tier-1 profiles;
  live binding and pairwise work remain M64 and M66.

## Consequences

Future releases can register additional capability, product-profile, or binding targets
without changing the report family: exact target keys use kind-appropriate versions and
dispatch through an explicit handler registry. Unknown handlers fail closed. M62 proves
that architecture with `aicp.session_state_projection@v1`; M63 proves reusable
product-profile execution without altering the frozen v1 IUT path.
Producer scenarios expose raw facts and a response-free transcript prefix, never the
reviewed projection/hash. Capability and product-profile marks remain typed and cannot
cross-prove one another. Projection v2 stays internal and pairwise publication remains
unavailable.
