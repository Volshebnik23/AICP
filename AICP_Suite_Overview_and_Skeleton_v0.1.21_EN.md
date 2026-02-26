AICP — AI Interconnector Protocol

Context-Accurate and Safe Agent-to-Agent Interaction
Suite Overview and v0.1 Specification Skeleton (RFC frame + Core v0.1 + Registered Extensions)

Version: 0.1.21 (English master)
Date: 2026-02-25
Status: Draft
 
Change log
 
Contents
1.	0. Protocol positioning (AI-OSI)
2.	0.2 Relationship to MCP and other tool interfaces
3.	1. RFC frame: Problem, Goals, Non-Goals, Requirements, Extension points
4.	2. Glossary
5.	3. Roles and state model (Core v0.1)
6.	4. Message model and Core message types (Core v0.1)
7.	5. Policy core (Core v0.1)
8.	6. Attestations and crypto minimum (Core v0.1)
9.	7. Conformance and testability
10.	8. RFC: Registry and Change Control
11.	9. RFC: Error model and recovery
12.	10. RFC: EXT-CAPNEG (capability and profile negotiation)
13.	11. RFC: Transport bindings (EXT-BIND-*)
14.	12. RFC: EXT-POLICY-EVAL (policy evaluation semantics)
15.	13. RFC: EXT-OBJECT-RESYNC (object retrieval and state resync)
16.	14. RFC: EXT-IDENTITY-LC (identity lifecycle)
17.	15. RFC: Applied extensions (workflow, delegation, disputes, security alerts)
18.	16. RFC: Governance / IPR / Stewardship
19.	17. Reference implementations and conformance harness
20.	18. Interop event and external security review
21.	Roadmap and current status
 
0. Protocol positioning (AI-OSI)
The industry uses many “protocols” and interfaces for AI systems, but they address different layers: transport, cryptography, message framing, tool access, or domain application logic. To avoid confusion, this document uses a practical layered model (loosely analogous to OSI) to specify what level AICP targets.
0.1 A practical layered model for agent interaction (informative)
Layer	What it solves	Examples	Typical threats / failures
L0 Transport	Byte/message delivery	TCP/WebSocket/WebRTC, gRPC	Loss/latency, NAT, DoS
L1 Session & crypto	Identities, keys, encryption, signatures	TLS/mTLS, JWT, Ed25519	Key substitution, replay, key compromise
L2 Message framing	Serialization, queues, delivery semantics	JSON/CBOR, Redis Streams, NATS/Kafka	Reordering, duplicates, split-brain queues
L3 Content contract	Shared goals, roles, boundaries, versioned context	AICP Core	Context drift, version conflicts, forks
L4 Policies & attestations	Machine-checkable policies + evidence	Policy-as-code, attestations, audit chain	Policy bypass, false reporting, gray zones
L5 Domain apps	Vertical product logic	Dating, IDE coding, support	Goal drift, user harm, liability
Positioning: AICP primarily targets L3 (content contract) and partially L4 (policy and attestation formats). AICP is intentionally transport-agnostic (L0-L2) and domain-agnostic (L5).
0.2 Relationship to MCP and other tool interfaces
Core idea: MCP and similar interfaces standardize how an AI application connects to tools and context sources (tool/data plane), but they do not define a multi-agent “meaning contract”: roles, responsibilities, boundaries, authority/consent, versioned context evolution, and verifiable policy compliance. AICP fills this gap on the agent-contract plane. Enforcement is a separate plane: the protocol MUST remain useful without any single centralized enforcer and MUST allow third-party, local, federated, or self-enforcement.
0.2.1 MCP summary relevant for integration (informative)
MCP (Model Context Protocol) is commonly used to connect an AI host to external integrations that expose Tools, Resources, and Prompts. AICP can use MCP as the tool/data plane, while AICP defines cross-agent contracts.
0.2.2 Responsibility split: MCP vs AICP (normative intent)
MCP scope: tool invocation and context retrieval (Tools/Resources/Prompts).
AICP scope: multi-agent contract—goals, roles, authority/consent, boundaries, policy attestations, context versioning, conflict detection and resolution, and auditability.
0.2.3 Recommended integration: MCP under AICP contract control (informative)
In the practical architecture, MCP stays as the mechanism to call tools and read resources, while the AICP contract constrains what the agent is allowed to do through MCP. When an agent performs a tool call, it SHOULD emit ATTEST_ACTION binding the action to the contract version and to tool identifiers (e.g., tool name + args hash). MCP Host is a natural runtime enforcement point: it can block tool calls without required consent/authority and require attestations after side effects.
0.2.4 Optional integration: a transport binding over MCP (EXT-BIND-MCP)
AICP MAY be carried over MCP by using an MCP “aicp-bridge” server that provides tools/resources to send and fetch AICP envelopes and state (see Section 11). If the selected privacy_mode requires no observer on content, the AICP payload MUST be protected (e.g., via an encryption profile) before passing through a remote bridge.
0.2.5 Consent, authority, and audit when using tool interfaces
AICP policy categories separate: Agent-Authority (what the agent can do), User-Consent (what the user approves), User-Consent-Auth (how consent is verified via a trusted issuer), and Scope (context boundaries). When using MCP or other tool-calling systems, these policies can be enforced in the host runtime and evidenced via attestations and audit chains.
0.2.6 Non-MCP tool interfaces (informative)
AICP is compatible with any tool-calling interface (function calling, tool use, custom APIs). Bindings for specific interfaces are described as transport bindings (Section 11) rather than changing Core semantics.
 
1. RFC frame v0.1: Problem, Goals, Non-Goals, Requirements, Extension points
1.1 Problem Statement
AI agents and agent providers are multiplying while remaining fragmented. In practice this causes context drift, incompatible implementations, unclear responsibility boundaries, and weak verifiability of consent and authority during agent-to-agent interaction.

An open, transport-independent, content-layer protocol is needed so that 2+ agents can agree on a versioned Context Contract (goal, roles, policies), evolve it via Amendments, attest actions, and support auditing and third-party enforcement. The protocol MUST assume monitoring/enforcement exists, but MUST NOT require a single central enforcer or mandatory MITM access to content.
1.2 Goals
•	Provide a minimal, implementable, and testable protocol for agreeing on a shared, versioned context contract between 2+ agents.
•	Enable verifiable responsibility boundaries via machine-checkable policies and signed attestations.
•	Remain transport-agnostic and domain-agnostic.
•	Enable third-party enforcement and observation without requiring a single platform or mandatory content MITM.
1.3 Non-Goals
•	Philosophical “ethics” as a category (beyond machine-checkable policies and profiles).
•	Mandating a single enforcement provider or platform.
•	Standardizing UI/UX of domain applications.
•	Standardizing confidential computing / TEE-based enforcement in v0.1 (may be added as profiles later).
•	Introducing token economics or payments as part of Core.
1.4 Requirements (Core v0.1)
•	AICP MUST be transport-independent: it defines message structures and validation rules, not a specific transport.
•	AICP MUST define Session and Context Contract, including contract_id, session_id, versioning, branching (branch_id), and conflict resolution.
•	AICP MUST define a minimal set of message types for contract propose/accept, amendment propose/accept, action attestation, policy violation reporting, conflict resolution, and session close.
•	Messages that change the contract state MUST reference a specific contract_ref and MUST be signed under the contract signature_policy.
•	The Message Envelope MUST support extensibility via registered extensions without breaking Core schemas.
•	Core policies MUST include at minimum: Agent-Authority, User-Consent, User-Consent-Auth (external issuer reference), Scope, Boundaries, Tool Access, PII Handling, Auditability.
•	The protocol MUST allow a third-party Observer/Enforcer to verify compliance using messages, artifact references, and attestations, without requiring mandatory content MITM.
•	The protocol SHOULD support message hash chaining and correlation (in_reply_to / related_to) for auditability and disputes.
•	The protocol SHOULD define a standard ERROR format with machine-readable codes and recovery guidance (see Section 9).
1.5 Extension points and registry
v0.1 defines an extension mechanism: (a) namespaced message_type identifiers; (b) envelope.extensions (list of extension IDs) and/or envelope.ext (map) for extension-defined fields; (c) a public registry for extensions, profiles, and codes (see Section 8).
AICP intentionally separates (1) what is exchanged and how it can be verified (contracts, versioning, hashes, signatures, references) from (2) who enforces it and how (platform enforcers, policy engines, auditors). Implementations MAY use existing best practices and tools for enforcement as long as they do not contradict Core semantics.
1.6 Core v0.1 vs Registered Extensions (vision)
To keep the protocol implementable, AICP is split into a small Core v0.1 and a registry of extensions. The list below is informative and captures the intended evolution so that Core decisions do not block the roadmap.
•	EXT-CAPNEG — Capability and profile negotiation.
•	EXT-ARTIFACTS — Standard artifact references with hash/provenance.
•	EXT-WORKFLOW-SYNC — Workflow synchronization and enforceable step attestations.
•	EXT-DELEGATION — Hierarchical, purpose-oriented delegation with challenge/claim.
•	EXT-DISPUTES — Challenges, breach claims, optional arbitration hooks.
•	EXT-SECURITY-ALERT — Standard security events and escalation messages.
•	EXT-TRACING — Trace and observability fields (e.g., OpenTelemetry compatibility).
•	EXT-IDENTITY-LC — Identity lifecycle: rotation, revocation, migration, external attestations.
•	EXT-QOS — Budgets, deadlines, backpressure.
 
