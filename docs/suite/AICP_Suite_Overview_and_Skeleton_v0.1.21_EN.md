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
Canonical source: `docs/rfc/RFC_Registries_and_Change_Control.md`
Summary: Defines registry principles, required registry sets, entry format, and change/deprecation controls.

9. RFC: Error model and recovery
Canonical source: `docs/rfc/RFC_Error_Model_and_Recovery.md`
Summary: Defines ERROR semantics, code taxonomy, and deterministic recovery behaviors.

10. RFC: EXT-CAPNEG — Capability and profile negotiation (Registered Extension)
Canonical source: `docs/extensions/RFC_EXT_CAPNEG.md`
Summary: Defines capability/profile declaration and negotiation to avoid downgrade and ambiguity.

11. RFC: Transport bindings (Registered Extensions)
Canonical sources:
- `docs/bindings/RFC_BIND_MCP.md`
- `docs/bindings/RFC_BIND_HTTP_WS.md`
- `docs/bindings/RFC_BIND_MESSAGE_BUS.md`
Summary: Defines binding-specific carriage and runtime rules while preserving Core semantics.

12. RFC: EXT-POLICY-EVAL — Policy evaluation semantics (Registered Extension)
Canonical source: `docs/extensions/RFC_EXT_POLICY_EVAL.md`
Summary: Defines policy decision/evidence interoperability for external policy engines.

13. RFC: EXT-OBJECT-RESYNC — Object retrieval and state resync (Registered Extension)
Canonical source: `docs/extensions/RFC_EXT_OBJECT_RESYNC.md`
Summary: Defines deterministic object retrieval, verification, and unknown-base recovery.

14. RFC: EXT-IDENTITY-LC — Identity lifecycle (Registered Extension)
Canonical source: `docs/extensions/RFC_EXT_IDENTITY_LIFECYCLE.md`
Summary: Defines identity announcement, rotation, revocation, and migration primitives.

15. RFC: Applied extensions (workflow, delegation, disputes, security alerts)
Canonical sources:
- `docs/extensions/RFC_EXT_WORKFLOW_SYNC.md`
- `docs/extensions/RFC_EXT_DELEGATION.md`
- `docs/extensions/RFC_EXT_DISPUTES.md`
- `docs/extensions/RFC_EXT_SECURITY_ALERTS.md`
Summary: Defines applied extension primitives for workflow sync, delegation, disputes, and security escalation.

16. RFC: Governance / IPR / Stewardship
Canonical source: `docs/rfc/RFC_Governance_and_IPR.md`
Summary: Defines stewardship, licensing, patent posture, security disclosure, and compatibility marks.

17. Reference implementations and conformance harness
Canonical source: `docs/rfc/RFC_Reference_Impl_and_Conformance_Harness.md`
Summary: Defines minimal executable reference artifacts and CI-oriented conformance harness expectations.

18. RFC: Interop event and external security review
Canonical source: `docs/rfc/RFC_Interop_Plugfest_and_Security_Review.md`
Summary: Defines interop event procedure, outputs, and external security review scope/exit criteria.

Canonical sources note: Standalone RFC documents under `docs/rfc/`, `docs/extensions/`, and `docs/bindings/` are the canonical locations for Sections 8–18 content. This Suite document is an umbrella index.

Roadmap and current status
See `ROADMAP.md` for repo-backed status. Current milestone: M4 (Conformance as a product: runner + compatibility report).
