# AICP Documentation Index

AICP is a **transport-independent, content-layer protocol** for governed agent-to-agent sessions with verifiable transcripts, policy references, attestations, and enforcement-compatible artifacts.

## What AICP is

- A standard for governed conversation/context artifacts between agents.
- A content-layer protocol with deterministic hashing and transcript semantics.
- A protocol that supports policy/evidence-aware moderation and enforcement workflows.

## What AICP is not

- Not a discovery/directory protocol.
- Not a calling/connectivity or transport protocol.
- Not a tool catalog or tool execution protocol.
- Not an IAM system or payment rail.
- Not a hosted chat platform or trust fabric by itself.

## Choose your path

- **Agent developer:** start with [START_HERE_IMPLEMENTERS.md](../START_HERE_IMPLEMENTERS.md) and [docs/guides/AGENT_DEVELOPERS_GUIDE.md](guides/AGENT_DEVELOPERS_GUIDE.md).
- **Mediator / Host developer:** use [docs/guides/PLATFORM_BUILDERS_GUIDE.md](guides/PLATFORM_BUILDERS_GUIDE.md), [docs/playbooks/Session_Topologies.md](playbooks/Session_Topologies.md), and [docs/architecture/Enforcement_Models.md](architecture/Enforcement_Models.md).
- **Enforcer / Moderator developer:** use [docs/architecture/Enforcement_Models.md](architecture/Enforcement_Models.md) and extension RFCs under [docs/extensions/](extensions/).
- **Platform architect:** start with [docs/architecture/AICP_in_the_Ecosystem.md](architecture/AICP_in_the_Ecosystem.md).
- **Product / Solution architect:** start with [docs/profiles/Profile_Selection_Guide.md](profiles/Profile_Selection_Guide.md) and [docs/playbooks/](playbooks/).

## Start here by goal

- **I want to integrate AICP into an existing agent** → [START_HERE_IMPLEMENTERS.md](../START_HERE_IMPLEMENTERS.md), [templates/](../templates/).
- **I want to host moderated AICP sessions** → [docs/playbooks/Brand_Reception_and_Support.md](playbooks/Brand_Reception_and_Support.md), [docs/architecture/Enforcement_Models.md](architecture/Enforcement_Models.md).
- **I want to validate compatibility with a profile** → [docs/profiles/AICP_Profiles.md](profiles/AICP_Profiles.md), [docs/profiles/Profile_Selection_Guide.md](profiles/Profile_Selection_Guide.md).
- **I want to understand architecture boundaries** → [docs/architecture/AICP_in_the_Ecosystem.md](architecture/AICP_in_the_Ecosystem.md).
- **I want to design a real product around AICP** → [docs/playbooks/](playbooks/) + [docs/playbooks/Session_Topologies.md](playbooks/Session_Topologies.md).

## Extension discoverability and maturity

