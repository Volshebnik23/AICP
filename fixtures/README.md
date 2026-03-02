# Fixtures Policy

Fixtures and golden transcripts are verification artifacts.

## Rules

- Do not hand-edit golden transcripts.
- Regenerate fixtures deterministically and document generation method.
- Keep fixture updates aligned with schema and conformance expectations.
- Treat fixtures as executable proof for interoperability checks.


Generation note: GT-04..GT-08 were generated deterministically using `reference/python/aicp_ref/hashing.py` for `message_hash` recomputation and serialized as JSONL in canonical field order from Python dict insertion order used by generation scripts.

Extension note: CAPNEG fixtures (`fixtures/extensions/capneg/CN-01*`, `CN-02*`, `CN-05*`, `CN-06*`, `CN-07*`, `CN-08*`) are generated deterministically using `reference/python/aicp_ref/hashing.py` for message hash computation, including profile-negotiation and contract binding pass/fail vectors (`scripts/generate_capneg_binding_fixtures.py`).
Extension note: OBJECT-RESYNC fixtures (`fixtures/extensions/object_resync/OR-01*`, `OR-02*`) are generated deterministically using `reference/python/aicp_ref/hashing.py` and `object_hash(...)` for payload object hash binding.
Extension note: POLICY-EVAL fixtures (`fixtures/extensions/policy_eval/PE-01*`, `PE-02*`) are generated deterministically using `reference/python/aicp_ref/hashing.py` and include a controlled negative transcript for unknown reason_code validation.
Extension note: ENFORCEMENT fixtures (`fixtures/extensions/enforcement/EF-01*`, `EF-02*`) are generated deterministically using `reference/python/aicp_ref/hashing.py` for message hash and prev-hash chain binding, including a controlled negative transcript for blocking-gate violations.
Extension note: OPS hardening fixtures (`fixtures/ops/OPS-01*`..`OPS-03*`) are generated deterministically via `reference/python/aicp_ref/hashing.py` (`message_hash_from_body`) with linear `prev_msg_hash` chaining to provide expected-fail evidence for probing, verdict-storm, and alert-verbosity checks.
Security note: signed-path fixtures (`fixtures/security/signed_paths/SP-01*`, `SP-02*`) are generated deterministically from templates using `scripts/generate_signed_transcript.py` with `fixtures/keys/TEST_private_keys.json`; `SP-02` is produced by deterministic single-signature corruption to exercise signature verification failure.

Extension note: DISPUTES fixtures (`fixtures/extensions/disputes/DS-01*`, `DS-02*`) are generated deterministically via `scripts/generate_disputes_fixtures.py` using `reference/python/aicp_ref/hashing.py` for message hash/chain computation, including registered and unknown-claim-type vectors.
Extension note: SECURITY-ALERT fixtures (`fixtures/extensions/security_alerts/SA-01*`, `SA-02*`) are generated deterministically via `scripts/generate_security_alerts_fixtures.py` using `reference/python/aicp_ref/hashing.py` for message hash/chain computation, including registered and unknown-category vectors.
Extension note: POLICY-EVAL fixture `PE-05_policy_decision_attest_presence.jsonl` was added deterministically with `reference/python/aicp_ref/hashing.py` to provide fixture-level coverage for `POLICY_DECISION_ATTEST` required by profile coverage gating.
Extension note: DISPUTES fixtures include resolvable-evidence coverage (`DS-03`) generated deterministically via `scripts/generate_disputes_fixtures.py`.
Extension note: SECURITY-ALERT fixtures include resolvable-evidence coverage (`SA-03`) generated deterministically via `scripts/generate_security_alerts_fixtures.py`.
