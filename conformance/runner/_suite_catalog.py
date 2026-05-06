from __future__ import annotations

from typing import Literal

CatalogKind = Literal["core", "extensions", "bindings", "profiles", "demos", "ops", "security"]
CatalogPair = tuple[str, str]


SUITE_CATALOGS: dict[CatalogKind, tuple[CatalogPair, ...]] = {
    "core": (
        ("conformance/core/CT_CORE_0.1.json", "conformance/report.json"),
        ("conformance/core/CT_NUMERIC_GUARDRAILS_0.1.json", "conformance/report_core_numeric_guardrails.json"),
    ),
    "extensions": (
        ("conformance/extensions/CN_CAPNEG_0.1.json", "conformance/report_ext_capneg.json"),
        ("conformance/extensions/CF_CONFIDENTIALITY_0.1.json", "conformance/report_ext_confidentiality.json"),
        ("conformance/extensions/CM_COMMERCE_ACP_PROFILE_0.1.json", "conformance/report_ext_commerce_acp_profile.json"),
        ("conformance/extensions/RD_REDACTION_0.1.json", "conformance/report_ext_redaction.json"),
        ("conformance/extensions/HA_HUMAN_APPROVAL_0.1.json", "conformance/report_ext_human_approval.json"),
        ("conformance/extensions/DS_DISPUTES_0.1.json", "conformance/report_ext_disputes.json"),
        ("conformance/extensions/SA_SECURITY_ALERT_0.1.json", "conformance/report_ext_security_alerts.json"),
        ("conformance/extensions/PA_PARTICIPANTS_0.1.json", "conformance/report_ext_participants.json"),
        ("conformance/extensions/TG_TOOL_GATING_0.1.json", "conformance/report_ext_tool_gating.json"),
        ("conformance/extensions/AM_ARTIFACT_MANIFESTS_PINNING_0.1.json", "conformance/report_ext_artifact_manifests_pinning.json"),
        ("conformance/extensions/ID_IDENTITY_LC_0.1.json", "conformance/report_ext_identity_lc.json"),
        ("conformance/extensions/DL_DELEGATION_0.1.json", "conformance/report_ext_delegation.json"),
        ("conformance/extensions/WF_WORKFLOW_SYNC_0.1.json", "conformance/report_ext_workflow_sync.json"),
        ("conformance/extensions/OR_OBJECT_RESYNC_0.1.json", "conformance/report_ext_object_resync.json"),
        ("conformance/extensions/PE_POLICY_EVAL_0.1.json", "conformance/report_ext_policy_eval.json"),
        ("conformance/extensions/ENF_ENFORCEMENT_0.1.json", "conformance/report_ext_enforcement.json"),
        ("conformance/extensions/AL_ALERTS_0.1.json", "conformance/report_ext_alerts.json"),
        ("conformance/extensions/RS_RESUME_0.1.json", "conformance/report_ext_resume.json"),
        ("conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json", "conformance/report_ext_delegated_identity.json"),
        ("conformance/extensions/IB_IAM_BRIDGE_0.1.json", "conformance/report_ext_iam_bridge.json"),
        ("conformance/extensions/OB_OBSERVABILITY_0.1.json", "conformance/report_ext_observability.json"),
        ("conformance/extensions/EB_ENTERPRISE_BINDINGS_0.1.json", "conformance/report_ext_enterprise_bindings.json"),
        ("conformance/extensions/ET_EXTERNAL_TRANSACTION_0.1.json", "conformance/report_ext_external_transaction.json"),
        ("conformance/extensions/RC_RECEPTION_CHAT_SEMANTICS_0.1.json", "conformance/report_ext_reception_chat_semantics.json"),
        ("conformance/extensions/EC_ECONOMICS_0.1.json", "conformance/report_ext_economics.json"),
        ("conformance/extensions/AD_ADMISSION_0.1.json", "conformance/report_ext_admission.json"),
        ("conformance/extensions/QL_QUEUE_LEASES_0.1.json", "conformance/report_ext_queue_leases.json"),
        ("conformance/extensions/FA_FACILITATION_0.1.json", "conformance/report_ext_facilitation.json"),
        ("conformance/extensions/CH_CHANNELS_0.1.json", "conformance/report_ext_channels.json"),
        ("conformance/extensions/SB_SUBSCRIPTIONS_0.1.json", "conformance/report_ext_subscriptions.json"),
        ("conformance/extensions/PB_PUBLICATIONS_0.1.json", "conformance/report_ext_publications.json"),
        ("conformance/extensions/IB_INBOX_0.1.json", "conformance/report_ext_inbox.json"),
        ("conformance/extensions/MP_MARKETPLACE_0.1.json", "conformance/report_ext_marketplace.json"),
        ("conformance/extensions/PR_PROVENANCE_0.1.json", "conformance/report_ext_provenance.json"),
        ("conformance/extensions/ES_ACTION_ESCROW_0.1.json", "conformance/report_ext_action_escrow.json"),
        ("conformance/extensions/RP_RESPONSIBILITY_0.1.json", "conformance/report_ext_responsibility.json"),
        ("conformance/extensions/TA_TRUST_ATTESTATIONS_0.1.json", "conformance/report_ext_trust_attestations.json"),
        ("conformance/extensions/SC_STATUS_CHANNEL_0.1.json", "conformance/report_ext_status_channel.json"),
        ("conformance/extensions/TW_TRANSCRIPT_WITNESS_0.1.json", "conformance/report_ext_transcript_witness.json"),
        ("conformance/extensions/EX_EXECUTION_LIFECYCLE_0.1.json", "conformance/report_ext_execution_lifecycle.json"),
    ),
    "bindings": (
        ("conformance/bindings/TB_MCP_0.1.json", "conformance/report_bind_mcp.json"),
        ("conformance/bindings/TB_HTTP_WS_0.1.json", "conformance/report_bind_http_ws.json"),
    ),
    "demos": (
        ("conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json", "conformance/report_demo_enforcement_behavioral.json"),
    ),
    "ops": (
        ("conformance/ops/OPS_HARDENING_0.1.json", "conformance/report_ops_hardening.json"),
    ),
    "security": (
        ("conformance/security/SIG_SIGNED_PATHS_0.1.json", "conformance/report_security_signed_path.json"),
    ),
    "profiles": (),
}

