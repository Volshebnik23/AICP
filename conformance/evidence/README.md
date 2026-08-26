# Generalized external evidence

This directory contains the post-UAT, target-oriented external evidence path. It is
separate from the frozen product-profile IUT v1 path under `conformance/iut/`.

M62 retains one executable capability target:

```text
target key:      aicp.session_state_projection@v1
target kind:     capability
execution mode:  full-capability
eligible mark:   AICP-Evidence-SESSION-STATE-PROJECTION-v1
historical TCK:  AICP-EVIDENCE-TCK-1.1.0 (strong-eligible exact reports)
current TCK:     AICP-EVIDENCE-TCK-1.10.0
```

M63 adds exactly three product-profile targets:

```text
AICP-MEDIATED-BLOCKING@0.1  -> AICP-Profile-MEDIATED-BLOCKING-0.1
AICP-RESUMABLE-SESSIONS@0.1 -> AICP-Profile-RESUMABLE-SESSIONS-0.1
AICP-DELEGATED-IDENTITY@0.1 -> AICP-Profile-DELEGATED-IDENTITY-0.1
```

They use report 2.2 for new executions, `full-profile`, `product_profile_v01`, and current
`AICP-EVIDENCE-TCK-1.10.0`. Frozen 1.2.0 and 1.3.0 releases are historical and
strong-ineligible. The 1.2.0 producer evaluator did not close every required-suite check
and its report evaluator did not enforce exact generated-artifact multiplicity. The
1.3.0 evaluator did not close generated messages over their exact owner payload schemas
or match ordinary PE/CAPNEG namespace semantics. The shared handler executes 10, 9, and 13 neutral producer
scenarios respectively and all required-suite transcripts exactly once. M65 expands the
consumer corpus from 25/16/28 to 26 mediated, 16 resumable, and 31 delegated cases (73
executions in total), derived from the exact required suites.

`targets.json` is schema-validated and resolves an exact target record to its catalog,
registered handler, and current release. Target kind, execution mode, claim type,
handler, mark, suites, operations, and release are load-bearing. The projection catalog is derived from
`conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json` and binds one deterministic
producer scenario plus all 12 consumer transcripts. `evidence_tck_releases.json` binds the
report schema, registry and registry schema, catalog, generated import-closure bundle,
owning suite, fixtures, neutral producer scenario, and canonicalization vector by digest.
M64 adds exactly two live binding targets:

```text
BIND-HTTP@0.1 -> AICP-BIND-HTTP-0.1
BIND-MCP@0.1  -> AICP-BIND-MCP-0.1
```

They use report 2.2, `full-binding`, `live_binding_v01`, and current Evidence TCK
1.10. A full run launches the same implementation build in both roles and repeats both
from clean state. HTTP uses real literal-loopback HTTP, SSE, WebSocket, and verified WSS traffic; MCP
uses JSON-RPC over child-process stdio. Optional SSE/WebSocket scenarios run exactly when
the role descriptor declares them. A WSS declaration additionally requires an executed
TLS/WebSocket interaction. The reference implementation declares and exercises all three.

## Live endpoint test-control contract

The runner starts every role with `shell=false` and a bounded process supervisor. It
retains only runtime-discovery variables that are present and needed across supported
platforms (`PATH`, `PATHEXT`, `SystemRoot`, `WINDIR`, `HOME`, `USERPROFILE`, `TMP`,
`TEMP`, `TMPDIR`, `LANG`, `LC_ALL`, and `VIRTUAL_ENV`), then adds the explicit test-control
environment below. Arbitrary `*_TOKEN`, `*_SECRET`, cloud, GitHub, and application
credentials are not inherited. This contract is harness
infrastructure and is not an AICP wire protocol:

```text
AICP_LIVE_RUN_ID
AICP_LIVE_BINDING_ID
AICP_LIVE_BINDING_VERSION
AICP_LIVE_ROLE
AICP_LIVE_READY_FILE
AICP_LIVE_SCENARIO_FILE       # client-under-test only
AICP_LIVE_ENDPOINT_URL        # HTTP client-under-test only
AICP_LIVE_WEBSOCKET_URL       # HTTP client-under-test or server WSS endpoint
AICP_LIVE_WSS_CHALLENGE_URL   # client-under-test negative-certificate endpoint
AICP_LIVE_TEST_BEARER         # HTTP only; never serialized into evidence
AICP_LIVE_TLS_CA_FILE         # per-run trust anchor
AICP_LIVE_TLS_CERT_FILE       # server-under-test only
AICP_LIVE_TLS_KEY_FILE        # server-under-test only; temporary
```

The child atomically writes an `aicp.live_endpoint_descriptor.v2` JSON object to the
ready-file. The descriptor binds the exact binding, role, implementation kind, ID,
version, digest, and declared optional features. An HTTP server additionally supplies a
literal-loopback `base_url` and, when WebSocket is declared, a `websocket_url`; WSS requires
that URL to use `wss://`. MCP declares `transport=stdio`. Descriptors using DNS names,
non-loopback addresses, a mismatched role or binding, unstable identity, or mixed
reference/external implementation kinds fail closed. HTTP redirects are not followed.

For a full-binding report the runner launches a server-under-test against the repository
client and a client-under-test against the repository reference server, then repeats both
roles from clean state. The two descriptors must name the same implementation build.
Phase deadlines, stdout/stderr, response bodies, events, frames, JSON-RPC lines, and
interaction counts are bounded; termination uses graceful shutdown followed by kill and
reap fallback. Ready files and scenario files are temporary and are removed after each
role. External processes inherit only the documented runtime-discovery allowlist plus
explicit `AICP_LIVE_*` controls. The child receives a schema-validated public scenario
projection, not runner-private fixture paths, suite check IDs, normative source paths, or
expected outcomes. Trace v4 contains strict, sanitized HTTP exchanges, parsed
SSE events, WebSocket handshakes/frames, and MCP JSON-RPC exchanges. Authorization is
represented only by presence and scheme; values, cookies, environment maps, bearer tokens,
TLS private keys, temporary key paths, and raw stderr are absent. Exact reflection of a
runner-created secret fails with `EVIDENCE_LIVE_SECRET_REFLECTION`.

For every declared client-role WSS execution, the harness exposes trusted and untrusted
endpoints but supplies only the trusted CA. Repository-owned listeners distinguish no TLS,
plaintext-on-TLS, pre-certificate abort, certificate rejection, and completed TLS before
recording HTTP Upgrade independently. Skipping the negative endpoint, probing it without
TLS, or disabling certificate verification fails. MCP client evidence omits optional
sendMessage cursors and proves that poll-1 first discloses the opaque continuation consumed
by the later poll-2. Release records 1.0.0 through 1.9.0 are byte-frozen. Release-specific registry
snapshots make `tck_release.registry_digest` immutable: 1.1.0 remains strong-eligible for
its exact projection reports, while 1.4.0 and 1.8.0 remain strong-eligible for their exact reports.
Releases 1.0.0, 1.2.0, 1.3.0, 1.5.0, 1.6.0, 1.7.0, and 1.9.0 are explicitly
strong-ineligible for their documented evidence defects. TCK 1.9 is ineligible because
its M65 semantics were split across two authorities and exceeded the normative 0.1 RFC
surface; this is an evidence/conformance defect, not a claimed security vulnerability.
Repository inspection finds zero real external submission
folders; examples, templates, reference reports, and test adapters are not adoption.
Regenerate and check with:

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

The capability target uses `describe`, `canonicalize_hash`, `validate_transcript`, and
`project_session_state`. Profile targets replace the final operation with
`generate_scenario`. Requests do not disclose canonical case IDs, fixture paths, or expected answers.
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

For profile targets, the adapter receives only the exact target, a schema-valid neutral
scenario, and runtime options. It returns an in-memory transcript. Independent runner code
checks every mandatory check ID derived from each scenario's required suites. That includes
Core contract/policy schemas and private exact sequences, CAPNEG registries and selection
constraints, enforcement sanctions, resume actions, signatures and key lifecycle, object
hashes, and delegated-identity lifecycle semantics. Unknown mandatory checks fail catalog,
producer, and mark eligibility. It never validates by
comparing generated bytes with a hidden golden transcript.