2. Glossary (draft)
Agent — An AI system capable of exchanging protocol messages and acting on behalf of a user or service.
Party — A protocol participant (agent/service) with an identity key set used for signing and verification.
Session — A protocol interaction among 2+ parties bound to a single Context Contract. Identified by session_id.
Context Contract (Contract) — A versioned, machine-readable document defining goal, roles, policies, and boundaries for the session. Identified by contract_id and evolved by Amendments.
contract_id — A stable identifier of the contract within a session.
branch_id — A branch identifier for parallel contract evolution. Default is 'main'.
head_version — The current contract version for a branch, formatted as "vN" (e.g., "v1").
contract_ref — A reference that binds a message to a specific branch and version(s). Core v0.1 uses: {branch_id (default "main"), base_version ("vN"), head_version ("vN"), contract_hash (optional)}.
Message — An atomic unit of exchange: an Envelope plus a message-type-specific Payload.
Message Envelope (Envelope) — Protocol metadata enabling verification, correlation, and binding to a specific contract version.
Amendment — A signed, versioned change to the contract (diff/patch + rationale + base_version).
Attestation — A signed statement binding an action/result to a specific contract version and policy context.
Observer — An optional passive party receiving replicated messages/attestations for monitoring and audit, without changing the contract.
Enforcer — An optional entity that monitors/verifies/limits protocol execution and can emit violations or decisions. It can be third-party, local sidecar, federated, or self-enforcement.
Agent-Authority — A machine-readable set of permissions granted to an agent (e.g., categories of actions).
User-Consent — A user-approved consent granting authority to an agent within a given scope and expiry.
User-Consent-Auth — A trusted issuer mechanism producing verifiable consent artifacts linking User - Agent - Authority - Scope - Expiry - Issuer.
Consent Artifact — A verifiable proof of consent (e.g., JWT/OAuth token/VC), carried inline or by reference.
Scope — Machine-readable boundaries of allowed actions/disclosures/obligations for a session/contract.
Workflow — A machine-readable plan/process (e.g., graph of steps) synchronized as part of context; steps can be attested and enforced by third parties.
Workflow Artifact — An artifact (by reference) that describes a workflow (JSON/YAML), including step IDs and expected outputs.
Delegation — A formal transfer of a subset of authority to a delegatee within scope, time, and purpose; can be hierarchical.
Delegation purpose — An explicit expected outcome; the delegator retains result control and can challenge/claim breach.
Challenge — A message disputing a result/fact/attestation (e.g., suspected distortion or policy breach).
Claim (breach) — A message asserting improper execution of delegated work or contract obligations.
Security Alert — A standardized security event (e.g., suspected malicious result distortion, key substitution, replay/forgery) bound to session evidence.
Canonicalization — A deterministic procedure mapping an object to a unique byte representation for hashing/signing.
object_hash — A domain-separated hash identifier, e.g., sha256:BASE64URL.
message_hash — An object_hash in the 'message' domain used for hash chaining.
kid — Key ID for selecting a specific public key within a party identity.
Signature — A cryptographic proof that a party key signed an object_hash under a specified algorithm.
Privacy mode — A negotiated mode defining who may observe content (cleartext moderated, E2EE local enforcement, confidential enforcement, etc.).
 
3. Roles and state model (Core v0.1)
Core v0.1 defines a replicated state machine (RSM) model: session state and the current contract head are derived from applying valid protocol messages to local state. Independent implementations MUST converge on the same state given the same set of valid messages (subject to conflict handling defined here).
3.1 Replicated state machine: derived state and invariants (normative)
•	Derived state includes:
•	session_state (lifecycle state)
•	branch_heads (branch_id -> head_version)
•	active_head_version (the chosen canonical head when not in Conflict)
•	pending_amendments (amendments proposed but not yet quorum-accepted)
•	conflict_sets (detected conflicts awaiting RESOLVE_CONFLICT)
•	Core invariants:
•	Any message that changes the contract state (CONTRACT_ACCEPT, AMENDMENT_ACCEPT, RESOLVE_CONFLICT, CLOSE_SESSION) MUST reference a specific contract_ref and MUST satisfy signature_policy.
•	Version numbering MUST be monotonic within a branch.
•	Distinct contract states MUST have distinct contract_hash values.
3.2 Roles (normative)
Core roles are logical (not necessarily separate processes):
•	Initiator: Creates session_id and proposes Contract v1 via CONTRACT_PROPOSE.
•	Counterparty (1..N): Accepts/rejects contract and amendments; emits attestations.
•	Observer (optional): Receives replicated messages for audit/analytics; MUST NOT modify the contract.
•	Enforcer (optional): Evaluates policy compliance and can emit POLICY_VIOLATION and/or policy decisions (via extensions). The protocol does not require the enforcer to be a content MITM.
3.3 Session lifecycle states (normative)
session_state is derived. Implementations MAY add local substates, but MUST preserve the semantics below.
State	Meaning	Entry condition	Typical exit / transition
Draft (local)	Initiator prepared a draft before first proposal.	Before CONTRACT_PROPOSE is sent.	CONTRACT_PROPOSE -> Proposed
Proposed	Contract proposal delivered; acceptance ongoing.	Valid CONTRACT_PROPOSE received.	Quorum CONTRACT_ACCEPT -> Active[v1]; or close/reject by policy
Active[vN]	A canonical contract head is active.	Quorum for the current head is achieved.	AMENDMENT_PROPOSE -> Amendment-in-flight; concurrent accepts -> Conflict; CLOSE_SESSION -> Closing/Closed
Amendment-in-flight	There are proposed amendments pending acceptance.	AMENDMENT_PROPOSE received referencing active head.	Quorum AMENDMENT_ACCEPT -> Active[vN+1]; concurrent accepts -> Conflict; reject/timeout by policy
Conflict	Two or more incompatible accepted heads exist.	Any conflict class in 3.5 detected.	RESOLVE_CONFLICT -> Active; CLOSE_SESSION may terminate if policy allows
Closing (optional)	Close requested; waiting for confirmations if required.	CLOSE_SESSION received.	Quorum close confirmations -> Closed
Closed	Session is terminated; contract immutable.	Close completed per policy.	Terminal
Non-contract-changing messages (e.g., ATTEST_ACTION, POLICY_VIOLATION) MAY be emitted in any state unless forbidden by policy. During Conflict, any attestation MUST explicitly reference the branch/version it applies to.
3.4 Versions and branches (normative)
Core v0.1 uses branch_id (default 'main') and monotonic version strings formatted as 'vN' per branch. Implementations MAY additionally compute contract_hash over the canonical contract representation for auditability. Core messages reference versions via contract_ref.{base_version, head_version} (and MAY include contract_hash). Amendments MUST specify base_version (the head_version they apply to).
3.5 Conflict classes and detection (normative minimum)
•	An implementation MUST detect at minimum:
•	Concurrent-accept: two different AMENDMENT_ACCEPT create different children from the same base_version.
•	Divergent-quorum: different signer subsets reach quorum for different heads (split-brain by signatures).
•	Non-head-accept: an AMENDMENT_ACCEPT references a known base_version that is not the current active head (fork).
•	Unknown-base: an amendment/accept references an unknown base_version (buffer or reject; MUST NOT silently change active head).
•	Incompatible-close: CLOSE_SESSION references a final head that does not match the known canonical head.
3.6 Conflict resolution (RESOLVE_CONFLICT) (normative)
Conflict resolution MUST be performed via RESOLVE_CONFLICT, signed under signature_policy quorum and referencing the full conflict_set. Two resolution types are supported: choose and merge.
•	choose: Select one head_version as canonical and mark others superseded. Implementations MUST stop accepting new amendments on superseded refs if policy requires.
•	merge: Create a merge amendment referencing all merge_parents and producing a new head_version on the target branch.
During Conflict, implementations SHOULD enter conservative execution (freeze side effects) unless policy explicitly allows otherwise. If side effects are allowed, attestations MUST carry a conflict_context flag (extension-defined) and a precise head_version.
3.7 Signature policy and quorums (normative)
Contract.signature_policy defines required signers and thresholds for: contract acceptance, amendment acceptance, conflict resolution, and close. If absent, the safe default is: all parties that accepted v1 are required for future accepts/resolve/close.
3.8 Minimum implementation requirements (Core v0.1)
•	A Core v0.1 implementation MUST:
•	Validate signatures and contract_ref for contract-changing messages.
•	Track branch heads and detect conflict classes in 3.5.
•	Implement RESOLVE_CONFLICT with choose and merge.
•	Ensure ATTEST_ACTION binds to a specific head_version (branch/version).
 
