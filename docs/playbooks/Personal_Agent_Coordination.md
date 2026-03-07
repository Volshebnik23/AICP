# Playbook: Personal Agent Coordination

## Purpose
Describe a personal agent coordinating external specialist agents/services while keeping governed context and user-policy boundaries.

## Actor map
- Personal agent (primary coordinator)
- External specialist agent(s)
- Optional mediator/relay agent
- User approval/authority source

## What runs where
- Personal context policy and user preferences run in personal-agent domain.
- External specialist interactions run in foreign receptions or relay paths.
- AICP provides portable governed transcript/context semantics across boundaries.

## Recommended AICP profile(s)
- Primary: `AICP-BASE@0.1`
- Upgrade: `AICP-RESUMABLE-SESSIONS@0.1` when continuity/reconnect is critical

## Required / optional extensions
- Required: profile-defined minimum
- Optional: `EXT-RESUME`, `EXT-OBJECT-RESYNC`, `EXT-DELEGATED-IDENTITY`, `EXT-TOOL-GATING`

## Adjacent protocols/services required
- Connectivity/calling layer(s)
- Personal identity/auth stack
- Optional relay/mediation service

## Trust/privacy assumptions
- Minimal context disclosure by default; share only required scoped context.
- Sensitive user context may require redacted forwarding or summary-only portability.

## Out of scope for AICP
- Personal data vault implementation
- Direct discovery/roaming infra implementation
- Consumer identity-wallet internals

## Canonical flow references
- [Session topologies](Session_Topologies.md)
- [AICP canonical flows](../flows/AICP_Canonical_Flows.md)

## Failure/rollback notes
- If direct foreign session access fails, use relay pattern with explicit provenance/evidence references.
- Avoid uncontrolled context replay into new sessions without policy revalidation.
