# OAuth Bridge Cookbook (M28 IAM Bridge)

This cookbook explains how to map external OAuth/OIDC/IAM outcomes into AICP transcript evidence safely and auditably.

## Scope

AICP does **not** implement OAuth protocol exchanges. This cookbook covers how to represent IAM outcomes in AICP after external verification completes.

## Recommended mapping pattern

1. **Validate externally**
   - Verify issuer, token validity, signature, expiry, audience, and client binding in your IAM layer.
2. **Project into AICP evidence**
   - Use M28 surfaces (`SUBJECT_BINDING_ISSUE`, `payload.ext.iam_bridge`) to project issuer/scopes/roles/groups/ACR/AMR.
3. **Bind to governed action**
   - For sensitive actions, include explicit `iam_bridge.action` on `TOOL_CALL_REQUEST`.
4. **Require step-up when policy demands**
   - If ACR/AMR are insufficient, require M26 challenge/grant before execution.
5. **Record decision path**
   - Keep policy decision + reason codes + evidence refs transcript-visible.

## ACR/AMR step-up interpretation

A safe baseline:
- define minimum required `acr` per sensitive action class,
- use `amr` as supporting factors (e.g., MFA methods),
- reject or step-up when observed claims are below required assurance.

Example rule:
- `tool.execute_sensitive_approval` requires phishing-resistant MFA (`acr >= org:high`) and human approval grant.

## Delegated identity and authority linkage

When delegation is used:
- include explicit delegation scope and expiry in transcript artifacts,
- link delegated authority to IAM subject binding,
- ensure tool actions validate both delegation and IAM constraints.

## Common implementation pitfalls

- **Pitfall:** relying on transient in-memory IAM context not represented in transcript.
  - **Fix:** project minimal claims/evidence hashes into AICP artifacts.
- **Pitfall:** scope string exists but action binding missing.
  - **Fix:** require `iam_bridge.action` linkage for governed actions.
- **Pitfall:** step-up performed out-of-band without transcript evidence.
  - **Fix:** record challenge/grant or intervention completion linkage.
- **Pitfall:** over-sharing raw token content.
  - **Fix:** record normalized claims/evidence refs, not bearer tokens.

## Minimum transcript evidence checklist

- issuer and subject binding evidence,
- mapped scopes/roles/groups used in decision,
- action-level IAM bridge object on governed tool call,
- policy decision outcome and reason codes,
- step-up/approval evidence where required.
