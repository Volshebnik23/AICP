# AICP — Agent Interaction Content Protocol

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

AICP is a practical, implementable protocol repo for teams building multi-agent platforms.

➡️ **Start here:** [START_HERE_IMPLEMENTERS.md](START_HERE_IMPLEMENTERS.md)
➡️ **30-second standard overview:** [docs/overview/AICP_STANDARD_OVERVIEW.md](docs/overview/AICP_STANDARD_OVERVIEW.md)

## What AICP is

- An **agent-to-agent protocol** focused on interoperable message content, not transport lock-in.
- A **content-layer** standard with deterministic hashing/canonicalization for verifiable exchanges.
- Built for **enforcement / enforcer** workflows (policy checks, replay checks, conformance checks).
- Includes **policies & attestations** primitives for trust, auditability, and governance.
- Supports **profiles / negotiation** and extension-based capability growth.


## Quickstart

- `make quickstart-ts`
- `make quickstart-py`

Both commands generate a deterministic minimal Core transcript and validate it locally.

## Implementer path

1. Read the suite index: `docs/suite/AICP_Suite_Overview_and_Skeleton_v0.1.21_EN.md`
2. Implement against schemas in `schemas/`
3. Validate with:
   - `make validate`
   - `make conformance`
   - `make conformance-ext`
4. Reuse references:
   - Python reference: `reference/python/`
   - TypeScript SDK: `sdk/typescript/`

## Canonical layout

- Core normative document (canonical): `docs/core/AICP_Core_v0.1_Normative.md`
- Glossary: `docs/GLOSSARY.md`
- Optional release artifact (not edited in normal PRs): `docs/core/AICP_Core_v0.1_Normative_0.1.0.docx`
- Core schemas: `schemas/core/`
- Core fixtures and golden transcripts: `fixtures/`
- Conformance suite and runner: `conformance/`
- Python reference implementation: `reference/python/`
- TypeScript SDK: `sdk/typescript/`

## One-command checks

- `make validate`
- `make test`
- `make conformance`
- `make conformance-ext`

Keywords: agent-to-agent, multi-agent, LLM agents, content-layer protocol, policy enforcement, orchestration, governance, attestations, interoperability standard
