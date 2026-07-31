# Generalized external evidence

This directory contains the post-UAT, target-oriented external evidence path. It is
separate from the frozen product-profile IUT v1 path under `conformance/iut/`.

M62 registers one executable target:

```text
target key:      aicp.session_state_projection@v1
target kind:     capability
execution mode:  full-capability
eligible mark:   AICP-Evidence-SESSION-STATE-PROJECTION-v1
TCK release:     AICP-EVIDENCE-TCK-1.1.0
```

`targets.json` is schema-validated and resolves an exact target record to its catalog,
registered handler, and current release. Capability versions such as `v1` and future
profile/binding versions such as `0.1` use their own exact version families; only
`projection_v1` is executable today. The target catalog is derived from
`conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json` and binds one deterministic
producer scenario plus all 12 consumer transcripts. `evidence_tck_releases.json` binds the
report schema, registry and registry schema, catalog, generated import-closure bundle,
owning suite, fixtures, neutral producer scenario, and canonicalization vector by digest.
`AICP-EVIDENCE-TCK-1.0.0` remains byte-frozen historical data and is marked
`superseded-experimental` outside its frozen record; it cannot support current strong
eligibility. No real external submission depended on 1.0.0. Regenerate and check with:

```bash
python scripts/generate_evidence_framework.py --write
python scripts/generate_evidence_framework.py --check
```

## Adapter contract

The runner reuses adapter protocol 1.1 and its JSONL request/response wrapper. An eligible
implementation declares the exact capability in both immutable `describe` responses:

```json
{
  "capability_id": "aicp.session_state_projection",
  "capability_version": "v1"
}
```

The target uses `describe`, `canonicalize_hash`, `validate_transcript`, and
`project_session_state`. Requests do not disclose canonical case IDs or expected answers.
The producer receives a schema-validated neutral scenario plus a transcript prefix that
omits the final `STATE_SYNC_RESPONSE`. It derives message hashes, `as_of_message_hash`,
`msghash:` evidence references, canonical projection fields, and the projection hash.
The producer runs twice with different opaque request IDs and identical semantic input.

## Running the target

Use `--cmd-json` so the adapter command is represented without shell parsing:

```bash
python conformance/evidence/aicp_external_evidence_runner.py \
  --cmd-json '["/path/to/adapter"]' \
  --target aicp.session_state_projection@v1 \
  --mode full-capability \
  --out out/projection-v1-evidence.json
```

`smoke` is a diagnostic mode and never emits the capability evidence mark. The checked-in
reference adapter uses `implementation_kind=reference_corpus`; its full run is also
ineligible for an external mark. `fake_adapters.py --mode external_good` is a repository
test double used only to prove reachability and is not a real external submission.

The standalone `report_evaluator.py` validates report v2 through a generic envelope
evaluator plus the registered target handler. It independently recomputes target/release
resolution, subject, registry/schema/catalog and import-closed runner provenance, case
coverage, producer validation and determinism, reviewed exact consumer observations, and
the eligible mark. A raw
`compatibility_marks` string is never sufficient.

## Evidence boundaries

- Product-profile IUT report v1, its TCK releases, and `full-profile` eligibility remain
  valid and unchanged.
- Report v2 is target-oriented. Its schema reserves `product_profile`, `capability`, and
  `binding`, but M62 executes only the registered projection-v1 capability.
- A capability mark is not a product-profile mark, certification, endorsement, aggregate
  composition mark, or pairwise interoperability result.
- Digests establish consistency of the evaluated bytes; they do not establish
  organizational identity or authority.
- No real external capability submission is checked into this repository.
- Session-state projection v2 remains internal-only and is not registered here.
- Real pairwise publication remains fail-closed.

See `ADR_Generalized_External_Evidence.md` for the architectural decision and
`docs/interop/AICP_Compatibility_Claims_and_Evidence.md` for public claim rules.
