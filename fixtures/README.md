# Fixtures Policy

Fixtures and golden transcripts are verification artifacts.

Status note: Fixture/suite presence indicates deterministic test coverage, not automatic milestone graduation; roadmap status in `ROADMAP.md` remains authoritative for shipped vs incubating scope.

## Rules

- Do not hand-edit golden transcripts.
- Regenerate fixtures deterministically and document generation method.
- Keep fixture updates aligned with schema and conformance expectations.
- Treat fixtures as executable proof for interoperability checks.


Generation note: GT-04..GT-08 were generated deterministically using `reference/python/aicp_ref/hashing.py` for `message_hash` recomputation and serialized as JSONL in canonical field order from Python dict insertion order used by generation scripts.

Extension note: CAPNEG fixtures (`fixtures/extensions/capneg/CN-01*`, `CN-02*`, `CN-05*`, `CN-06*`, `CN-07*`, `CN-08*`, `CN-09*`, `CN-10*`) are generated deterministically using `reference/python/aicp_ref/hashing.py` for message hash computation, including profile-negotiation, rejection-semantics, channel-properties, and contract-binding pass/fail vectors (`scripts/generate_capneg_binding_fixtures.py`, `scripts/generate_capneg_channel_properties_fixtures.py`).
Extension note: OBJECT-RESYNC fixtures (`fixtures/extensions/object_resync/OR-01*`, `OR-02*`) are generated deterministically using `reference/python/aicp_ref/hashing.py` and `object_hash(...)` for payload object hash binding.
Extension note: POLICY-EVAL fixtures (`fixtures/extensions/policy_eval/PE-01*`, `PE-02*`) are generated deterministically using `reference/python/aicp_ref/hashing.py` and include a controlled negative transcript for unknown reason_code validation.
Extension note: ENFORCEMENT fixtures (`fixtures/extensions/enforcement/EF-01*`, `EF-02*`) are generated deterministically using `reference/python/aicp_ref/hashing.py` for message hash and prev-hash chain binding, including a controlled negative transcript for blocking-gate violations.
Extension note: OPS hardening fixtures (`fixtures/ops/OPS-01*`..`OPS-03*`) are generated deterministically via `reference/python/aicp_ref/hashing.py` (`message_hash_from_body`) with linear `prev_msg_hash` chaining to provide expected-fail evidence for probing, verdict-storm, and alert-verbosity checks.
Security note: signed-path fixtures (`fixtures/security/signed_paths/SP-01*`, `SP-02*`) are generated deterministically from templates using `scripts/generate_signed_transcript.py` with `fixtures/keys/TEST_private_keys.json`; `SP-02` is produced by deterministic single-signature corruption to exercise signature verification failure.

Extension note: DISPUTES fixtures (`fixtures/extensions/disputes/DS-01*`, `DS-02*`) are generated deterministically via `scripts/generate_disputes_fixtures.py` using `reference/python/aicp_ref/hashing.py` for message hash/chain computation, including registered and unknown-claim-type vectors.
Extension note: SECURITY-ALERT fixtures (`fixtures/extensions/security_alerts/SA-01*`, `SA-02*`) are generated deterministically via `scripts/generate_security_alerts_fixtures.py` using `reference/python/aicp_ref/hashing.py` for message hash/chain computation, including registered and unknown-category vectors.
M65 message-surface note: five existing orphan fixture paths (identity migration, disputes arbitration, delegation revoke, participant leave, and policy attestation) are now generator-reproducible positive suite cases. Six genuinely new positive fixture paths cover facilitation, valid key revoke, marketplace update/withdraw/decline, responsibility revoke, active-run cancel, and delegated-identity revoke. `scripts/generate_m65_message_surface_fixtures.py` owns the facilitation, participant, and policy outputs; the existing family generators own the other paths. No new negative fixture was added.
Extension note: DISPUTES fixtures include resolvable-evidence coverage (`DS-03`) generated deterministically via `scripts/generate_disputes_fixtures.py`.
Extension note: SECURITY-ALERT fixtures include resolvable-evidence coverage (`SA-03`) generated deterministically via `scripts/generate_security_alerts_fixtures.py`.

Extension note: CONFIDENTIALITY fixtures (`fixtures/extensions/confidentiality/CF-01*`..`CF-08*`) are generated deterministically via `scripts/generate_confidentiality_fixtures.py` using `reference/python/aicp_ref/hashing.py` for CAPNEG negotiation hash binding and message hash/chain computation.

Extension note: REDACTION fixtures (`fixtures/extensions/redaction/RD-01*`..`RD-09*`) are generated deterministically via `scripts/generate_redaction_fixtures.py` using `reference/python/aicp_ref/hashing.py` for message hash/chain computation, including retention policy-category and delete-semantics negative vectors.

Extension note: HUMAN-APPROVAL fixtures (`fixtures/extensions/human_approval/HA-01*`..`HA-08*`) are generated deterministically via `scripts/generate_human_approval_fixtures.py` using `reference/python/aicp_ref/hashing.py` for message hash/chain computation, including signer mismatch, expiry, target-reuse, and intervention-link expected-fail vectors.
Extension note: IAM-BRIDGE fixtures (`fixtures/extensions/iam_bridge/IB-01*`..`IB-09*`) are generated deterministically via `scripts/generate_iam_bridge_fixtures.py` using `reference/python/aicp_ref/hashing.py` (`message_hash_from_body`) and `object_hash(...)` for claims snapshot and subject-binding linkage.
