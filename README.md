# AICP — Agent Interaction Content Protocol

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

AICP is a practical, implementable standard for governed multi-agent conversation/context artifacts.

➡️ **Docs front door:** [docs/INDEX.md](docs/INDEX.md)  
➡️ **Start here:** [START_HERE_IMPLEMENTERS.md](START_HERE_IMPLEMENTERS.md)  
➡️ **Adoption core + tiers:** [docs/architecture/AICP_Adoption_Core_and_Tiers.md](docs/architecture/AICP_Adoption_Core_and_Tiers.md)
➡️ **Interop corpus + claims:** [docs/interop/AICP_Public_Interop_Corpus.md](docs/interop/AICP_Public_Interop_Corpus.md)
➡️ **Interop submission playbook:** [docs/interop/AICP_Interop_Submission_Playbook.md](docs/interop/AICP_Interop_Submission_Playbook.md)  
➡️ **Interop validator + matrix entrypoints:** [interop/README.md](interop/README.md)

## What problem AICP solves

Multi-agent systems often need portable, verifiable conversation/context semantics across vendors and products. AICP provides a shared content-layer model for contracts, policies, attestations, transcript linkage, and enforcement-compatible evidence.

## What AICP standardizes

- Agent-to-agent **content-layer** message/envelope semantics.
- Governed contract/policy/attestation references in transcripts.
- Hash/canonicalization-based verifiable artifacts.
- Conformance/profile model for interoperability targets.
- Enforcement-compatible transcript/evidence semantics.

## What AICP intentionally does not standardize

- Discovery/directory protocols.
- Calling/connectivity/transport protocols.
- Tool execution protocols or tool catalogs.
- IAM provider internals.
- Commerce/payment rails.
- A universal trust fabric.

## Where AICP fits in a multi-protocol stack

AICP sits as the **governed content layer** between transport/connectivity and domain/application behavior. It complements (does not replace) discovery, calling/connectivity, tool integration, IAM, commerce, and trust infrastructure.

See: [docs/architecture/AICP_in_the_Ecosystem.md](docs/architecture/AICP_in_the_Ecosystem.md) and [docs/architecture/AICP_Adoption_Core_and_Tiers.md](docs/architecture/AICP_Adoption_Core_and_Tiers.md).

## Practical adoption patterns

Start with the packaged adoption model in [docs/architecture/AICP_Adoption_Core_and_Tiers.md](docs/architecture/AICP_Adoption_Core_and_Tiers.md), then choose the smallest shipped profile that satisfies your need.

1. **Embed AICP directly in an agent/app**
   - Use drop-ins/templates, then validate against conformance/profile suites.
2. **Use an adapter/gateway in front of an existing system**
   - Preserve audit-critical envelope/evidence fields.
3. **Use AICP as the governed layer for hosted receptions/mediated sessions**
   - Keep moderation and enforcement policy decisions portable and checkable.

See: [docs/guides/Protocol_Adapter_Gateway.md](docs/guides/Protocol_Adapter_Gateway.md), [docs/playbooks/](docs/playbooks/).

## When not to use AICP

- Single-agent local tool orchestration without governed multi-party context.
- Discovery-only or transport-only integration problems.
- Pure payment-rail requirements with no governed conversation/evidence needs.


## Executable truth layers

- Narrative requirements: `docs/core/AICP_Core_v0.1_Normative.md`
- Boundary shape validation: `schemas/core/`
- Stronger semantic/transcript checks: `conformance/` runners and suites
- Reference helpers/SDK/drop-ins: supportive implementer artifacts

## Implementer path

1. Read suite index: `docs/suite/AICP_Suite_Overview_and_Skeleton_v0.1.21_EN.md`
2. Read Core narrative: `docs/core/AICP_Core_v0.1_Normative.md`
3. Validate boundary/schema + conformance:
   - `make validate`
   - `make conformance`
   - `make conformance-ext`
   - `make conformance-bindings`
   - `make conformance-profiles`
   - `make prepr`
4. Reuse helpers:
   - Python reference: `reference/python/`
   - TypeScript SDK: `sdk/typescript/`

## One-command checks

- `make validate`
- `make test`
- `make conformance`
- `make conformance-ext`
- `make conformance-bindings`
- `make conformance-profiles`
- `make template-smoke`
- `make prepr`

## Legal and vendor-adoption quick links

- [LICENSING.md](LICENSING.md)
- [LICENSE](LICENSE)
- [LICENSE-docs](LICENSE-docs)
- [NOTICE](NOTICE)
- [PATENTS.md](PATENTS.md)
- [TRADEMARKS.md](TRADEMARKS.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [DCO](DCO)

## Continue reading

- [docs/INDEX.md](docs/INDEX.md)
- [START_HERE_IMPLEMENTERS.md](START_HERE_IMPLEMENTERS.md)
- [docs/overview/AICP_STANDARD_OVERVIEW.md](docs/overview/AICP_STANDARD_OVERVIEW.md)
- [docs/architecture/AICP_Adoption_Core_and_Tiers.md](docs/architecture/AICP_Adoption_Core_and_Tiers.md)
- [docs/profiles/AICP_Profiles.md](docs/profiles/AICP_Profiles.md)
- [docs/profiles/Profile_Selection_Guide.md](docs/profiles/Profile_Selection_Guide.md)
- [docs/architecture/AICP_in_the_Ecosystem.md](docs/architecture/AICP_in_the_Ecosystem.md)
- [docs/architecture/Enforcement_Models.md](docs/architecture/Enforcement_Models.md)
- [docs/adjacent/A2A_Integration_Pattern.md](docs/adjacent/A2A_Integration_Pattern.md)
- [docs/security/SECURITY_BEST_PRACTICES.md](docs/security/SECURITY_BEST_PRACTICES.md)
- [docs/interop/AICP_Public_Interop_Corpus.md](docs/interop/AICP_Public_Interop_Corpus.md)
- [docs/interop/AICP_Compatibility_Claims_and_Evidence.md](docs/interop/AICP_Compatibility_Claims_and_Evidence.md)
- [docs/interop/AICP_Interop_Submission_Playbook.md](docs/interop/AICP_Interop_Submission_Playbook.md)
