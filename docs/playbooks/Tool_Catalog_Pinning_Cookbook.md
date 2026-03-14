# Tool Catalog Pinning Cookbook (M30 + Tool Gating)

This cookbook shows how to run pinned tool catalogs safely so runtime drift and namespace shadowing do not silently bypass governance.

## Scope

This is an implementation cookbook for artifact manifests + contract pinning + tool gating composition. It is not a vendor package-manager guide.

## Baseline pinned flow

1. Publish canonical artifact manifests (tool/resource/prompt) with issuer-scoped identity and content hash.
2. Include pinned artifact set in contract (`artifact_pinning` extension object).
3. Require `TOOL_CALL_REQUEST.payload.manifest_ref` to match active pins.
4. Enforce tool-gating checks before/after execution according to mode.
5. Reject execution when manifest reference mismatches pinned tuple.

## Controlled upgrade flow (explicit amendment)

1. Build new manifest version and compute hash.
2. Propose contract/context amendment with updated pin tuple.
3. Collect required approvals for upgrade.
4. Activate new pin set only after amendment acceptance.
5. Keep transcript evidence of old and new pins for audit/replay.

## Unexpected manifest drift: failure and recovery

**Scenario**
- Registry now serves changed manifest for same apparent ID.

**Expected behavior**
- Enforcer detects mismatch against pinned `issuer_id`/`version`/`content_hash`.
- Execution is blocked (or marked denied/degraded by policy).
- Operator receives actionable event with mismatch tuple.

**Recovery**
- Investigate whether this is legitimate upgrade or shadowing attack.
- If legitimate, run explicit amendment flow.
- If suspicious, quarantine issuer/source and preserve transcript evidence.

## Anti-shadowing discipline

- Treat `issuer_scoped_id` as mandatory identity boundary.
- Never resolve by plain `manifest_id` only.
- Reject collisions where issuer or hash differs from contract pin.

## Approval linkage (recommended)

For high-risk tool upgrades:
- require M26 human approval for pin-set amendments,
- link upgrade decision to policy-eval reason codes,
- emit observability events for amendment and first execution on new pin.
