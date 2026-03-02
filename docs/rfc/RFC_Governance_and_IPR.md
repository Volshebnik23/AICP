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
Implementations SHOULD declare compatibility in the form: 'AICP-Core-0.1' plus a list of supported extensions and profiles (e.g., '+ EXT-CAPNEG + BIND-MCP-0.1 (deprecated alias EXT-BIND-MCP may be accepted for legacy input)').
