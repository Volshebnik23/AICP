# Security Policy

## Reporting a Vulnerability

Please report potential security issues privately to project maintainers before public disclosure.

Include:
- affected files/components
- reproduction steps
- impact assessment
- suggested mitigations (if any)

Do not commit secrets, credentials, or private keys to this repository.


## Security review artifacts
See `security_review/README.md` for threat model, assumptions, checklist, and remediation log scaffolding.

After private reporting and coordinated disclosure timing, remediation tracking can be recorded in `security_review/REMEDIATION_LOG.md`.

### Current review status

M67 shipped an internal, machine-validated threat-coverage manifest and generated map with
36 components: 24 `covered`, 12 `deferred`, and 0 `partial`. Covered rows resolve to named
executable evidence; deferred rows preserve their deployment or ecosystem boundary and
rationale. See `security_review/threat_coverage.json`, `security_review/COVERAGE_MAP.md`, and
`security_review/M67_SECURITY_CLOSURE.md`.

The repository does not contain a completed independent external security-review artifact.
Do not describe the review scaffolding, `SELF_REVIEW.md`, M67 closure, or repository-generated
conformance evidence as external assurance. The future handoff and artifact contract are in
`security_review/EXTERNAL_REVIEW_HANDOFF.md` and `security_review/external_reviews/README.md`.

The experimental CAPNEG v0.2 surface has an explicit threat/negative-vector map in
`docs/security/CAPNEG_v0.2_Threat_Model.md` and executable coverage in
`conformance/extensions/CN_CAPNEG_0.2.json`. That internal coverage does not establish
participant identity or authority, truthful capability declarations, external component
conformance, off-transcript consensus, policy correctness, transport security, or an
independent security review.