4. Message model and Core message types (Core v0.1)
4.0 Message and Envelope (normative)
An AICP Message is transport-independent and consists of a Message Envelope plus a message-type-specific Payload. The protocol defines validation rules; transports are defined by bindings (Section 11).
Envelope fields (Core v0.1):
Field	Level	Meaning
message_type	MUST	Core or registered extension message type.
message_id	MUST	Unique identifier (UUID/ULID). Used for idempotency.
session_id	MUST	Session identifier.
contract_id	MUST	Contract identifier within the session.
contract_ref	MUST (if applicable)	Version reference for contract-scoped messages: {branch_id, base_version, head_version, contract_hash?}.
sender	MUST	Sender party/agent identifier.
timestamp	MUST	Creation time (RFC3339) and/or monotonic counter.
signatures	SHOULD / per policy	Array of Signature objects (Section 6). REQUIRED by policy for state-changing messages.
prev_msg_hash	SHOULD	Previous message hash for hash chaining (Section 6).
in_reply_to	SHOULD	Correlation to a prior message.
related_to	SHOULD	Correlation to a related object (amendment_id, delegation_id, workflow_step_id).
extensions	SHOULD	List of extension IDs used by this message.
ext	SHOULD	Map of extension-defined fields (namespaced).
message_hash	SHOULD	Precomputed message_hash if supported (must verify).
Legacy field signature MAY be accepted as syntactic sugar for signatures[0], but new implementations SHOULD use signatures[].
4.1 CONTRACT_PROPOSE — Propose a contract
Purpose: Initiate a session and propose Contract v1 (or a new branch proposal).
Trigger / conditions: Sent by Initiator when moving from Draft to Proposed.
Payload (minimum fields):
•	contract (MUST): full Context Contract object.
•	initial_version (MUST): typically v1.
•	signature_policy (SHOULD): signer/quorum policy if not embedded in contract.
•	capabilities_declared (MAY): if EXT-CAPNEG not used.
•	profile_refs (MAY): references to policy/value profiles.
Notes: If a party needs changes, it SHOULD propose a new contract version/branch rather than relying on informal negotiation.
4.2 CONTRACT_ACCEPT — Accept a contract
Purpose: Accept a specific proposed contract version and commit to act under it.
Trigger / conditions: Sent by counterparties in response to CONTRACT_PROPOSE. Quorum activates Active[v1].
Payload (minimum fields):
•	accepted_contract_hash or accepted_head_ref (MUST): exact version being accepted.
•	consent_artifacts (MAY): references to user consent proofs if required.
•	capabilities_declared (MAY): updated capabilities declaration.
4.3 AMENDMENT_PROPOSE — Propose an amendment
Purpose: Propose a contract change (diff/patch) on top of a base_version.
Trigger / conditions: Sent in Active[vN] by a party authorized to amend. Creates Amendment-in-flight.
Payload (minimum fields):
•	base_version (MUST): head_version being amended.
•	amendment_id (MUST): unique identifier.
•	diff/patch (MUST): machine-readable change.
•	rationale (SHOULD): reason/intent.
•	proposed_version (SHOULD): next version number or deterministic rule.
4.4 AMENDMENT_ACCEPT — Accept an amendment
Purpose: Accept a proposed amendment and move the branch head forward.
Trigger / conditions: Sent by required signers. Quorum advances to Active[vN+1] or creates Conflict if concurrent.
Payload (minimum fields):
•	amendment_id (MUST): reference to proposal.
•	new_head_version or resulting_contract_hash (MUST): exact resulting contract state.
•	acknowledgements (MAY): migration/upgrade acknowledgments.
Notes: Accept MUST be unambiguous about the resulting contract_hash to prevent divergent interpretations.
4.5 ATTEST_ACTION — Attest an action
Purpose: Bind an action and its result to a specific contract head and policy context for auditability and responsibility.
Trigger / conditions: Emitted after performing an action (message emission, tool call, workflow step, etc.).
Payload (minimum fields):
•	action_id (MUST)
•	action_type (MUST): e.g., tool_call, plan_step, message_emit.
•	contract_head_version (MUST): the head_version under which the action was taken.
•	action_summary and/or result_summary (SHOULD)
•	evidence_refs (MAY): artifact refs, tool call logs, outputs.
4.6 POLICY_VIOLATION — Report a policy violation
Purpose: Report suspected or confirmed policy breach (boundaries, tools, PII, audit).
Trigger / conditions: May be emitted by any party or an Enforcer. Does not change contract state by default.
Payload (minimum fields):
•	policy_id or policy_category (MUST)
•	severity (MUST): low/medium/high/critical.
•	violated_by (MUST): references to actor/message/action.
•	evidence_refs (SHOULD)
•	recommended_action (MAY): block/escalate/amend/close.
4.7 RESOLVE_CONFLICT — Resolve a conflict set
Purpose: Resolve a detected conflict via choose or merge, restoring a canonical head.
Trigger / conditions: Emitted when state is Conflict; requires quorum signatures.
Payload (minimum fields):
•	conflict_set (MUST): list of conflicting head_version values.
•	resolution_type (MUST): choose or merge.
•	chosen_head_version (MUST if choose)
•	superseded_refs (SHOULD if choose)
•	merge_parents (MUST if merge)
•	merge_amendment (MUST if merge)
•	signatures_quorum (MUST): reference to signature_policy or explicit quorum rule.
4.8 CLOSE_SESSION — Close the session
Purpose: Terminate the session and freeze the contract.
Trigger / conditions: Sent by a party authorized to close; may require confirmations per policy.
Payload (minimum fields):
•	final_head_version (MUST): final canonical head.
•	close_reason (SHOULD)
•	retention/audit_hints (MAY)
•	final_attestations (MAY)
4.9 Registered Extensions (informative index)
All non-Core message types MUST be registered (Section 8) and specified in extension RFCs. Core implementations MAY ignore unknown extensions unless required by the contract/negotiation_result.
 
