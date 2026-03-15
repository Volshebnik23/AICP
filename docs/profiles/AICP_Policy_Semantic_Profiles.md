# AICP Policy Semantic Profiles (Normative)

## 1. Scope and boundary
This document defines optional, transcript-native policy semantic interoperability profiles that build on `EXT-POLICY-EVAL`.

These profiles standardize **decision interpretation**, **registry usage**, and **conformance evidence** so independent vendors can reach the same decision for the same policy bundle and evaluation context.

### 1.1 Non-goals
- This document does **not** define a new policy engine.
- This document does **not** define vendor runtime orchestration glue.
- This document does **not** replace `EXT-ENTERPRISE-BINDINGS`; enterprise bindings remain cross-reference wiring and do not complete M25 policy semantic interoperability.

### 1.2 Shared requirements
All profiles in this document:
- MUST require Core + `EXT-POLICY-EVAL`.
- MUST use registered `policy_languages`, `policy_bindings`, and `policy_reason_codes`.
- MUST demonstrate deterministic same-bundle/same-context interoperability boundaries via conformance fixtures.
- MUST remain externally enforceable from transcript evidence.

"Same policy bundle" means matching `policy_bundle_id`, `version`, `language_id`, and `content_hash` in `policy_bundle_ref`.

## 2. `AICP-POLICY-OPA-REGO@0.1` {#aicp-policy-opa-rego-01}
### Scope
Deterministic OPA/Rego-oriented evaluation semantics over `EXT-POLICY-EVAL` payloads and registries.

### Required extension/suites
- Core: `conformance/core/CT_CORE_0.1.json`
- `EXT-POLICY-EVAL`: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
- Profile semantic suite: `conformance/extensions/PE_PROFILE_OPA_REGO_0.1.json`

### Required registry usage
- `policy_languages.json`: `rego.v1`
- `policy_bindings.json`: `opa.input.v1`
- `policy_reason_codes.json`: registered reason codes only (or namespaced `vendor:` / `org:`)

### Decision semantics
For identical `policy_bundle_ref`, `policy_binding_ref`, and `evaluation_context`, implementations MUST produce the same `policy_decision.decision` and reason-code set.

### Security considerations
Implementations MUST bind policy decisions to `context_hash` and refuse unregistered language/binding IDs for profile badge claims.

## 3. `AICP-POLICY-ABAC-RBAC@0.1` {#aicp-policy-abac-rbac-01}
### Scope
Deterministic ABAC/RBAC policy-dimension interpretation over `subject`, `action`, and `resource` carried by `evaluation_context`.

### Required extension/suites
- Core: `conformance/core/CT_CORE_0.1.json`
- `EXT-POLICY-EVAL`: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
- Profile semantic suite: `conformance/extensions/PE_PROFILE_ABAC_RBAC_0.1.json`

### Required registry usage
- `policy_languages.json`: `abac-rbac.v1`
- `policy_bindings.json`: `abac-rbac.input.v1`
- `policy_reason_codes.json`: include registered scope/access reasons (for example `SCOPE_VIOLATION`, `TOOL_ACCESS_DENIED`)

### Decision semantics
For identical ABAC/RBAC dimensions (`subject`, `action`, `resource`) and same bundle+binding tuple, profile-conformant implementations MUST return the same decision and reason-code set.

### Security considerations
Implementations MUST avoid hidden vendor interpretation layers that alter ABAC/RBAC semantics without transcript evidence.

## 4. `AICP-POLICY-LLM-SAFETY@0.1` {#aicp-policy-llm-safety-01}
### Scope
Minimal deterministic interoperability boundary for LLM-safety policy usage.

### Required extension/suites
- Core: `conformance/core/CT_CORE_0.1.json`
- `EXT-POLICY-EVAL`: `conformance/extensions/PE_POLICY_EVAL_0.1.json`
- Profile semantic suite: `conformance/extensions/PE_PROFILE_LLM_SAFETY_0.1.json`

### Required registry usage
- `policy_languages.json`: `llm-safety-taxonomy.v1`
- `policy_bindings.json`: `llm-safety.evidence.v1`
- `policy_reason_codes.json`: `PROMPT_INJECTION_SUSPECTED`, `LLM_SAFETY_REVIEW_REQUIRED`

### Decision semantics
Classifier/model outputs are evidence, not deterministic truth. For this profile's deterministic boundary, policy results MUST remain transcript-stable and evidence-bound; conformance requires evidence references when the language is `llm-safety-taxonomy.v1`.

### Security considerations
Do not treat probabilistic classifier output as final ground truth without explicit human/secondary gate semantics.

## 5. Registry stability baseline (M25) {#registry-stability-baseline-m25}
For M25 baseline interoperability, canonical profile language/binding entries and profile-level reason codes are promoted to stable with compatibility notes in:
- `registry/policy_languages.json`
- `registry/policy_bindings.json`
- `registry/policy_reason_codes.json`
