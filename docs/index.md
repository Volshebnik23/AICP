# AICP — Agent Interaction Content Protocol

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

AICP helps teams build trustworthy agent ecosystems with verifiable message content, explicit policy enforcement hooks, and interoperable conformance artifacts.

## The problem AICP solves

- **Trust:** deterministic hashes, chains, and signatures for verifiable interaction history.
- **Interoperability:** shared schemas, fixtures, registries, and conformance suites.
- **Enforcement:** protocol-level structures that enforcers can evaluate independently.

## Roles

- **Agent:** sends/receives protocol messages and executes capabilities.
- **Enforcer:** validates policy constraints, signatures, hashes, and conformance outcomes.
- **Observer:** audits transcripts and attestations for governance/compliance.

## Profiles and extensions

AICP Core is minimal and stable; extensions are optional and productized in waves. Not all features are mandatory for every implementation.

## Primary links

- Standard overview (30 seconds): [docs/overview/AICP_STANDARD_OVERVIEW.md](overview/AICP_STANDARD_OVERVIEW.md)
- Start Here for Implementers: [START_HERE_IMPLEMENTERS.md](../START_HERE_IMPLEMENTERS.md)
- Suite index: [AICP_Suite_Overview_and_Skeleton_v0.1.21_EN.md](suite/AICP_Suite_Overview_and_Skeleton_v0.1.21_EN.md)
- Core normative markdown: [AICP_Core_v0.1_Normative.md](core/AICP_Core_v0.1_Normative.md)
- Core docs: [docs/core/](core/)
- Glossary (canonical): [docs/GLOSSARY.md](GLOSSARY.md)
- Drop-ins (copy folder): [dropins/aicp-core/](../dropins/aicp-core/)
- Sandbox validator: [sandbox/run.py](../sandbox/run.py)
- Conformance: [conformance/](../conformance/)
- Platform builders guide: [docs/guides/PLATFORM_BUILDERS_GUIDE.md](guides/PLATFORM_BUILDERS_GUIDE.md)
- Agent developers guide: [docs/guides/AGENT_DEVELOPERS_GUIDE.md](guides/AGENT_DEVELOPERS_GUIDE.md)
- Error and recovery playbook: [docs/ops/ERROR_AND_RECOVERY.md](ops/ERROR_AND_RECOVERY.md)
- References: [reference/](../reference/)
- Registries: [registry/](../registry/)

## For platform builders

Start with `schemas/core/`, `registry/`, and `conformance/` to implement enforcer-grade validation and compatibility gates.

## For agent developers

Start with `reference/python/`, `sdk/typescript/`, and `templates/ts-agent/` to bootstrap message generation, hashing, and chain handling.

Keywords: agent-to-agent, multi-agent, LLM agents, content-layer protocol, policy enforcement, orchestration, governance, attestations, interoperability standard