5. Policy core (Core v0.1)
Core v0.1 standardizes policy categories and their intent. Policies MUST be machine-checkable wherever feasible. Where LLM classification is used, the protocol MUST treat such checks as non-deterministic and require explicit evidence/logging if used for enforcement.
5.1 Core policy categories (normative list)
•	Agent-Authority: What the agent is allowed to do (capabilities/permissions), potentially structured by action categories.
•	User-Consent: User-approved consent granting authority within scope and time bounds.
•	User-Consent-Auth: Reference to a trusted consent issuer/provider that binds User - Agent - Authority - Scope - Expiry.
•	Scope: Context boundaries: allowed actions/disclosures/obligations in this session.
•	Boundaries: Hard prohibitions and escalation rules (stop conditions).
•	Tool Access: Allow/deny lists and conditions for tool/integration calls (including through MCP).
•	PII Handling: Rules for collecting, transmitting, masking, storing, and retaining personal data.
•	Auditability: Requirements for signatures, contract refs, hash chain, and minimal decision logging.
5.2 Extension policy categories (informative)
Extensions MAY introduce additional policy categories such as Workflow Governance, Delegation Governance, Dispute Handling, Security Event Reporting, Budgets/QoS, and Identity Lifecycle policies. Such categories MUST be registered and specified with deterministic schemas where possible.
 
6. Attestations and crypto minimum (Core v0.1)
This section defines the minimum cryptographic primitives required for verifiable auditability independent of transport and platform. Transports MAY provide TLS/mTLS, but AICP signatures and hashes are content-layer proofs and remain valid even when transcripts are exported.
6.1 Core crypto profiles (normative)
•	AICP-JCS-1: JSON canonicalization per RFC 8785 (JCS).
•	AICP-HASH-SHA256-1: Domain-separated SHA-256 object hashing.
•	AICP-SIG-ED25519-1: Ed25519 signatures over object_hash.
•	AICP-MSGCHAIN-1: Message hash chaining via prev_msg_hash.
6.2 Canonicalization (AICP-JCS-1) (normative)
For JSON objects, canonical_bytes MUST be produced using RFC 8785 JSON Canonicalization Scheme (JCS), UTF-8 encoded, and deterministic across implementations.
6.3 Object hashing (AICP-HASH-SHA256-1) (normative)
object_hash is computed as:
canonical_bytes = JCS(obj)
preimage = "AICP1\0" + object_type + "\0" + canonical_bytes
digest = SHA-256(preimage)
object_hash = "sha256:" + base64url(digest) (no padding)

Core object_type domains include: contract, amendment, message, attestation. New domains MUST be registered (Section 8) to prevent type-confusion attacks.
6.4 Signatures (AICP-SIG-ED25519-1) (normative)
A Signature binds signer identity (agent_id + kid) to an object_hash. For AICP-SIG-ED25519-1:
signing_input = UTF-8("AICP1\0SIG\0" + object_hash)
sig = Ed25519.sign(private_key, signing_input)

Messages that change the contract state SHOULD be signed and MUST satisfy signature_policy when required.
6.5 Message hash chaining (AICP-MSGCHAIN-1) (normative)
message_hash is object_hash in domain 'message' computed over the canonical 'signed message body'. The signed message body MUST include all envelope fields that influence meaning and ordering (including prev_msg_hash), and MUST exclude signatures/signature and message_hash itself.

If prev_msg_hash is present, it MUST equal the message_hash of the previous message in the chosen chain.
6.6 Test vectors (fixtures) (normative)
The authoritative fixtures for Core v0.1 are published in the reference package under fixtures/core_tv.json. They are repeated here for implementer convenience.
TV-01 (contract):
•	canonical_json = {"contract_id":"c1","goal":"demo","roles":["initiator","responder"]}
•	object_hash = sha256:3atge33khhRmVABSaXgxtgzqVMv0oFe5SFv_zCaiq_g
TV-02 (ed25519 signature of TV-01 object_hash):
•	public_key_b64url = A6EHv_POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg
•	signature_b64url = wlwZ7y5oTek1lFLDpzbaSQtZyFM7UHo77KLrv8qEAcz_L_4tAchGrzbR27eY2dp1oKp-2sEebKrf4LbPYF5WAw
TV-03 (message chain):
•	m1_message_hash = sha256:95ujQaZblvWlvBzYQWbM9K1JHJC2VjZJWRzsmXfrss0
•	m2_prev_msg_hash = sha256:95ujQaZblvWlvBzYQWbM9K1JHJC2VjZJWRzsmXfrss0
•	m2_message_hash = sha256:u5K09B7_w80ZGSaQvH-vNmPgfTWVVgREX3wf_yc7-fI
 
7. Conformance and testability
A protocol becomes real when independent implementations can prove compatibility via conformance tests, fixtures, and deterministic outcomes. Core v0.1 defines a minimal conformance matrix; extensions define their own.
7.1 Core v0.1 conformance matrix (normative minimum)
•	CT-01: CONTRACT_PROPOSE + quorum CONTRACT_ACCEPT -> Proposed -> Active[v1].
•	CT-02: AMENDMENT_PROPOSE (base=head) -> Amendment-in-flight; quorum AMENDMENT_ACCEPT -> Active[v2].
•	CT-03: Concurrent-accept: two different AMENDMENT_ACCEPT on same base_version -> Conflict detected by all parties.
•	CT-04: RESOLVE_CONFLICT choose with quorum -> Active on chosen head; superseded refs stop progressing if policy requires.
•	CT-05: RESOLVE_CONFLICT merge -> new head_version with merge_parents; parties converge to same resulting contract_hash.
•	CT-06: Unknown-base: accept/propose referencing unknown base_version -> buffered/rejected; MUST NOT silently change active head.
•	CT-07: CLOSE_SESSION with required confirmations -> Closed; AMENDMENT_* after Closed are rejected.
•	CT-08: ATTEST_ACTION in Conflict MUST include explicit head_version (and conflict_context via ext if used).
•	CT-09: JCS canonicalization matches TV-01 canonical_json.
•	CT-10: object_hash matches TV-01 object_hash.
•	CT-11: signature verification matches TV-02.
•	CT-12: message chain hashes match TV-03.
•	CT-13: INVALID_SIGNATURE: contract-changing message rejected; state unchanged; SHOULD emit ERROR INVALID_SIGNATURE.
•	CT-14: UNKNOWN_BASE_REF: no state change; SHOULD emit ERROR with recover_action=FETCH_OBJECT.
•	CT-15: DUPLICATE_MESSAGE_ID: idempotent handling (no double-apply).
•	CT-16: INVALID_CONTRACT_REF: attestation referencing unknown head_version rejected for audit; state unchanged.
7.2 Extension conformance suites (informative)
Each registered extension MUST ship its own conformance tests and fixtures, and register them in the registry entry. For example: CN-* for EXT-CAPNEG, TB-* for bindings, PE-* for policy evaluation, OR-* for object resync, IL-* for identity lifecycle.
 
