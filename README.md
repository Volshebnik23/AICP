# AICP — Agent Interaction Content Protocol

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

AICP is a practical, implementable protocol repo for teams building multi-agent platforms.

➡️ **Start here:** [START_HERE_IMPLEMENTERS.md](START_HERE_IMPLEMENTERS.md)
➡️ **30-second standard overview:** [docs/overview/AICP_STANDARD_OVERVIEW.md](docs/overview/AICP_STANDARD_OVERVIEW.md)


## Primary links

- Standard overview: [docs/overview/AICP_STANDARD_OVERVIEW.md](docs/overview/AICP_STANDARD_OVERVIEW.md)
- Compatibility ladder & badges: [docs/adoption/COMPATIBILITY_AND_BADGES.md](docs/adoption/COMPATIBILITY_AND_BADGES.md)
- Start Here: [START_HERE_IMPLEMENTERS.md](START_HERE_IMPLEMENTERS.md)

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
2. Read Core normative behavior: `docs/core/AICP_Core_v0.1_Normative.md`
3. Implement envelope boundary validation against schemas in `schemas/`
4. Validate semantics and invariants with:
   - `make validate`
   - `make conformance`
   - `make conformance-ext`
   - `make conformance-bindings`
5. Reuse helper implementations:
   - Python reference validators/helpers (minimal but invariant-enforcing): `reference/python/`
   - TypeScript SDK hashing/chain helpers: `sdk/typescript/`
6. Use onboarding templates for bootstrap only:
   - TS agent template: `templates/ts-agent/`
   - Protocol adapter template: `templates/protocol-adapter/`

## Core truth stack (canonical boundary)

- **Narrative spec (normative):** `docs/core/AICP_Core_v0.1_Normative.md`
- **Shipped Core baseline:** includes `ERROR` alongside the core message taxonomy and is enforced through core schema/payload/conformance artifacts.
- **Schema boundary validation:** `schemas/core/`
- **Semantic/conformance validation:** `conformance/core/CT_CORE_0.1.json` + runner in `conformance/runner/`
- **Reference helper status:** `reference/python/` is a correctness-first minimal reference layer for implementers, not the protocol authority.

## Canonical layout

- Core normative document (canonical narrative): `docs/core/AICP_Core_v0.1_Normative.md`
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


## Bazaar-scale protocol additions (v88 sprint)
- **EXT-ECONOMICS**: token-agnostic billing proofs for paid message delivery (no payment rails required).
- **Crowd control**: EXT-ADMISSION + EXT-QUEUE-LEASES + EXT-FACILITATION for admission, lease limits, overload/backoff, and turn-taking.
- **Agent-media feeds**: EXT-CHANNELS + EXT-SUBSCRIPTIONS + EXT-PUBLICATIONS + EXT-INBOX.
- **Market collaboration MVP**: EXT-MARKETPLACE + EXT-PROVENANCE + EXT-ACTION-ESCROW scaffolding.


## Maturity and version labels

- **Protocol version** (`aicp_version`): protocol semantics and conformance target (currently `0.1`).
- **Repository/release version** (`VERSION`, release notes tags): repo packaging cadence and shipped artifact set.
- **Roadmap milestone labels** (`Mxx` in `ROADMAP.md`): planning status, not wire-level protocol versioning.

Extension maturity is intentionally mixed in this repo: some components are stable and some are scaffolded/experimental.
Scaffolded extensions remain shipped for implementer iteration; maturity is communicated via docs/registry status, not by deleting surfaces.
