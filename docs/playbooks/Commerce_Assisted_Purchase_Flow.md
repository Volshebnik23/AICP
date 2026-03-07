# Playbook: Commerce-Assisted Purchase Flow

## Purpose
Describe product/service guidance conversations where specialist agents assist users, while checkout/payment remain external.

## Actor map
- Buyer/user agent
- Seller/brand reception mediator
- Specialist support agents
- External commerce/checkout systems
- Enforcer/moderation service

## What runs where
- Product selection and governed conversation run in AICP session.
- Tool/API calls query catalog/inventory/eligibility systems.
- Final checkout/payment execution runs in external commerce protocols.

## Recommended AICP profile(s)
- Primary: `AICP-MEDIATED-BLOCKING@0.1`
- Upgrade: `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1` for complex approval chains

## Required / optional extensions
- Required: as profile requires
- Optional: `EXT-TOOL-GATING`, `EXT-DELEGATED-IDENTITY`, `EXT-ENFORCEMENT`, `EXT-ECONOMICS`

## Adjacent protocols/services required
- Commerce API/checkout/payment rails
- Identity/consent systems
- Fraud/risk systems

## Trust/privacy assumptions
- Approval-sensitive actions must be explicitly represented before external side effects.
- Payment credentials and rail-specific security remain external to AICP.

## Out of scope for AICP
- Payment rail implementation
- Settlement/reconciliation internals
- Tax/compliance engine internals

## Canonical flow references
- [AICP canonical flows](../flows/AICP_Canonical_Flows.md)
- [Protocol adapter/gateway](../guides/Protocol_Adapter_Gateway.md)

## Failure/rollback notes
- If checkout fails externally, record failure reason/evidence refs in AICP artifacts.
- Avoid replaying irreversible external actions without idempotency/approval re-check.