8. RFC: Registry and Change Control
AICP requires public, mirrorable registries and a transparent change-control process to prevent identifier collisions, enable interoperable extensions, and keep compatibility reproducible without dependence on any single SaaS platform.
8.1 Principles (normative)
•	Registries MUST be publicly accessible, versioned, and mirrorable.
•	Each registry entry MUST reference a stable normative specification and a compatibility range.
•	Registries SHOULD support status stages: experimental, stable, deprecated, withdrawn.
•	Changes MUST be reproducible: tracked as diffs with a changelog and semantic versioning.
8.2 Minimum registry set (v0.1)
•	Message Types Registry (non-Core message_type identifiers).
•	Policy Categories Registry (machine-checkable schemas and semantics).
•	Security and Crypto Profiles Registry (canonicalization/hash/sign/encryption profiles).
•	Object Hash Domains Registry (domain separation strings).
•	Transport Bindings Registry (EXT-BIND-*).
•	Policy Languages and Bindings Registry (for EXT-POLICY-EVAL).
•	Policy Reason Codes Registry (stable reason identifiers).
•	Attestation Types and Identity Providers Registry (for identity lifecycle).
•	Security Events and Alert Categories Registry (for EXT-SECURITY-ALERT).
•	Dispute and Claim Types Registry (for challenges/claims).
8.3 Namespaces and collision avoidance (normative)
Identifiers SHOULD be namespaced using reverse-DNS (e.g., com.example.aicp.workflow.WORKFLOW_DECLARE). The namespace aicp.core.* is reserved and MUST NOT be used for third-party extensions.
8.4 Registry entry format (normative minimum)
Each registry entry MUST include: id, type, status, spec_ref, introduced_in, maintainer, security_considerations, and (optionally) conformance test references.
8.5 Registration and stability process (normative intent)
Registration MUST be open and auditable (e.g., public pull requests). To reach stable status, an entry SHOULD have at least one independent implementation and a minimal conformance suite. Crypto- and identity-affecting extensions SHOULD require security review.
8.6 Deprecation and withdrawal
Deprecated entries MUST provide a deprecation plan and recommended replacement. Withdrawn entries SHOULD be used only for severe security issues; history MUST remain available for audit reproducibility.
8.7 Publication integrity (recommended)
Registry releases SHOULD be signed and/or recorded in a transparency log (e.g., Sigstore) to provide tamper-evidence.
 
9. RFC: Error model and recovery
The error model makes integrations predictable. A protocol ERROR does not change contract state; it reports a failure to validate or apply a message, using machine-readable codes and recovery hints.
9.1 Principles (normative)
•	Errors MUST NOT change the contract state; they describe refusal or inability to apply a message.
•	Receivers MUST be idempotent by message_id.
•	ERROR payload MUST be safe to log (no secrets/PII unless policy explicitly allows).
•	Implementations MAY rate-limit ERROR replies to mitigate abuse, but SHOULD log locally for audit.
9.2 ERROR message (Core v0.1, SHOULD)
Core defines message_type=ERROR. Implementations SHOULD support generating and receiving ERROR; if a party declares ERROR support, it MUST follow this section.
ERROR payload fields (normative):
Field	Level	Meaning
error_code	MUST	Error code from Section 9.3 or registered extension.
error_class	MUST	VALIDATION | CRYPTO | STATE | POLICY | RATE | INTERNAL.
severity	MUST	low | medium | high | critical.
applies_to	MUST	Reference to message_id and/or object_hash.
disposition	MUST	IGNORED | BUFFERED | REJECTED.
recover_action	SHOULD	Recommended recovery action (Section 9.4).
retry_after_ms	MAY	Suggested delay for retry.
details	MAY	Human-readable explanation (no secrets/PII).
evidence_refs	MAY	References to hashes/logs/artifacts, if safe.
9.3 Core v0.1 error codes (minimum)
•	VALIDATION:
•	INVALID_ENVELOPE
•	UNKNOWN_MESSAGE_TYPE
•	DUPLICATE_MESSAGE_ID
•	INVALID_CONTRACT_REF
•	INVALID_PAYLOAD
•	CRYPTO:
•	SIGNATURE_REQUIRED
•	UNKNOWN_KEY
•	INVALID_SIGNATURE
•	HASH_MISMATCH
•	STATE:
•	SESSION_NOT_FOUND
•	SESSION_CLOSED
•	UNKNOWN_BASE_REF
•	INVALID_STATE_TRANSITION
•	CONFLICT_ACTIVE
•	QUORUM_NOT_MET
•	POLICY:
•	CONSENT_REQUIRED
•	AUTHORITY_MISSING
•	SCOPE_VIOLATION
•	TOOL_ACCESS_DENIED
•	PII_POLICY_BLOCKED
•	RATE:
•	RATE_LIMITED
•	DEADLINE_EXCEEDED
9.4 Recovery actions (recover_action)
•	RETRY_LATER: Retry later; use retry_after_ms if provided.
•	RESEND_MESSAGE: Resend the original message (transport loss).
•	FETCH_OBJECT: Retrieve a missing object/base_version (recommended: EXT-OBJECT-RESYNC).
•	SYNC_STATE: Resynchronize session head/state (recommended: EXT-OBJECT-RESYNC).
•	REQUEST_CONSENT: Prompt the human user for required consent and attach consent artifacts.
•	ROTATE_KEY: Rotate identity key and provide linkage proof (EXT-IDENTITY-LC).
•	CLOSE_SESSION: Close the session if recovery is unsafe or impossible.
9.5 Typical cases (normative)
UNKNOWN_BASE_REF: MUST NOT change state; SHOULD buffer if policy allows and request missing objects via FETCH_OBJECT.
INVALID_SIGNATURE: MUST reject and keep state unchanged; MAY emit SECURITY_ALERT via extension if attack is suspected.
SESSION_CLOSED: MUST reject any contract-changing messages.
 
10. RFC: EXT-CAPNEG — Capability and profile negotiation (Registered Extension)
EXT-CAPNEG defines a minimal, verifiable handshake so parties can agree on compatible profiles before executing side effects. It standardizes: (a) capability declarations; (b) a proposed profile selection; (c) an accepted negotiation_result that can be embedded into the Context Contract for auditability.

