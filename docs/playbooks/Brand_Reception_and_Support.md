# Playbook: Brand Reception and Support

## Purpose
Describe a brand-owned hosted reception where external clients/agents join governed sessions for support, presales, and constrained sales conversations.

## Actor map
- Brand mediator/host
- Brand enforcer/moderation service
- Customer agent or client gateway
- Optional specialist agents/tools

## What runs where
- Hosted session control and transcript ownership run on brand infrastructure.
- Policy gating and moderation run in host-owned or delegated enforcement stack.
- Tool/API calls run in external service layer; AICP carries governance/evidence artifacts.

## Recommended AICP profile(s)
- Primary: `AICP-MEDIATED-BLOCKING@0.1`
- Upgrade: `AICP-MEDIATED-BLOCKING-OPS@0.1` for stricter operational controls

## Required / optional extensions
- Required: as defined by selected profile conformance requirements
- Optional: `EXT-ALERTS`, `EXT-SECURITY-ALERT`, `EXT-RESUME`, `EXT-DISPUTES`

## Adjacent protocols/services required
- Calling/connectivity transport
- IAM/auth for customer/operator identity
- Tool/API integration for CRM, ticketing, product systems

## Trust/privacy assumptions
- Host controls moderation policy publication and evidence retention boundaries.
- Customer-facing data handling follows host privacy and retention obligations.

## Out of scope for AICP
- Discovery catalog strategy
- IAM provider internals
- Payment/checkout rails

## Canonical flow references
- [AICP canonical flows](../flows/AICP_Canonical_Flows.md)
- [Session topologies](Session_Topologies.md)

## Failure/rollback notes
- On policy uncertainty, prefer explicit escalation artifacts over silent drops.
- Preserve transcript/evidence continuity on failover and resume paths.
