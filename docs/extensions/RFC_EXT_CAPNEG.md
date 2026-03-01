10. RFC: EXT-CAPNEG — Capability and profile negotiation (Registered Extension)
EXT-CAPNEG defines a minimal, verifiable handshake so parties can agree on compatible profiles before executing side effects. It standardizes: (a) capability declarations; (b) a proposed profile selection; (c) an accepted negotiation_result that can be embedded into the Context Contract for auditability.

EXT-CAPNEG is transport-agnostic. It does not require a centralized service. Negotiation messages MAY be observed/enforced by third parties.

10.1 Message types (normative)
All EXT-CAPNEG messages MUST use the Core Envelope. They MUST NOT change the contract state directly unless the contract explicitly requires a negotiated profile for activation.

• CAPABILITIES_DECLARE — publish capabilities of a party (crypto profiles, AICP product profile support/requirements, privacy modes, supported extensions, limits).
• CAPABILITIES_PROPOSE — propose a concrete compatible selection and provide negotiation_result.
• CAPABILITIES_ACCEPT — accept a negotiation_result.
• CAPABILITIES_REJECT — reject with a machine-readable reason and (optionally) alternative constraints.

10.2 CapabilityDeclaration object (normative minimum)
CAPABILITIES_DECLARE payload MUST include:

• capabilities_id (MUST): unique identifier for this declaration.
• party_id (MUST): sender identifier (same as Envelope.sender).
• supported_profiles (MUST): list of crypto/profile IDs (e.g., AICP-JCS-1, AICP-HASH-SHA256-1, AICP-SIG-ED25519-1, AICP-MSGCHAIN-1).
• supported_privacy_modes (MUST): list of privacy_mode IDs (registered).
• supported_extensions (SHOULD): list of extension IDs supported by the party.
• supported_policy_categories (SHOULD): list of policy category IDs supported for evaluation/enforcement.
• limits (SHOULD): max_message_bytes, max_object_bytes, max_objects_per_request, max_clock_skew_s.
• bindings (MAY): supported transport bindings (e.g., EXT-BIND-MCP, EXT-BIND-HTTP).
• languages (MAY): supported natural languages for human-facing text.

AICP product profile negotiation additions (backward compatible):

• supported_aicp_profiles (MAY): array of `{profile_id, profile_version}` values the party supports.
• required_aicp_profiles (MAY): array of `{profile_id, profile_version}` values acceptable as required minimum set (exact-match membership, not partial-order ranking).

A party MAY issue multiple declarations over time. New declarations SHOULD reference supersedes_capabilities_id for auditability.

10.3 negotiation_result object (normative)
CAPABILITIES_PROPOSE MUST carry negotiation_result. negotiation_result is a hashable object (extension-defined) that MUST include:

• negotiation_id (MUST): stable identifier for the negotiation attempt.
• session_id and contract_id (MUST): bind the result to a specific session/contract.
• participants (MUST): list of party_ids included in the agreement.
• selected.crypto_profile (MUST): selected set of crypto/profile IDs.
• selected.privacy_mode (MUST): selected privacy_mode.
• selected.aicp_profile (MAY): selected AICP product profile as `{profile_id, profile_version}`.
• selected.required_extensions (MAY): extensions required for this session/contract.
• selected.required_policy_categories (MAY): policy categories that MUST be enforceable.
• selected.limits (MAY): negotiated limits.
• transcript_binding (SHOULD): hash binding to the negotiation transcript (e.g., message_hash of the last negotiation message).

A negotiation_result MUST be signed by the required parties (either as signatures on the CAPABILITIES_ACCEPT message, or as an object-level signature referenced by it).

AICP product profiles (AICP-BASE, AICP-MEDIATED-BLOCKING, …) are negotiated via `selected.aicp_profile`. Crypto profiles remain negotiated via `selected.crypto_profile`.

10.4 Validation rules (normative)

• Receivers MUST reject proposals that select a profile not included in their most recent CAPABILITIES_DECLARE.
• Receivers MUST reject downgrade attempts below their local minimum acceptable security baseline (implementation-defined), and SHOULD explain via reason_code.
• If `selected.aicp_profile` is present, receivers MUST verify it is registered and acceptable against declared `supported_aicp_profiles`/`required_aicp_profiles` for negotiation participants.
• If the Context Contract requires a negotiated profile for activation, CONTRACT_ACCEPT MUST reference an accepted negotiation_result (by hash or embedded copy).
• negotiation_result_hash MUST be computed as `object_hash("capneg.negotiation_result", negotiation_result)`.
• If a contract requires negotiated profile activation, `CONTRACT_PROPOSE.payload.contract` MUST include `contract.ext.capneg` with:
  - `negotiation_result_hash` (MUST), matching the accepted negotiation_result hash,
  - `selected` (MUST, copy of `negotiation_result.selected`),
  - `negotiation_id` (MAY),
  - `transcript_binding` (MAY).

10.5 Conformance suite (CN-*) (normative minimum)

• CN-01: Compatible declarations -> propose -> accept -> negotiation_result identical across implementations.
• CN-02: Downgrade attempt (proposed weaker crypto_profile) -> reject with reason_code=DOWNGRADE_NOT_ALLOWED.
• CN-03: Missing required extension -> reject with reason_code=REQUIRED_EXTENSION_UNSUPPORTED.
• CN-04: Capabilities spoof (proposal selects unsupported id) -> reject, no state change.
• CN-05: Product profile agreement -> selected.aicp_profile accepted and consistent with participant declarations.
• CN-06: Product profile downgrade attempt -> conformance detects profile negotiation violation deterministically.

10.6 Registry requirements (normative intent)

• privacy_mode IDs and CAPNEG reason_code IDs MUST be registered.
• Negotiated AICP product profiles MUST be registered in `registry/aicp_profiles.json`.
• If negotiation_result introduces a new hash domain, it MUST be registered (Section 8, Object Hash Domains).

Security note: downgrade/inconsistent negotiation is a security concern; conformance checks `CN-DOWNGRADE-01` and `CN-AICP-PROFILE-NEGOTIATION-01` in `conformance/extensions/CN_CAPNEG_0.1.json` provide executable detection coverage.