EXT-CAPNEG is transport-agnostic. It does not require a centralized service. Negotiation messages MAY be observed/enforced by third parties.
10.1 Message types (normative)
All EXT-CAPNEG messages MUST use the Core Envelope. They MUST NOT change the contract state directly unless the contract explicitly requires a negotiated profile for activation.
•	CAPABILITIES_DECLARE — publish capabilities of a party (crypto profiles, privacy modes, supported extensions, limits).
•	CAPABILITIES_PROPOSE — propose a concrete compatible selection and provide negotiation_result.
•	CAPABILITIES_ACCEPT — accept a negotiation_result.
•	CAPABILITIES_REJECT — reject with a machine-readable reason and (optionally) alternative constraints.
10.2 CapabilityDeclaration object (normative minimum)
CAPABILITIES_DECLARE payload MUST include:
•	capabilities_id (MUST): unique identifier for this declaration.
•	party_id (MUST): sender identifier (same as Envelope.sender).
•	supported_profiles (MUST): list of crypto/profile IDs (e.g., AICP-JCS-1, AICP-HASH-SHA256-1, AICP-SIG-ED25519-1, AICP-MSGCHAIN-1).
•	supported_privacy_modes (MUST): list of privacy_mode IDs (registered).
•	supported_extensions (SHOULD): list of extension IDs supported by the party.
•	supported_policy_categories (SHOULD): list of policy category IDs supported for evaluation/enforcement.
•	limits (SHOULD): max_message_bytes, max_object_bytes, max_objects_per_request, max_clock_skew_s.
•	bindings (MAY): supported transport bindings (e.g., EXT-BIND-MCP, EXT-BIND-HTTP).
•	languages (MAY): supported natural languages for human-facing text.
A party MAY issue multiple declarations over time. New declarations SHOULD reference supersedes_capabilities_id for auditability.
10.3 negotiation_result object (normative)
CAPABILITIES_PROPOSE MUST carry negotiation_result. negotiation_result is a hashable object (extension-defined) that MUST include:
•	negotiation_id (MUST): stable identifier for the negotiation attempt.
•	session_id and contract_id (MUST): bind the result to a specific session/contract.
•	participants (MUST): list of party_ids included in the agreement.
•	selected.crypto_profile (MUST): selected set of crypto/profile IDs.
•	selected.privacy_mode (MUST): selected privacy_mode.
•	selected.required_extensions (MAY): extensions required for this session/contract.
•	selected.required_policy_categories (MAY): policy categories that MUST be enforceable.
•	selected.limits (MAY): negotiated limits.
•	transcript_binding (SHOULD): hash binding to the negotiation transcript (e.g., message_hash of the last negotiation message).
A negotiation_result MUST be signed by the required parties (either as signatures on the CAPABILITIES_ACCEPT message, or as an object-level signature referenced by it).
10.4 Validation rules (normative)
•	Receivers MUST reject proposals that select a profile not included in their most recent CAPABILITIES_DECLARE.
•	Receivers MUST reject downgrade attempts below their local minimum acceptable security baseline (implementation-defined), and SHOULD explain via reason_code.
•	If the Context Contract requires a negotiated profile for activation, CONTRACT_ACCEPT MUST reference an accepted negotiation_result (by hash or embedded copy).
10.5 Conformance suite (CN-*) (normative minimum)
•	CN-01: Compatible declarations -> propose -> accept -> negotiation_result identical across implementations.
•	CN-02: Downgrade attempt (proposed weaker crypto_profile) -> reject with reason_code=DOWNGRADE_NOT_ALLOWED.
•	CN-03: Missing required extension -> reject with reason_code=REQUIRED_EXTENSION_UNSUPPORTED.
•	CN-04: Capabilities spoof (proposal selects unsupported id) -> reject, no state change.
10.6 Registry requirements (normative intent)
•	privacy_mode IDs and reason_code IDs MUST be registered (Section 8).
•	If negotiation_result introduces a new hash domain, it MUST be registered (Section 8, Object Hash Domains).
11. RFC: Transport bindings (Registered Extensions)
Transport bindings define how AICP envelopes are carried over specific transports or tool interfaces (Layers L0–L2) without changing Core semantics. Bindings MUST be reversible: the receiver MUST recover the original Envelope and Payload byte-for-byte at the semantic level (subject to canonicalization rules for signing/hashing).
11.1 Binding principles (normative)
•	A binding MUST NOT mutate Envelope/Payload fields.
•	A binding MUST specify delivery semantics (at-most-once / at-least-once), idempotency expectations, and ordering constraints.
•	A binding MUST define how receivers report acceptance/rejection (and how ERROR is transported).
•	A binding MUST document observer/MITM implications under each privacy_mode.
11.2 EXT-BIND-MCP — Binding over MCP (normative)
Model: an MCP server ("aicp-bridge") exposes tools and resources to exchange AICP envelopes. The bridge MAY be local (sidecar) or remote. If privacy_mode disallows relay visibility, payload MUST be protected before passing through a remote bridge.
Required MCP tools (normative minimum):
•	aicp.sendMessage(envelope) -> {accepted, error_envelope?, head_version?, cursor?}
•	aicp.pollMessages(session_id, after_cursor?, limit?) -> {messages[], next_cursor?}
•	aicp.getHead(session_id) -> {session_state, branch_heads, active_head_version?, final_head_version?}
•	aicp.getObject(object_hash) -> {status, object_type?, object_json?, artifact_ref?}
Recommended MCP resources (informative): aicp://sessions/{session_id}/head, aicp://objects/{object_hash}, aicp://sessions/{session_id}/messages?after=...
Delivery semantics: at-least-once is assumed. Receivers MUST be idempotent by message_id. Ordering MUST NOT be assumed; use contract_ref/base_version and message hash chaining when available.
11.3 EXT-BIND-HTTP — HTTP(S)/WebSocket binding (normative)
Model: an HTTP(S) service (or WSS gateway) accepts envelopes and provides polling for message replication. This binding does not define auth; deployments may use OAuth/JWT/mTLS, but MUST NOT alter envelopes.
Normative endpoints (minimum):
•	POST /aicp/v1/sessions/{session_id}/messages  (body: envelope) -> 202 Accepted or 4xx with optional ERROR
•	GET  /aicp/v1/sessions/{session_id}/messages?after={cursor}&limit=N -> {messages[], next_cursor}
•	GET  /aicp/v1/sessions/{session_id}/head -> {session_state, branch_heads, active_head_version?, final_head_version?}
•	GET  /aicp/v1/objects/{object_hash} (SHOULD) -> object or status (or redirect to artifact_ref)
Idempotency: servers MUST use message_id as an idempotency key; duplicate POST MUST NOT create duplicates and SHOULD return 200/202 with the same acceptance disposition.
11.4 EXT-BIND-BUS — Message bus binding (normative)
Model: publish/subscribe over a message bus (Kafka/NATS/etc). Topic naming MUST be documented and stable. Consumers MUST handle duplicates and reordering.
Recommended topics (informative):
•	aicp.sessions.{session_id}.messages  (envelopes)
•	aicp.sessions.{session_id}.head      (state sync snapshots)
If the bus supports message keys/partitions, publishers SHOULD use message_id as the key to improve ordering per session partition (still not a semantic guarantee).
11.5 Binding conformance (TB-*) (normative minimum)
•	TB-MCP-01: aicp.sendMessage transports Envelope losslessly; receiver validates signatures/hashes.
•	TB-HTTP-01: POST duplicates are idempotent by message_id; polling returns consistent ordering cursor semantics.
•	TB-BUS-01: duplicate delivery does not double-apply; consumer converges to same head_version.
12. RFC: EXT-POLICY-EVAL — Policy evaluation semantics (Registered Extension)
EXT-POLICY-EVAL standardizes how machine-checkable policies are packaged, evaluated, and evidenced across vendors. It intentionally avoids forcing a single policy language; instead it provides a reference binding mechanism to existing policy engines while keeping evaluations auditable.
12.1 Core objects (normative)
policy_bundle (normative minimum) MUST include: policy_bundle_id, version, language_id (registered), content (inline) OR artifact_ref, and content_hash (object_hash).
policy_binding (normative minimum) MUST include: binding_id (registered), parameters (MAY), input_schema_version (MUST).
evaluation_context (normative minimum) MUST include: context_id, contract_head_version, subject, action, resource, environment (MAY), and context_hash (object_hash over canonical form).
policy_decision (normative minimum) MUST include: decision (ALLOW|DENY|INCONCLUSIVE), reason_codes (SHOULD, registered), obligations (MAY), advice (MAY), evaluated_at, engine_info (MAY), and context_hash binding.
12.2 Message types and payloads (normative)
POLICY_EVAL_REQUEST payload MUST include: eval_id, policy_bundle_ref (hash or artifact_ref), policy_binding_ref, evaluation_context, and requested_action_id (MAY). It MAY include dry_run and deadline.
POLICY_EVAL_RESULT payload MUST include: eval_id, policy_decision, and MAY include evidence_refs. If the result is intended to be enforcement-relevant, it SHOULD be signed by the evaluating enforcer/engine identity.
POLICY_DECISION_ATTEST (optional) MAY be used to bind a policy_decision to ATTEST_ACTION when decisions are produced asynchronously.
12.3 Determinism requirements (normative intent)
•	The context_hash MUST be computed over a canonical evaluation_context so independent implementations can reproduce the input to the policy engine.
•	Policy engines that are non-deterministic (LLM classifiers) MAY be used only if their outputs are treated as evidence, not as deterministic truth; such use SHOULD be explicitly marked in engine_info.
12.4 Conformance suite (PE-*) (normative minimum)
•	PE-01: Same evaluation_context -> identical context_hash across implementations.
•	PE-02: Registered reason_codes used; unknown codes rejected or mapped per registry policy.
•	PE-03: Signed POLICY_EVAL_RESULT verifies under EXT-IDENTITY-LC rules when used for enforcement.
12.5 Registry bindings (normative)
language_id, binding_id, and reason_codes MUST be registered (Section 8).
13. RFC: EXT-OBJECT-RESYNC — Object retrieval and state resync (Registered Extension)
EXT-OBJECT-RESYNC provides a transport-independent recovery mechanism to fetch missing objects by object_hash and to resynchronize minimal session state. It is essential for real deployments with reordering, partial replication, offline operation, and third-party observation.
13.1 Message types (normative)
•	OBJECT_REQUEST — request one or more objects by object_hash.
•	OBJECT_RESPONSE — return objects or statuses for requested hashes.
•	STATE_SYNC_REQUEST — request minimal session state (heads, closed status, hints).
•	STATE_SYNC_RESPONSE — return minimal session state and replication hints.
13.2 OBJECT_REQUEST payload (normative minimum)
•	request_id (MUST): identifier for idempotency and correlation.
•	objects (MUST): list of {object_hash (MUST), want_type (MAY), max_bytes (MAY)}.
•	allow_redaction (SHOULD): whether REDACTED responses are acceptable.
•	allow_encrypted (MAY): whether encrypted objects are acceptable (binding/profile dependent).
•	max_total_bytes (MAY): receiver may cap response size.
13.3 OBJECT_RESPONSE payload (normative minimum)
OBJECT_RESPONSE MUST include request_id and entries[]. Each entry MUST include: object_hash, status, and (if status=FOUND) object_type and object_json (or artifact_ref).
status MUST be one of: FOUND | NOT_FOUND | ACCESS_DENIED | TOO_LARGE | REDACTED | ERROR.
If status=FOUND and object_json is provided, the receiver MUST ensure that re-hashing the object_json under the declared object_type yields object_hash.
13.4 STATE_SYNC_* payloads (normative minimum)
STATE_SYNC_REQUEST MUST include: request_id (MUST), known_heads (MAY), known_message_hash (MAY), want_closed_status (MAY).
STATE_SYNC_RESPONSE MUST include: request_id (MUST), session_state (MUST), branch_heads (MUST), active_head_version (MAY), final_head_version (MAY), replication_hints (MAY).
13.5 Security and privacy considerations (normative intent)
•	Implementations SHOULD mitigate DoS/amplification (rate limits, max bytes, chunking via artifact_ref, and TOO_LARGE responses).
•	Object existence leakage is a security concern; implementations MAY respond with ACCESS_DENIED instead of NOT_FOUND based on policy.
•	Redaction MUST be explicit (status=REDACTED) and SHOULD include redaction_note. Receivers MUST NOT silently alter objects.
13.6 Conformance suite (OR-*) (normative minimum)
•	OR-01: UNKNOWN_BASE_REF -> ERROR with recover_action=FETCH_OBJECT; OBJECT_REQUEST/RESPONSE resolves it.
•	OR-02: HASH_MISMATCH on FOUND object -> reject and raise CRYPTO error.
14. RFC: EXT-IDENTITY-LC — Identity lifecycle (Registered Extension)
EXT-IDENTITY-LC standardizes identity lifecycle events so long-lived or cross-platform sessions remain verifiable even when keys rotate or agents migrate. It introduces an Agent Identity Document (AID) as a canonical, hashable object and defines rotation/revocation semantics that third-party enforcers can verify.
14.1 Agent Identity Document (AID) (normative)
AID MUST be a canonical object (subject to AICP-JCS-1) that includes at minimum: agent_id (MUST), issuer (SHOULD), issued_at (MUST), expires_at (SHOULD), keys[] (MUST).
Each keys[] entry MUST include: kid (MUST), alg (MUST), public_key_b64url (MUST), status (MUST: active|retiring|revoked), not_before (MAY), not_after (MAY).
AID MAY include: provider metadata (name/version), revocation endpoints, external attestation refs, and constraints (e.g., allowed transports).
14.2 Message types (normative)
•	IDENTITY_ANNOUNCE — announce or update an AID reference for a session.
•	KEY_ROTATION — introduce a new key and retire an old key with cross-signing.
•	KEY_REVOKE — revoke a kid/key set by a revocation authority per policy.
•	AGENT_MIGRATION — record runtime/model/environment migration with updated AID and optional attestations.
14.3 Payloads (normative minimum)
IDENTITY_ANNOUNCE payload MUST include: aid_hash (MUST), aid_ref (MAY), supersedes_aid_hash (MAY), reason (MAY).
KEY_ROTATION payload MUST include: rotation_id (MUST), old_kid (MUST), new_key (MUST: kid+public_key+alg), effective_at (MAY), cross_signatures (MUST) where: (a) old key signs the new key material; and (b) new key signs the old key identifier.
KEY_REVOKE payload MUST include: revocation_id (MUST), target_kid or target_aid_hash (MUST), reason_code (SHOULD, registered), effective_at (MUST), issuer_attestation_ref (MAY).
AGENT_MIGRATION payload MUST include: migration_id (MUST), from_agent_version/from_environment (SHOULD), to_agent_version/to_environment (SHOULD), aid_hash (MUST), external_attestations (MAY).
14.4 Validation rules (normative)
•	KEY_ROTATION without valid cross_signatures MUST be rejected.
•	Once a KEY_REVOKE is known, messages signed by the revoked kid MUST be rejected for contract-changing operations; local policy MAY allow limited read-only audit parsing.
•	If AID is expired and no newer AID is available, implementations SHOULD enter a safe degraded mode (freeze side effects) or close per policy.
14.5 Conformance suite (IL-*) (normative minimum)
•	IL-01: IDENTITY_ANNOUNCE + valid AID -> resolver loads active keys; signatures verify.
•	IL-02: KEY_ROTATION cross-signing verified; old key transitions to retiring; new key becomes active.
•	IL-03: KEY_REVOKE -> subsequent messages by revoked key rejected.
15. RFC: Applied extensions (workflow, delegation, disputes, security alerts)
This section defines optional but broadly useful extensions for real products. They are designed to be enforceable by third-party enforcers and to remain transport-agnostic. Each extension below MUST be registered (Section 8). Parties MAY require specific extensions via EXT-CAPNEG and/or contract.signature_policy.
15.1 EXT-WORKFLOW-SYNC — Workflow synchronization (Registered Extension)
Purpose: synchronize a machine-readable workflow (plan/graph) as part of context, and attest step execution in a way a third-party enforcer can verify.
Message types:
•	WORKFLOW_DECLARE — introduce a workflow artifact and bind it to a contract head_version.
•	WORKFLOW_UPDATE — update/replace the workflow artifact (new version), referencing base_workflow_ref.
•	WORKFLOW_STEP_ATTEST — attest execution of a workflow step (inputs/outputs/evidence) under a specific head_version.
WORKFLOW_DECLARE payload (normative minimum): workflow_id (MUST), contract_head_version (MUST), workflow_artifact_ref (MUST), workflow_hash (SHOULD), version (MUST), step_index (MAY), policies_applied (MAY).
WORKFLOW_STEP_ATTEST payload (normative minimum): workflow_id (MUST), step_id (MUST), contract_head_version (MUST), status (MUST: started|completed|failed|skipped), input_refs or input_hash (SHOULD), output_refs or output_hash (SHOULD), evidence_refs (MAY), started_at/ended_at (MAY).
Enforcement hooks (normative intent): an enforcer MAY require that side effects only occur after a prior WORKFLOW_STEP_ATTEST or after a policy_decision attached to it.
15.2 EXT-DELEGATION — Hierarchical purpose-oriented delegation (Registered Extension)
Purpose: allow a delegator to formally grant a subset of authority to a delegatee for a specific purpose, with hierarchical delegation limits, and with verifiable result control retained by the delegator.
Message types:
•	DELEGATION_GRANT — grant authority subset with scope, purpose, acceptance criteria, expiry, and max_depth.
•	DELEGATION_ACCEPT — accept the grant (delegatee commitment).
•	DELEGATION_REVOKE — revoke delegation (immediate or scheduled).
•	DELEGATION_RESULT_ATTEST — delegatee attests results bound to purpose and head_version.
DELEGATION_GRANT payload (normative minimum): delegation_id (MUST), delegator (MUST), delegatee (MUST), parent_delegation_id (MAY), authority_subset (MUST), scope (MUST), purpose (MUST), acceptance_criteria (SHOULD), expiry (MUST), max_depth (SHOULD, default=0), required_attestations (MAY).
Purpose-oriented control (normative): the delegator retains the right to accept/reject outcomes. A delegatee result MUST be attested via DELEGATION_RESULT_ATTEST and MAY be challenged or claimed as breach (Section 15.3).
15.3 EXT-DISPUTES — Challenges, breach claims, arbitration hooks (Registered Extension)
Purpose: interoperable dispute primitives to challenge suspected distortion, incorrect results, or improper execution of delegated obligations, and to optionally request arbitration.
Message types:
•	CHALLENGE_ASSERTION — dispute an attestation/object/message with evidence and requested remedy.
•	CLAIM_BREACH — assert breach of delegation purpose, acceptance criteria, or contract obligation.
•	ARBITRATION_REQUEST (optional) — request arbitration by a designated arbitrator party or profile.
•	ARBITRATION_RESULT (optional) — publish arbitration outcome with signatures.
CHALLENGE_ASSERTION payload (normative minimum): challenge_id (MUST), target_ref (MUST: object_hash or message_id), challenge_type (MUST, registered), claim (MUST), evidence_refs (SHOULD), requested_remedy (MAY), deadline (MAY).
CLAIM_BREACH payload (normative minimum): claim_id (MUST), delegation_id or obligation_ref (MUST), breach_type (MUST, registered), narrative (SHOULD), evidence_refs (SHOULD), requested_remedy (MAY).
15.4 EXT-SECURITY-ALERT — Security events and escalation (Registered Extension)
Purpose: standardize security incident reporting for agent-to-agent interaction (e.g., suspected malicious result distortion, key substitution, replay/forgery attempts) with evidence binding.
Message types:
•	SECURITY_ALERT — report a security event bound to session evidence.
SECURITY_ALERT payload (normative minimum): alert_id (MUST), category (MUST, registered), severity (MUST: low|medium|high|critical), suspected_actor (MAY), suspected_attack (MAY), indicators (SHOULD), evidence_refs (SHOULD), recommended_action (MAY), disclosure_policy (MAY).
15.5 Extension conformance (normative minimum)
•	AW-01: WORKFLOW_DECLARE + WORKFLOW_STEP_ATTEST validates head_version binding and evidence_refs hashing.
•	AD-01: DELEGATION_GRANT/ACCEPT/RESULT_ATTEST forms a verifiable chain of responsibility; max_depth enforced.
•	DS-01: CHALLENGE_ASSERTION references an existing attestation and is audit-verifiable via object_hash.
•	SA-01: SECURITY_ALERT includes evidence_refs and does not leak secrets/PII beyond policy.
16. RFC: Governance / IPR / Stewardship
Open standards often fail without clear licensing, patent posture, and stewardship. This section defines minimum governance requirements so AICP can be adopted by companies and communities.
16.1 Goals
•	Provide a transparent RFC/change process and registry stewardship.
•	Make adoption legally safe: clear licenses for spec text, code, fixtures, and a patent posture.
•	Preserve interoperability through semantic versioning and conformance marks.
16.2 Non-Goals
•	Mandating a specific legal entity or jurisdiction.
•	Blocking commercial implementations.
16.3 Licensing (recommended)
Specification text SHOULD use a permissive documentation license (e.g., CC BY 4.0). Reference implementations and conformance harness SHOULD use a permissive software license (e.g., Apache-2.0 or MIT). Fixtures SHOULD be licensed for CI embedding.
16.4 Patent posture (recommended)
Core contributors SHOULD provide a royalty-free patent grant or equivalent to reduce enterprise adoption risk.
16.5 Security disclosure
A public vulnerability disclosure process MUST exist (e.g., SECURITY.md and a security contact). Crypto- and identity-related changes MUST include new fixtures/test vectors.
16.6 Compatibility marks
Implementations SHOULD declare compatibility in the form: 'AICP-Core-0.1' plus a list of supported extensions and profiles (e.g., '+ EXT-CAPNEG + EXT-BIND-MCP').
 
