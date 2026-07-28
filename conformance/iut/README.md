# AICP IUT Adapter Protocol 1.1

This directory defines a language-neutral, test-only adapter between the AICP TCK runner
and an Implementation Under Test (IUT). It is not an AICP wire-protocol or production
interface requirement.

The runner starts an argument-vector command with `shell=False` and exchanges one JSON
object per line over stdin/stdout. One monotonic deadline covers process creation, bounded
stdin writing, bounded stdout/stderr collection, process completion, pipe cleanup, and
child reaping. `--cmd-json` is the least ambiguous command form.

## Operations and answer isolation

- `describe` returns immutable implementation/build metadata and declared profile support.
- `canonicalize_hash` returns canonical JSON and an AICP object hash.
- `validate_transcript` receives only an opaque challenge ID, exact target profile,
  transcript, public test verification material, and neutral runtime options.
- `generate_scenario` receives a neutral producer scenario: participants, requested
  message-type sequence, explicit session/contract inputs, deterministic seed, and crypto
  mode. It never receives a fixture path or canonical case ID.
- `project_session_state` produces the strict portable state projection and its hash.

Canonical case IDs, fixture paths, expected outcomes, and invalidity labels remain inside
the runner. Generated output is validated by the runner against the selected profile's
schemas, hashes, chain invariants, semantic relations, and authentication requirements; it
is not trusted or compared byte-for-byte merely because the adapter returned it. Every
producer message is also bound to the requested exact profile, session, contract,
declared/required participants, and crypto mode. In `full-profile` mode each scenario runs
twice with distinct opaque request IDs and the same seed; both results are validated and
their canonical content digests must match.

## Smoke versus full profile

`--mode smoke` is fast CI evidence. It emits no ordinary AICP product-profile compatibility
mark, even for an external-kind adapter, and cannot support `implements_profile`,
`compatible_with_profile`, or `pairwise_interop` publication.

`--mode full-profile` derives coverage from the target profile and required suite catalogs.
The registered TCK release currently requires:

- `AICP-BASE@0.1`: **21 mandatory cases**, including all 10 `CT-CORE-0.1` transcripts and
  six neutral producer scenarios covering every positive Core message family.
- `AICP-AUTHENTICATED-BASE@0.1`: **37 mandatory cases**, comprising full Core coverage,
  every authenticated-message fixture, six authenticated producer scenarios, and the
  unavailable-crypto behavior probe.

A full product-profile mark is emitted only for a complete, passed, non-degraded
`external_implementation` execution with no skipped checks and exact registered TCK,
profile, suite, fixture/vector, runner-bundle, and generated-artifact digests. The reference
adapter always reports `execution_subject.kind=reference_corpus` and therefore receives no
external implementation profile mark, even when every functional case passes.

The authenticated catalog's required `AUTH-CRYPTO-UNAVAILABLE` case deliberately asks the
adapter to simulate an unavailable backend. Its exact degraded reason and
`AUTH-SIGNATURE-VERIFY-01` skip are a `case_local_expected` observation: matching them makes
that case pass but does not mark the TCK run degraded and does not claim that the simulated
check ran. Every normal authenticated case still requires complete Ed25519 verification.
Any unavailable backend, degraded response, or skipped check outside that explicit probe
fails the case and suppresses the profile mark.

Every consumer result must explicitly contain boolean `accepted`/`degraded` fields and
array `errors`, `degraded_reasons`, and `skipped_checks` fields. Missing or contradictory
fields fail closed. Any adapter-reported mandatory skip is recorded and suppresses eligibility,
including when an adapter incorrectly declares `degraded=false`, unless it exactly matches
the registered case-local probe expectation described above.

Runner-generated reports record each consumer response under
`case_results[].execution_observation` with an explicit `scope`, `accepted`, `degraded`,
`degraded_reasons`, and `skipped_checks`. The strong-evidence validator independently
compares those values to the registered case catalog; a passed string or raw mark is not
sufficient.

`full-profile` cannot be combined with `--include-session-state-projection`. A product
profile report covers one exact profile target; strict projection evidence must currently
be emitted through a separate smoke/capability run until overlay provenance has an explicit
report model.

Examples:

```bash
python conformance/iut/aicp_iut_runner.py \
  --cmd-json '["python","conformance/iut/reference_adapter.py"]' \
  --profile AICP-BASE@0.1 \
  --mode smoke \
  --out out/iut-base-smoke.json

python conformance/iut/aicp_iut_runner.py \
  --cmd-json '["/path/to/external-adapter","--tck"]' \
  --profile AICP-BASE@0.1 \
  --mode full-profile \
  --out out/iut-base-full.json

python conformance/iut/aicp_iut_runner.py \
  --cmd-json '["/path/to/external-adapter","--tck"]' \
  --profile AICP-AUTHENTICATED-BASE@0.1 \
  --mode full-profile \
  --out out/iut-authenticated-base-full.json
```

The current experimental release is `AICP-IUT-TCK-1.1.0`.
`AICP-IUT-TCK-1.0.0` remains frozen as historical metadata; no real external submission in
the repository depended on its superseded authenticated eligibility accounting.
`tck_releases.json` is a repository-owned release registry, not a certification authority.
An internally consistent report remains self-attested unless separately signed,
independently reproduced, and reviewed. Digests establish artifact consistency; they do not
prove organizational identity, endorsement, or non-fabrication by themselves.
