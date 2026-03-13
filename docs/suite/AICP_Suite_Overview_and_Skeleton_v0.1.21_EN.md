# AICP — Agent Interaction Content Protocol

> An open content-layer protocol for agent-to-agent interaction with enforceable policies.

**Suite overview and v0.1 specification skeleton** (RFC frame + Core + Registered Extensions).

- Version: `0.1.21` (English master)
- Status: Draft
- Suite doc audit note: This overview is repo-backed and was last audited in-repo.

## Canonical sources

- Core normative source: `docs/core/AICP_Core_v0.1_Normative.md`
- Profiles: `docs/profiles/AICP_Profiles.md`
- Personas/profile rationale: `docs/profiles/AICP_Personas_Stories_Features_Profiles.md`
- Canonical flows: `docs/flows/AICP_Canonical_Flows.md`
- Roadmap/status: `ROADMAP.md`

## Contents

1. [Protocol positioning](#1-protocol-positioning)
2. [RFC frame summary](#2-rfc-frame-summary)
3. [Core model summary](#3-core-model-summary)
4. [Conformance model](#4-conformance-model)
5. [Registered extensions (repo-backed)](#5-registered-extensions-repo-backed)
6. [Policy categories (registry-backed)](#6-policy-categories-registry-backed)
7. [Profiles (repo-backed)](#7-profiles-repo-backed)
8. [Bindings](#8-bindings)
9. [Future / non-registered ideas](#9-future--non-registered-ideas)

## 1. Protocol positioning

AICP primarily targets:

- **L3 content contract semantics** (goals, roles, context/versioning, conflict handling), and
- **L4 policy/attestation interoperability** (machine-checkable evidence and enforcement signals).

AICP is transport-agnostic and domain-agnostic. Transport/runtime bindings are separate artifacts.

## 2. RFC frame summary

For complete normative text, use canonical docs under `docs/core/`, `docs/extensions/`, `docs/bindings/`, and `docs/rfc/`.

This suite overview is an index/skeleton, not a replacement for those canonical artifacts.

## 3. Core model summary

Core message and contract semantics are defined in:

- `docs/core/AICP_Core_v0.1_Normative.md`
- `schemas/core/`
- `fixtures/golden_transcripts/`
- `conformance/core/CT_CORE_0.1.json`

## 4. Conformance model

Conformance is executable and repo-backed:

- Runner: `conformance/runner/aicp_conformance_runner.py`
- Suite catalog: `conformance/`
- Profile runner: `conformance/runner/aicp_profile_runner.py`
- One-command workflows: `make validate`, `make conformance-all`, `make conformance-profiles`

## 5. Registered extensions (repo-backed)

Registered extension IDs are authoritative in `registry/extension_ids.json`.

- `EXT-CAPNEG` — `docs/extensions/RFC_EXT_CAPNEG.md`
- `EXT-CONFIDENTIALITY` — `docs/extensions/RFC_EXT_CONFIDENTIALITY.md`
- `EXT-POLICY-EVAL` — `docs/extensions/RFC_EXT_POLICY_EVAL.md`
- `EXT-OBJECT-RESYNC` — `docs/extensions/RFC_EXT_OBJECT_RESYNC.md`
- `EXT-IDENTITY-LC` — `docs/extensions/RFC_EXT_IDENTITY_LIFECYCLE.md`
- `EXT-WORKFLOW-SYNC` — `docs/extensions/RFC_EXT_WORKFLOW_SYNC.md`
- `EXT-DELEGATION` — `docs/extensions/RFC_EXT_DELEGATION.md`
- `EXT-DELEGATED-IDENTITY` — `docs/extensions/RFC_EXT_DELEGATED_IDENTITY.md`
- `EXT-DISPUTES` — `docs/extensions/RFC_EXT_DISPUTES.md`
- `EXT-SECURITY-ALERT` — `docs/extensions/RFC_EXT_SECURITY_ALERTS.md`
- `EXT-ENFORCEMENT` — `docs/extensions/RFC_EXT_ENFORCEMENT.md`
- `EXT-ALERTS` — `docs/extensions/RFC_EXT_ALERTS.md`
- `EXT-RESUME` — `docs/extensions/RFC_EXT_RESUME.md`
- `EXT-REDACTION` — `docs/extensions/RFC_EXT_REDACTION.md`
- `EXT-HUMAN-APPROVAL` — `docs/extensions/RFC_EXT_HUMAN_APPROVAL.md`
- `EXT-PARTICIPANTS` — `docs/extensions/RFC_EXT_PARTICIPANTS.md`
- `EXT-TOOL-GATING` — `docs/extensions/RFC_EXT_TOOL_GATING.md`

## 6. Policy categories (registry-backed)

Policy category IDs are authoritative in `registry/policy_categories.json`.

Current set (9):

- `agent_authority`
- `user_consent`
- `scope_boundaries` (deprecated; retained for compatibility)
- `user_consent_auth`
- `scope`
- `boundaries`
- `tool_access`
- `pii_handling`
- `auditability`

## 7. Profiles (repo-backed)

Profile definitions and status are authoritative in:

- `docs/profiles/AICP_Profiles.md`
- `registry/aicp_profiles.json`
- `conformance/profiles/`

Currently available profile IDs include:

- `AICP-BASE@0.1`
- `AICP-MEDIATED-BLOCKING@0.1`
- `AICP-MEDIATED-BLOCKING-OPS@0.1`
- `AICP-RESUMABLE-SESSIONS@0.1`
- `AICP-RECEPTION-CHAT@0.1`
- `AICP-DELEGATED-IDENTITY@0.1`
- `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1`

## 8. Bindings

Bindings are not extension IDs. Binding RFCs live under `docs/bindings/`:

- `docs/bindings/RFC_BIND_MCP.md`
- `docs/bindings/RFC_BIND_HTTP_WS.md`
- `docs/bindings/RFC_BIND_MESSAGE_BUS.md`

## 9. Future / non-registered ideas

Items sometimes discussed as potential future work (for example tracing/QoS/artifact-oriented conventions) are **not registered extensions** unless they appear in `registry/extension_ids.json`.

Do not treat unregistered ideas as conformance targets or compatibility claims.


## Added extension suites (v90)
- `conformance/extensions/RD_REDACTION_0.1.json`
- `conformance/extensions/CF_CONFIDENTIALITY_0.1.json`
- `conformance/extensions/HA_HUMAN_APPROVAL_0.1.json`
- `conformance/extensions/EC_ECONOMICS_0.1.json`
- `conformance/extensions/AD_ADMISSION_0.1.json`
- `conformance/extensions/QL_QUEUE_LEASES_0.1.json`
- `conformance/extensions/FA_FACILITATION_0.1.json`
- `conformance/extensions/CH_CHANNELS_0.1.json`
- `conformance/extensions/SB_SUBSCRIPTIONS_0.1.json`
- `conformance/extensions/PB_PUBLICATIONS_0.1.json`
- `conformance/extensions/IB_INBOX_0.1.json`
- `conformance/extensions/MK_MARKETPLACE_0.1.json`
- `conformance/extensions/PR_PROVENANCE_0.1.json`
- `conformance/extensions/ES_ACTION_ESCROW_0.1.json`