17. Reference implementations and conformance harness
Reference implementations and a conformance harness are part of the standard toolkit. They make the protocol executable and reduce integration cost. Reference code is not production-grade security software; production systems MUST undergo security review.
17.1 Required artifacts (normative intent)
•	Reference library implementing Core algorithms: JCS, object_hash, Ed25519 verify/sign, message hash chain.
•	Minimal contract replica implementing CT-01..CT-08 state machine behavior.
•	Fixtures: TV-01..TV-03 synchronized with this spec.
•	Conformance runner suitable for CI (pytest or equivalent).
17.2 Recommended run (Python example)
Example commands:
cd reference/python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
 
18. RFC: Interop event and external security review
18.1 Why interop and security review are required
Interoperability cannot be assumed even with a good spec: subtle differences (canonicalization, idempotency, conflict handling, recovery) break cross-vendor compatibility. Crypto and identity details require independent review.
18.2 Interop event (AICP Interop)
•	Entry criteria:
•	Implementation passes Core conformance tests CT-01..CT-16 and fixtures TV-01..TV-03.
•	Implementation declares its supported profiles and extensions.
•	Procedure (minimum):
•	Pairwise runs between independent implementations over the same scenarios: propose/accept/amend/conflict/resolve/close.
•	Record artifacts: messages, computed hashes, validation results, and decision logs (without PII).
•	Classify mismatches as spec bug / implementation bug / undefined behavior; publish errata and updated fixtures when needed.
•	Deliverables:
•	Public interop report with compatibility matrix.
•	Errata pack (patch/minor releases) with updated fixtures/test vectors.
18.3 External security review (minimum scope)
•	Core crypto profiles: JCS usage, hashing, signing_input, message chain; Unicode/number pitfalls.
•	Error model and recovery: information leakage and replay/idempotency.
•	EXT-OBJECT-RESYNC: DoS/amplification and existence leakage.
•	EXT-IDENTITY-LC: rotation, revocation, migration, issuer trust assumptions.
•	EXT-CAPNEG: downgrade and capability spoofing.
18.4 Exit criteria for AICP Core v0.1.0 (recommended)
•	At least two independent implementations interoperate on Core v0.1.
•	No unresolved critical/high security findings; disclosure process established.
•	Registry snapshot published and signed; errata process available.
 