- Extension RFC index: [docs/extensions/README.md](extensions/README.md)
- Extension maturity notes (shipped vs incubating wording): [docs/extensions/README.md#how-to-read-maturity-in-this-repo](extensions/README.md#how-to-read-maturity-in-this-repo)
- Extension RFC folder: [docs/extensions/](extensions/)
- Key extension RFCs for current enterprise-control milestones: [RFC_EXT_CONFIDENTIALITY.md](extensions/RFC_EXT_CONFIDENTIALITY.md), [RFC_EXT_REDACTION.md](extensions/RFC_EXT_REDACTION.md), [RFC_EXT_HUMAN_APPROVAL.md](extensions/RFC_EXT_HUMAN_APPROVAL.md), [RFC_EXT_IAM_BRIDGE.md](extensions/RFC_EXT_IAM_BRIDGE.md), [RFC_EXT_OBSERVABILITY.md](extensions/RFC_EXT_OBSERVABILITY.md), [RFC_EXT_ENTERPRISE_BINDINGS.md](extensions/RFC_EXT_ENTERPRISE_BINDINGS.md)
- Executable extension checks: [conformance/extensions/](../conformance/extensions/)
- Source of truth for shipped vs incubating milestone status: [ROADMAP.md](../ROADMAP.md)

### Quick links for shipped enterprise-control extensions

- Human Approval (M26): [RFC_EXT_HUMAN_APPROVAL.md](extensions/RFC_EXT_HUMAN_APPROVAL.md) + suite [`HA_HUMAN_APPROVAL_0.1.json`](../conformance/extensions/HA_HUMAN_APPROVAL_0.1.json)
- IAM Bridge (M28): [RFC_EXT_IAM_BRIDGE.md](extensions/RFC_EXT_IAM_BRIDGE.md) + suite [`IB_IAM_BRIDGE_0.1.json`](../conformance/extensions/IB_IAM_BRIDGE_0.1.json)
- Observability production attributes (M27): [RFC_EXT_OBSERVABILITY.md](extensions/RFC_EXT_OBSERVABILITY.md) + suite [`OB_OBSERVABILITY_0.1.json`](../conformance/extensions/OB_OBSERVABILITY_0.1.json)
- Enterprise domain bindings (M29): [RFC_EXT_ENTERPRISE_BINDINGS.md](extensions/RFC_EXT_ENTERPRISE_BINDINGS.md) + suite [`EB_ENTERPRISE_BINDINGS_0.1.json`](../conformance/extensions/EB_ENTERPRISE_BINDINGS_0.1.json)
- Marketplace orchestration (M36): [RFC_EXT_MARKETPLACE.md](extensions/RFC_EXT_MARKETPLACE.md) + suite [`MP_MARKETPLACE_0.1.json`](../conformance/extensions/MP_MARKETPLACE_0.1.json)
- Full extension index and maturity notes: [docs/extensions/README.md](extensions/README.md)

Note: document/fixture/schema presence does not by itself mean a milestone is shipped; roadmap + executable conformance surface define release maturity.


## M34 security & operations cookbook quickstart

- [Mediated Blocking in Production](playbooks/Mediated_Blocking_in_Production.md)
- [OAuth Bridge Cookbook](playbooks/OAuth_Bridge_Cookbook.md)
- [Tool Catalog Pinning Cookbook](playbooks/Tool_Catalog_Pinning_Cookbook.md)
- [Context Hub Fresh Content Cookbook](playbooks/Context_Hub_Fresh_Content_Cookbook.md)

## Core docs map

- Repo front door: [README.md](../README.md)
- Implementer quickstart: [START_HERE_IMPLEMENTERS.md](../START_HERE_IMPLEMENTERS.md)
- Standard overview: [docs/overview/AICP_STANDARD_OVERVIEW.md](overview/AICP_STANDARD_OVERVIEW.md)
- Profiles: [docs/profiles/AICP_Profiles.md](profiles/AICP_Profiles.md)
- Profile selection: [docs/profiles/Profile_Selection_Guide.md](profiles/Profile_Selection_Guide.md)
- Ecosystem positioning: [docs/architecture/AICP_in_the_Ecosystem.md](architecture/AICP_in_the_Ecosystem.md)
- Solution playbooks: [docs/playbooks/](playbooks/)
  - Security/ops cookbooks: [Mediated Blocking in Production](playbooks/Mediated_Blocking_in_Production.md), [OAuth Bridge Cookbook](playbooks/OAuth_Bridge_Cookbook.md), [Tool Catalog Pinning Cookbook](playbooks/Tool_Catalog_Pinning_Cookbook.md), [Context Hub Fresh Content Cookbook](playbooks/Context_Hub_Fresh_Content_Cookbook.md)
- Enforcement models: [docs/architecture/Enforcement_Models.md](architecture/Enforcement_Models.md)
- Security best practices: [docs/security/SECURITY_BEST_PRACTICES.md](security/SECURITY_BEST_PRACTICES.md)
- Repo-truth recovery workflow (RTSS): [docs/process/RTSS.md](process/RTSS.md)
- Canonical flows: [docs/flows/AICP_Canonical_Flows.md](flows/AICP_Canonical_Flows.md)