PROFILE_CATALOGS: dict[CatalogKind, tuple[CatalogPair, ...]] = {
    "profiles": (
        ("conformance/profiles/PF_AICP_BASE_0.1.json", "conformance/report_profile_base.json"),
        ("conformance/profiles/PF_AICP_MEDIATED_BLOCKING_0.1.json", "conformance/report_profile_mediated_blocking.json"),
        ("conformance/profiles/PF_AICP_MEDIATED_BLOCKING_OPS_0.1.json", "conformance/report_profile_mediated_blocking_ops.json"),
        ("conformance/profiles/PF_AICP_RESUMABLE_SESSIONS_0.1.json", "conformance/report_profile_resumable_sessions.json"),
        ("conformance/profiles/PF_AICP_RECEPTION_CHAT_0.1.json", "conformance/report_profile_reception_chat.json"),
        ("conformance/profiles/PF_AICP_DELEGATED_IDENTITY_0.1.json", "conformance/report_profile_delegated_identity.json"),
        ("conformance/profiles/PF_AICP_WORKFLOW_ORCHESTRATION_DELEGATION_0.1.json", "conformance/report_profile_workflow_orchestration_delegation.json"),
        ("conformance/profiles/PF_AICP_BAZAAR_RECEPTION_0.1.json", "conformance/report_profile_bazaar_reception.json"),
        ("conformance/profiles/PF_AICP_AGENT_MEDIA_0.1.json", "conformance/report_profile_agent_media.json"),
        ("conformance/profiles/PF_AICP_EXECUTION_INTEROP_0.1.json", "conformance/report_profile_execution_interop.json"),
        ("conformance/profiles/PF_AICP_COMMERCE_ACP_0.1.json", "conformance/report_profile_commerce_acp.json"),
        ("conformance/profiles/PF_AICP_POLICY_OPA_REGO_0.1.json", "conformance/report_profile_policy_opa_rego.json"),
        ("conformance/profiles/PF_AICP_POLICY_ABAC_RBAC_0.1.json", "conformance/report_profile_policy_abac_rbac.json"),
        ("conformance/profiles/PF_AICP_POLICY_LLM_SAFETY_0.1.json", "conformance/report_profile_policy_llm_safety.json"),
    ),
    "core": (),
    "extensions": (),
    "bindings": (),
    "demos": (),
    "ops": (),
    "security": (),
}


def catalog_names() -> tuple[CatalogKind, ...]:
    return ("core", "extensions", "bindings", "profiles", "demos", "ops", "security")


def catalog_pairs(name: CatalogKind) -> tuple[tuple[str, tuple[CatalogPair, ...]], tuple[str, tuple[CatalogPair, ...]]]:
    return ("suite", SUITE_CATALOGS[name]), ("profile", PROFILE_CATALOGS[name])