Roadmap and current status
This roadmap tracks progress from positioning to an executable protocol suite. Current document version: 0.1.21. This English master includes content up to Step 18.
•	[Done] 0) Positioning: AI-OSI layers and AICP scope.
•	[Done] 1) RFC frame: Problem/Goals/Non-Goals/Requirements + Core vs Extensions.
•	[Done] 2) Glossary: contract/session/message, roles, amendments, evidence, disputes.
•	[Done] 3) Roles and states: RSM + conflict classes + resolution.
•	[Done] 4) Core messages: envelope + propose/accept/amend/attest/violate/resolve/close.
•	[Done] 5) Core policies: authority/consent/consent-auth/scope/boundaries/tools/PII/auditability.
•	[Done] 6) Crypto minimum: JCS, object_hash, signatures, message hash chain, fixtures.
•	[Done] 7) Core conformance matrix + fixtures.
•	[Done] 8) Registry and change control.
•	[Done] 9) Error model and recovery.
•	[Done] 10) EXT-CAPNEG.
•	[Done] 11) Transport bindings (EXT-BIND-*).
•	[Done] 12) EXT-POLICY-EVAL.
•	[Done] 13) EXT-OBJECT-RESYNC.
•	[Done] 14) EXT-IDENTITY-LC.
•	[Done] 15) Applied extensions: workflow/delegation/disputes/security alerts.
•	[Done] 16) Governance/IPR and stewardship.
•	[Done] 17) Reference implementations + conformance harness.
•	[Done] 18) Interop event + external security review.
•	[Next] 19) Release candidate (RC) for Core v0.1: feature freeze, publish registry snapshot, and run errata/patch cycle based on interop/security review.
