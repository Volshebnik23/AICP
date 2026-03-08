# Playbook: Enterprise Orchestration

## Purpose
Describe governed multi-agent collaboration across enterprise teams/systems, including policy-sensitive tool usage and approval-gated actions.

## Actor map
- Enterprise mediator/orchestrator
- Domain specialist agents
- Human approvers / governance roles
- Enforcer service(s)
- External enterprise APIs

## What runs where
- Session coordination runs in enterprise host/orchestration layer.
- Tool routing and execution remain in integration/runtime infrastructure.
- AICP transcript captures governed context, contracts, policies, and attestations.

## Recommended AICP profile(s)
- Primary: `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1`
- Complementary: `AICP-DELEGATED-IDENTITY@0.1` where delegated authority is central

## Required / optional extensions
- Required: per selected profile(s)
- Optional: `EXT-TOOL-GATING`, `EXT-POLICY-EVAL`, `EXT-DISPUTES`, `EXT-RESUME`

## Adjacent protocols/services required
- Enterprise IAM and delegated auth systems
- Policy evaluation engines
- Workflow runtime/orchestration platform
- Auditing/SIEM pipelines

## Trust/privacy assumptions
- Strong data minimization and compartmentalization are required.
- Evidence references must be sufficient for internal/external audit.

## Out of scope for AICP
- Internal workflow engine implementation
- IAM policy model internals
- Tool runtime sandboxing internals

## Canonical flow references
- [AICP canonical flows](../flows/AICP_Canonical_Flows.md)
- [Enforcement models](../architecture/Enforcement_Models.md)

## Failure/rollback notes
- On partial failures, emit explicit state/update artifacts rather than implicit retries only.
- Keep replay-safe recovery for resumed sessions and delegated actions.
