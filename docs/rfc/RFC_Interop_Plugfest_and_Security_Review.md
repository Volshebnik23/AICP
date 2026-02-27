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
