# AICP Standard Overview

AICP is a content-layer agent-to-agent protocol for verifiable transcripts and enforceable policies in mediated channels.

For canonical term definitions, use the glossary: [docs/GLOSSARY.md](../GLOSSARY.md).

## Core roles

- **Mediator / Host**: serializes transcript order, gates delivery/side-effects, and preserves auditable flow integrity.
- **Enforcer / Moderator**: issues verdicts, sanctions, and alert guidance tied to policy/evidence.
- **Agents**: participants that propose/accept contracts and exchange protocol messages.

## Profiles (product feature of the standard)

Profiles are named bundles of required extensions, behavior expectations, and badge criteria. They convert “optional extension sets” into implementation targets with measurable conformance outcomes.

## What AICP is NOT

- Not a transport protocol (works over HTTP/WS/message bus/other transports).
- Not a tool protocol (complements MCP; does not replace it).
- Not an IAM/PAM/RBAC system (can reference external IAM decisions).
- Not a domain ontology.
- Not a hosted platform or CA.

## Version and status labels (avoid confusion)

- **Protocol version (`aicp_version`)**: wire/content semantics and conformance target (for example `0.1`).
- **Repo/release version (`VERSION`, release notes tags)**: packaging cadence of this repository.
- **Roadmap milestone IDs (`Mxx`)**: planning progress labels, not protocol negotiation values.

## Try it now

- `make quickstart-py`
- `make quickstart-ts`
- `make conformance-all`
- `make template-smoke`

## Where to go next

- Start Here: [START_HERE_IMPLEMENTERS.md](../../START_HERE_IMPLEMENTERS.md)
- Profiles: [docs/profiles/AICP_Profiles.md](../profiles/AICP_Profiles.md)
- Canonical flows: [docs/flows/AICP_Canonical_Flows.md](../flows/AICP_Canonical_Flows.md)
- Conformance suites/runner: [conformance/](../../conformance/)
- Security review package: [security_review/](../../security_review/)
