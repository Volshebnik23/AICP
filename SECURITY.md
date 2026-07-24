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

The repository contains an internal self-review, automated negative tests, and a coverage
map with both strong and partial rows. It does not contain a completed independent external
security review. Do not describe the review scaffolding or `SELF_REVIEW.md` as external
assurance. Remaining coverage and external-review work is planned under M67; see
`docs/process/AICP_Repo_Truth_Baseline.md`.
