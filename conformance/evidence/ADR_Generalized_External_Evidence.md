# ADR: Generalized provenance-bound external evidence

- **Status:** Accepted for M62; extended and corrected by M63 and M64
- **Decision date:** 2026-08-08
- **Scope:** target-oriented external evidence for capabilities, exact product profiles,
  and exact live transport bindings

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
   `AICP-AUTHENTICATED-BASE@0.1`. Add report 2.1 for exactly
   `AICP-MEDIATED-BLOCKING@0.1`, `AICP-RESUMABLE-SESSIONS@0.1`, and
   `AICP-DELEGATED-IDENTITY@0.1`. Freeze the audited Evidence TCK 1.2.0 as historical
   and strong-ineligible. Freeze 1.3.0 as historical and strong-ineligible because it did
   not close generated messages over their exact owner payload schemas or match ordinary
   namespace semantics; corrected 1.4.0 is current for all four generalized targets.
   Exact report-2.0/TCK-1.1.0 projection evidence remains strong-eligible.
7. Use one registered `product_profile_v01` handler. Producer challenges contain neutral
   facts, never case IDs, fixture paths, golden messages/hashes, or expected marks. The
   runner validates returned transcripts independently in memory, including every check
   ID derived from required suites, private exact flow sequences, cryptographic and
   lifecycle semantics, without golden-byte equality. Unknown checks fail closed.
8. Bind report registry provenance to immutable per-release snapshots, self-check the
   actual runtime import-closure digest, let handlers select report-2.1 artifact kinds,
   and require exact generated-artifact ID `Counter` equality before map construction.
9. A report proves one exact target. Public profile claims accept either frozen profile-IUT
   v1 or generalized report 2.1 only after independent evaluation, and `suite_refs` must
   exactly identify the claimed profiles' required-suite union.
10. For generated Tier-1 transcripts, derive message-owner payload routes from the union
    of exact v0.1 suite metadata rather than from only a scenario's primary suites. Missing
    or conflicting routes fail catalog validation. Mirror the ordinary narrow namespace
    predicate for PE reason codes and CAPNEG privacy modes while retaining the intentionally
    broader Core policy-category and enforcement-sanction predicates.
11. Freeze Evidence TCK 1.4 byte-for-byte and make 1.5 current. Report 2.2 adds one strict
    `live_binding_trace` artifact without changing report 2.0 or 2.1. Historical 1.1 and
    1.4 reports retain strong eligibility under their frozen release snapshots.
12. Register only `BIND-HTTP@0.1` and `BIND-MCP@0.1` as `binding` targets. One report
    proves one exact binding. Full-binding eligibility requires both roles of the same
    implementation ID, version, kind, and digest, executed twice from clean state.
13. Live evidence crosses real boundaries: HTTP/SSE/WebSocket use literal-loopback sockets;
    MCP uses JSON-RPC over a child process's stdin/stdout. A ready-file descriptor is
    test-control metadata, not an AICP wire protocol. Commands are argument vectors with
    `shell=false`; endpoints, streams, frames, lines, diagnostics, and deadlines are bounded.
14. Mandatory HTTP request/response semantics always run. Declared optional SSE or
    WebSocket support makes the corresponding live scenarios mandatory; an undeclared
    optional transport neither passes nor fails those scenarios. The reference
    implementation declares and exercises both.
15. Store only schema-allowlisted observations. Authorization, cookies, bearer values,
    environment dumps, ready paths, and key material are structurally absent. Normalize
    sessions, opaque cursors, and JSON-RPC IDs by first-seen symbols before comparing the
    two semantic digests; preserve message IDs/hashes and every relationship.
16. Public binding claims use `implements_binding`, exact `binding_refs`,
    `binding_report`, exact owning `suite_refs`, and reproducible evidence. Binding marks
    remain separate from profile and capability marks. Repository reference runs, smoke or
    one-role runs, examples, and test doubles cannot become external demonstrations.
17. Freeze Evidence TCK 1.6 byte-for-byte and make 1.7 current. TCK 1.5 is
    strong-ineligible because trace v1 encoded runner conclusions, inherited ambient
    credentials, and omitted complete WebSocket/WSS and MCP cursor evidence. TCK 1.6 kept
    report 2.2 but requires trace v2 transport exchanges, an allowlisted child environment,
    exact Idempotency-Key delimiters, verified RFC 6455 handshakes, real per-run WSS, and
    two-poll MCP cursor correlation; it is now historical/ineligible because predictable
    reference values did not prove client response causality or certificate verification.
    TCK 1.7 uses opaque response challenges, sequential MCP construction, a public scenario
    projection, and repository-observed trusted/untrusted WSS trace v3 evidence. Exact 1.1
    and 1.4 reports remain eligible.

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
- Registering every profile, a multi-profile composition, projection v2, BIND-BUS live
  evidence, remote public endpoints, or pairwise evidence was rejected. M64 selects only
  the HTTP and MCP bindings; pairwise work remains M66.

## Consequences

Future releases can register additional capability, product-profile, or binding targets
without changing the report family: exact target keys use kind-appropriate versions and
dispatch through an explicit handler registry. Unknown handlers fail closed. M62 proves
that architecture with `aicp.session_state_projection@v1`; M63 proves reusable
product-profile execution without altering the frozen v1 IUT path.
Producer scenarios expose raw facts and a response-free transcript prefix, never the
reviewed projection/hash. Capability, product-profile, and binding marks remain typed and
cannot cross-prove one another. Reference loopback proves the harness, not independent
external evidence. Projection v2 stays internal and pairwise publication remains
unavailable.