TCK 1.4 additionally derives one generated-message payload router from the union of the
Tier-1 scenarios' exact v0.1 suite metadata. Each of the 26 exercised message types resolves
to one `(schema path, JSON pointer, surface kind, surface ID, surface version)` identity;
identical duplicate identities coalesce and missing or conflicting identities fail target
validation. Thus Core lifecycle payloads are checked inside extension-focused scenarios,
and extension payloads such as `STATE_SYNC_RESPONSE` are checked inside Core recovery
scenarios. PE reason codes and CAPNEG privacy modes match the narrow ordinary-conformance
`vendor:`/`org:` predicate; Core policy categories and enforcement sanctions retain their
broader `x-...` and colon namespaces.

The standalone `report_evaluator.py` selects report 2.0, 2.1, or 2.2 through the declared TCK
release and validates it through a generic envelope
evaluator plus the registered target handler. It independently recomputes target/release
resolution, subject, registry/schema/catalog and import-closed runner provenance, case
coverage, producer validation and determinism, reviewed exact consumer observations, and
the eligible mark. Historical profile reports are evaluated against the exact case IDs
frozen in their selected release, so an expanded current corpus does not invalidate a
complete TCK 1.8 report. A raw
`compatibility_marks` string is never sufficient.

## Evidence boundaries

- Product-profile IUT report v1, its TCK releases, and the Base/Authenticated Base
  `full-profile` paths remain valid and unchanged.
- Report 2.0 remains valid for exact frozen projection-v1 releases. Report 2.1 adds discriminated
  projection/transcript artifacts and supports the three exact M63 product-profile targets.
  TCK 1.5 issued report 2.2 with trace v1 and is frozen/ineligible. TCK 1.6 issued trace v2
  and is frozen/ineligible because client response causality and client certificate verification
  were not independently challenged. TCK 1.7 issued trace v3 and is frozen/ineligible
  because MCP poll continuation could be disclosed by an earlier send response and its WSS
  challenge could be satisfied by a non-TLS probe. TCK 1.8 introduced report 2.2 trace v4
  with first-seen MCP continuation and normalized TLS rejection evidence and is now frozen
  historical/eligible. TCK 1.9 added the expanded M65 corpus but is frozen
  historical/ineligible due to the corrected semantic-authority defect. New TCK 1.10
  executions retain report 2.2, trace v4, six targets, and the 132/132 corpus while using
  only canonical normative semantics. The frozen historical projection report at
  `historical_reports/AICP-EVIDENCE-TCK-1.8.0-session-state-projection.json` was reproduced
  from commit `110c950ce069f323e084e02a13ce04b23f0c5fa3`; its normalized repository-byte digest is
  `sha256:8569bd2f403740a785ee6963f8aa8d6e507f5a11c0b8044c62cdf8021344b6d1`.
- A capability mark is not a product-profile mark, certification, endorsement, aggregate
  composition mark, or pairwise interoperability result.
- A profile report covers one exact profile. Component-suite marks do not become separate
  external product claims, and the three targets do not create a composition target.
- Digests establish consistency of the evaluated bytes; they do not establish
  organizational identity or authority.
- Reference, smoke, example, and test-only fake-adapter reports are not real external
  evidence. No real external Tier-1 profile submission is checked into this repository.
- Session-state projection v2 remains internal-only and is not registered here.
- Live binding marks prove one local external implementation against the frozen TCK, not
  two independent vendors. Real pairwise publication remains M66 and fail-closed.
- Reproducible live evidence is not remote hardware attestation: it proves an internally
  consistent, rerunnable transport transcript, not that arbitrary submitted JSON is
  cryptographically impossible to fabricate. AICP does not create a certification authority here.
- Client frame masking remains mandatory and repository-owned clients use fresh random mask
  keys. Trace v4 does not record external-client mask-key fingerprints, so cross-connection
  mask-key variation is a documented non-blocking residual limitation.

See `ADR_Generalized_External_Evidence.md` for the architectural decision and
`docs/interop/AICP_Compatibility_Claims_and_Evidence.md` for public claim rules.
