#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "ROADMAP.md"
MAKEFILE = ROOT / "Makefile"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_shipped_milestone(roadmap_text: str, milestone: str) -> bool:
    return f"### ✅ {milestone}" in roadmap_text


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    roadmap = _read(ROADMAP)
    makefile = _read(MAKEFILE)

    failures: list[str] = []

    if _has_shipped_milestone(roadmap, "M23"):
        if "conformance/extensions/CF_CONFIDENTIALITY_0.1.json" not in makefile:
            failures.append("ROADMAP marks M23 shipped, but Makefile conformance-ext does not include CF_CONFIDENTIALITY_0.1")

    if _has_shipped_milestone(roadmap, "M24"):
        if "conformance/extensions/RD_REDACTION_0.1.json" not in makefile:
            failures.append("ROADMAP marks M24 shipped, but Makefile conformance-ext does not include RD_REDACTION_0.1")

    if _has_shipped_milestone(roadmap, "M26"):
        if "conformance/extensions/HA_HUMAN_APPROVAL_0.1.json" not in makefile:
            failures.append("ROADMAP marks M26 shipped, but Makefile conformance-ext does not include HA_HUMAN_APPROVAL_0.1")

    if _has_shipped_milestone(roadmap, "M27"):
        if "conformance/extensions/OB_OBSERVABILITY_0.1.json" not in makefile:
            failures.append("ROADMAP marks M27 shipped, but Makefile conformance-ext does not include OB_OBSERVABILITY_0.1")
        if not (ROOT / "docs/extensions/RFC_EXT_OBSERVABILITY.md").exists():
            failures.append("ROADMAP marks M27 shipped, but docs/extensions/RFC_EXT_OBSERVABILITY.md is missing")
        if not (ROOT / "schemas/extensions/ext-observability-payloads.schema.json").exists():
            failures.append("ROADMAP marks M27 shipped, but schemas/extensions/ext-observability-payloads.schema.json is missing")
        if not (ROOT / "conformance/extensions/OB_OBSERVABILITY_0.1.json").exists():
            failures.append("ROADMAP marks M27 shipped, but conformance/extensions/OB_OBSERVABILITY_0.1.json is missing")
        if not (ROOT / "scripts/generate_observability_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/observability").glob("*.jsonl")):
            failures.append("ROADMAP marks M27 shipped, but no fixture generator or deterministic fixtures for observability are present")

    if _has_shipped_milestone(roadmap, "M29"):
        if "conformance/extensions/EB_ENTERPRISE_BINDINGS_0.1.json" not in makefile:
            failures.append("ROADMAP marks M29 shipped, but Makefile conformance-ext does not include EB_ENTERPRISE_BINDINGS_0.1")
        if not (ROOT / "docs/extensions/RFC_EXT_ENTERPRISE_BINDINGS.md").exists():
            failures.append("ROADMAP marks M29 shipped, but docs/extensions/RFC_EXT_ENTERPRISE_BINDINGS.md is missing")
        if not (ROOT / "schemas/extensions/ext-enterprise-bindings-payloads.schema.json").exists():
            failures.append("ROADMAP marks M29 shipped, but schemas/extensions/ext-enterprise-bindings-payloads.schema.json is missing")
        if not (ROOT / "conformance/extensions/EB_ENTERPRISE_BINDINGS_0.1.json").exists():
            failures.append("ROADMAP marks M29 shipped, but conformance/extensions/EB_ENTERPRISE_BINDINGS_0.1.json is missing")
        if not (ROOT / "scripts/generate_enterprise_bindings_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/enterprise_bindings").glob("*.jsonl")):
            failures.append("ROADMAP marks M29 shipped, but no fixture generator or deterministic fixtures for enterprise bindings are present")


    if _has_shipped_milestone(roadmap, "M35"):
        if "conformance/extensions/AD_ADMISSION_0.1.json" not in makefile:
            failures.append("ROADMAP marks M35 shipped, but Makefile conformance-ext does not include AD_ADMISSION_0.1")
        if "conformance/extensions/QL_QUEUE_LEASES_0.1.json" not in makefile:
            failures.append("ROADMAP marks M35 shipped, but Makefile conformance-ext does not include QL_QUEUE_LEASES_0.1")
        if not (ROOT / "docs/extensions/RFC_EXT_ADMISSION.md").exists():
            failures.append("ROADMAP marks M35 shipped, but docs/extensions/RFC_EXT_ADMISSION.md is missing")
        if not (ROOT / "docs/extensions/RFC_EXT_QUEUE_LEASES.md").exists():
            failures.append("ROADMAP marks M35 shipped, but docs/extensions/RFC_EXT_QUEUE_LEASES.md is missing")
        if not (ROOT / "schemas/extensions/ext-admission-payloads.schema.json").exists():
            failures.append("ROADMAP marks M35 shipped, but schemas/extensions/ext-admission-payloads.schema.json is missing")
        if not (ROOT / "schemas/extensions/ext-queue-leases-payloads.schema.json").exists():
            failures.append("ROADMAP marks M35 shipped, but schemas/extensions/ext-queue-leases-payloads.schema.json is missing")
        if not (ROOT / "conformance/extensions/AD_ADMISSION_0.1.json").exists():
            failures.append("ROADMAP marks M35 shipped, but conformance/extensions/AD_ADMISSION_0.1.json is missing")
        if not (ROOT / "conformance/extensions/QL_QUEUE_LEASES_0.1.json").exists():
            failures.append("ROADMAP marks M35 shipped, but conformance/extensions/QL_QUEUE_LEASES_0.1.json is missing")
        if not (ROOT / "scripts/generate_admission_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/admission").glob("*.jsonl")):
            failures.append("ROADMAP marks M35 shipped, but no fixture generator or deterministic admission fixtures are present")
        if not (ROOT / "scripts/generate_queue_leases_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/queue_leases").glob("*.jsonl")):
            failures.append("ROADMAP marks M35 shipped, but no fixture generator or deterministic queue-lease fixtures are present")

        # minimum behavioral coverage guardrails for shipped M35
        ad_suite_path = ROOT / "conformance/extensions/AD_ADMISSION_0.1.json"
        ql_suite_path = ROOT / "conformance/extensions/QL_QUEUE_LEASES_0.1.json"
        if ad_suite_path.exists():
            ad_suite = _load_json(ad_suite_path)
            ad_transcripts = ad_suite.get("transcripts", []) if isinstance(ad_suite, dict) else []
            ad_payload_map = ad_suite.get("payload_schema_map", {}) if isinstance(ad_suite, dict) else {}
            ad_types = set(ad_payload_map.keys()) if isinstance(ad_payload_map, dict) else set()
            if "ADMISSION_REJECT" not in ad_types:
                failures.append("ROADMAP marks M35 shipped, but AD_ADMISSION_0.1 payload_schema_map is missing ADMISSION_REJECT")
            if "ADMISSION_REVOKE" not in ad_types:
                failures.append("ROADMAP marks M35 shipped, but AD_ADMISSION_0.1 payload_schema_map is missing ADMISSION_REVOKE")
            if not any(isinstance(t, dict) and t.get("expect_pass") is False for t in ad_transcripts):
                failures.append("ROADMAP marks M35 shipped, but AD_ADMISSION_0.1 has no expected-fail transcript")

        if ql_suite_path.exists():
            ql_suite = _load_json(ql_suite_path)
            ql_transcripts = ql_suite.get("transcripts", []) if isinstance(ql_suite, dict) else []
            if not any(isinstance(t, dict) and t.get("expect_pass") is False for t in ql_transcripts):
                failures.append("ROADMAP marks M35 shipped, but QL_QUEUE_LEASES_0.1 has no expected-fail transcript")

    if _has_shipped_milestone(roadmap, "M36"):
        if "conformance/extensions/MP_MARKETPLACE_0.1.json" not in makefile:
            failures.append("ROADMAP marks M36 shipped, but Makefile conformance-ext does not include MP_MARKETPLACE_0.1")
        if not (ROOT / "docs/extensions/RFC_EXT_MARKETPLACE.md").exists():
            failures.append("ROADMAP marks M36 shipped, but docs/extensions/RFC_EXT_MARKETPLACE.md is missing")
        if not (ROOT / "schemas/extensions/ext-marketplace-payloads.schema.json").exists():
            failures.append("ROADMAP marks M36 shipped, but schemas/extensions/ext-marketplace-payloads.schema.json is missing")
        mp_suite_path = ROOT / "conformance/extensions/MP_MARKETPLACE_0.1.json"
        if not mp_suite_path.exists():
            failures.append("ROADMAP marks M36 shipped, but conformance/extensions/MP_MARKETPLACE_0.1.json is missing")
        if not (ROOT / "scripts/generate_marketplace_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/marketplace").glob("*.jsonl")):
            failures.append("ROADMAP marks M36 shipped, but no fixture generator or deterministic marketplace fixtures are present")

        if mp_suite_path.exists():
            mp_suite = _load_json(mp_suite_path)
            mp_transcripts = mp_suite.get("transcripts", []) if isinstance(mp_suite, dict) else []
            mp_payload_map = mp_suite.get("payload_schema_map", {}) if isinstance(mp_suite, dict) else {}
            mp_types = set(mp_payload_map.keys()) if isinstance(mp_payload_map, dict) else set()
            marketplace_checks = {c.get("test_id") for c in mp_suite.get("checks", []) if isinstance(c, dict)} if isinstance(mp_suite, dict) else set()
            message_registry_path = ROOT / "registry/message_types.json"
            message_registry = _load_json(message_registry_path) if message_registry_path.exists() else []
            registry_types = {
                entry.get("id")
                for entry in message_registry
                if isinstance(entry, dict) and entry.get("type") == "message_types" and isinstance(entry.get("id"), str)
            }
            mp_expected_failure_ids = {
                f.get("test_id")
                for t in mp_transcripts
                if isinstance(t, dict) and t.get("expect_pass") is False
                for f in t.get("expected_failures", [])
                if isinstance(f, dict)
            }

            canonical_m36_types = {
                "RFW_POST",
                "BID_SUBMIT",
                "BID_UPDATE",
                "BID_WITHDRAW",
                "AWARD_ISSUE",
                "AWARD_ACCEPT",
                "AWARD_DECLINE",
                "AUCTION_OPEN",
                "AUCTION_CLOSE",
                "BLACKBOARD_DECLARE",
                "BLACKBOARD_POST",
                "BLACKBOARD_UPDATE",
                "BLACKBOARD_REMOVE",
                "SUBCHAT_CREATE",
                "SUBCHAT_INVITE",
                "SUBCHAT_JOIN",
                "ROUTING_DECISION_ATTEST",
            }
            legacy_m36_types = {"RFW_DECLARE", "AWARD", "WORK_ORDER_DECLARE", "WORK_ORDER_UPDATE"}

            if len(mp_transcripts) < 2:
                failures.append("ROADMAP marks M36 shipped, but MP_MARKETPLACE_0.1 must include more than one transcript")
            if not any(isinstance(t, dict) and t.get("expect_pass") is False for t in mp_transcripts):
                failures.append("ROADMAP marks M36 shipped, but MP_MARKETPLACE_0.1 has no expected-fail transcript")
            if not canonical_m36_types.issubset(mp_types):
                missing = sorted(canonical_m36_types - mp_types)
                failures.append(f"ROADMAP marks M36 shipped, but MP_MARKETPLACE_0.1 payload_schema_map misses canonical types: {', '.join(missing)}")
            if legacy_m36_types & mp_types:
                present_legacy = sorted(legacy_m36_types & mp_types)
                failures.append(f"ROADMAP marks M36 shipped, but MP_MARKETPLACE_0.1 still includes legacy marketplace types: {', '.join(present_legacy)}")
            if not canonical_m36_types.issubset(registry_types):
                missing_registry = sorted(canonical_m36_types - registry_types)
                failures.append(f"ROADMAP marks M36 shipped, but registry/message_types.json misses canonical marketplace types: {', '.join(missing_registry)}")
            if legacy_m36_types & registry_types:
                present_legacy_registry = sorted(legacy_m36_types & registry_types)
                failures.append(f"ROADMAP marks M36 shipped, but registry/message_types.json still includes legacy marketplace types: {', '.join(present_legacy_registry)}")

            required_semantic_checks = {"MP-RFW-01", "MP-BID-01", "MP-AWARD-01", "MP-AUCTION-01", "MP-BLACKBOARD-01", "MP-SUBCHAT-01", "MP-ADMISSION-LINK-01"}
            if not required_semantic_checks.issubset(marketplace_checks):
                missing_checks = sorted(required_semantic_checks - marketplace_checks)
                failures.append(f"ROADMAP marks M36 shipped, but MP_MARKETPLACE_0.1 is missing marketplace semantic checks: {', '.join(missing_checks)}")
            if "MP-AWARD-01" not in mp_expected_failure_ids:
                failures.append("ROADMAP marks M36 shipped, but MP_MARKETPLACE_0.1 has no expected-fail transcript asserting MP-AWARD-01")

    if _has_shipped_milestone(roadmap, "M37"):
        if "conformance/extensions/PR_PROVENANCE_0.1.json" not in makefile:
            failures.append("ROADMAP marks M37 shipped, but Makefile conformance-ext does not include PR_PROVENANCE_0.1")
        if "conformance/extensions/ES_ACTION_ESCROW_0.1.json" not in makefile:
            failures.append("ROADMAP marks M37 shipped, but Makefile conformance-ext does not include ES_ACTION_ESCROW_0.1")
        if "conformance/extensions/RP_RESPONSIBILITY_0.1.json" not in makefile:
            failures.append("ROADMAP marks M37 shipped, but Makefile conformance-ext does not include RP_RESPONSIBILITY_0.1")
        if not (ROOT / "docs/extensions/RFC_EXT_PROVENANCE.md").exists():
            failures.append("ROADMAP marks M37 shipped, but docs/extensions/RFC_EXT_PROVENANCE.md is missing")
        if not (ROOT / "docs/extensions/RFC_EXT_ACTION_ESCROW.md").exists():
            failures.append("ROADMAP marks M37 shipped, but docs/extensions/RFC_EXT_ACTION_ESCROW.md is missing")
        if not (ROOT / "docs/extensions/RFC_EXT_RESPONSIBILITY.md").exists():
            failures.append("ROADMAP marks M37 shipped, but docs/extensions/RFC_EXT_RESPONSIBILITY.md is missing")
        if not (ROOT / "schemas/extensions/ext-provenance-payloads.schema.json").exists():
            failures.append("ROADMAP marks M37 shipped, but schemas/extensions/ext-provenance-payloads.schema.json is missing")
        if not (ROOT / "schemas/extensions/ext-action-escrow-payloads.schema.json").exists():
            failures.append("ROADMAP marks M37 shipped, but schemas/extensions/ext-action-escrow-payloads.schema.json is missing")
        if not (ROOT / "schemas/extensions/ext-responsibility-payloads.schema.json").exists():
            failures.append("ROADMAP marks M37 shipped, but schemas/extensions/ext-responsibility-payloads.schema.json is missing")
        if not (ROOT / "scripts/generate_provenance_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/provenance").glob("*.jsonl")):
            failures.append("ROADMAP marks M37 shipped, but no provenance fixture generator or deterministic fixtures are present")
        if not (ROOT / "scripts/generate_action_escrow_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/action_escrow").glob("*.jsonl")):
            failures.append("ROADMAP marks M37 shipped, but no action-escrow fixture generator or deterministic fixtures are present")
        if not (ROOT / "scripts/generate_responsibility_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/responsibility").glob("*.jsonl")):
            failures.append("ROADMAP marks M37 shipped, but no responsibility fixture generator or deterministic fixtures are present")

        pr_suite_path = ROOT / "conformance/extensions/PR_PROVENANCE_0.1.json"
        es_suite_path = ROOT / "conformance/extensions/ES_ACTION_ESCROW_0.1.json"
        rp_suite_path = ROOT / "conformance/extensions/RP_RESPONSIBILITY_0.1.json"

        if pr_suite_path.exists():
            pr_suite = _load_json(pr_suite_path)
            pr_transcripts = pr_suite.get("transcripts", []) if isinstance(pr_suite, dict) else []
            if not any(isinstance(t, dict) and t.get("expect_pass") is False for t in pr_transcripts):
                failures.append("ROADMAP marks M37 shipped, but PR_PROVENANCE_0.1 has no expected-fail transcript")

        if es_suite_path.exists():
            es_suite = _load_json(es_suite_path)
            es_transcripts = es_suite.get("transcripts", []) if isinstance(es_suite, dict) else []
            if not any(isinstance(t, dict) and t.get("expect_pass") is False for t in es_transcripts):
                failures.append("ROADMAP marks M37 shipped, but ES_ACTION_ESCROW_0.1 has no expected-fail transcript")

        if rp_suite_path.exists():
            rp_suite = _load_json(rp_suite_path)
            rp_transcripts = rp_suite.get("transcripts", []) if isinstance(rp_suite, dict) else []
            if not any(isinstance(t, dict) and t.get("expect_pass") is False for t in rp_transcripts):
                failures.append("ROADMAP marks M37 shipped, but RP_RESPONSIBILITY_0.1 has no expected-fail transcript")


    if _has_shipped_milestone(roadmap, "M38"):
        required_make = {
            "conformance/extensions/CH_CHANNELS_0.1.json": "CH_CHANNELS_0.1",
            "conformance/extensions/SB_SUBSCRIPTIONS_0.1.json": "SB_SUBSCRIPTIONS_0.1",
            "conformance/extensions/PB_PUBLICATIONS_0.1.json": "PB_PUBLICATIONS_0.1",
            "conformance/extensions/IB_INBOX_0.1.json": "IB_INBOX_0.1",
        }
        for suite_path, label in required_make.items():
            if suite_path not in makefile:
                failures.append(f"ROADMAP marks M38 shipped, but Makefile conformance-ext does not include {label}")

        required_docs = [
            ROOT / "docs/extensions/RFC_EXT_CHANNELS.md",
            ROOT / "docs/extensions/RFC_EXT_SUBSCRIPTIONS.md",
            ROOT / "docs/extensions/RFC_EXT_PUBLICATIONS.md",
            ROOT / "docs/extensions/RFC_EXT_INBOX.md",
        ]
        for path in required_docs:
            if not path.exists():
                failures.append(f"ROADMAP marks M38 shipped, but {path.relative_to(ROOT)} is missing")

        required_schemas = [
            ROOT / "schemas/extensions/ext-channels-payloads.schema.json",
            ROOT / "schemas/extensions/ext-subscriptions-payloads.schema.json",
            ROOT / "schemas/extensions/ext-publications-payloads.schema.json",
            ROOT / "schemas/extensions/ext-inbox-payloads.schema.json",
        ]
        for path in required_schemas:
            if not path.exists():
                failures.append(f"ROADMAP marks M38 shipped, but {path.relative_to(ROOT)} is missing")

        suite_specs = [
            (ROOT / "conformance/extensions/CH_CHANNELS_0.1.json", "CH-CHANNELS", {"CH-HIER-01", "CH-LIFECYCLE-01"}),
            (ROOT / "conformance/extensions/SB_SUBSCRIPTIONS_0.1.json", "SB-SUBSCRIPTIONS", {"SB-STATE-01", "SB-CURSOR-01"}),
            (ROOT / "conformance/extensions/PB_PUBLICATIONS_0.1.json", "PB-PUBLICATIONS", {"PB-LIFECYCLE-01", "PB-REASON-01", "PB-DELIVERY-01"}),
            (ROOT / "conformance/extensions/IB_INBOX_0.1.json", "IB-INBOX", {"IB-LINK-01", "IB-LEASE-01"}),
        ]

        for suite_path, label, required_checks in suite_specs:
            if not suite_path.exists():
                failures.append(f"ROADMAP marks M38 shipped, but {suite_path.relative_to(ROOT)} is missing")
                continue
            suite = _load_json(suite_path)
            transcripts = suite.get("transcripts", []) if isinstance(suite, dict) else []
            checks = {c.get("test_id") for c in suite.get("checks", []) if isinstance(c, dict)} if isinstance(suite, dict) else set()
            if not any(isinstance(t, dict) and t.get("expect_pass") is False for t in transcripts):
                failures.append(f"ROADMAP marks M38 shipped, but {label} has no expected-fail transcript")
            if not required_checks.issubset(checks):
                missing_checks = sorted(required_checks - checks)
                failures.append(f"ROADMAP marks M38 shipped, but {label} is missing semantic checks: {', '.join(missing_checks)}")

        generators_or_fixtures = [
            (ROOT / "scripts/generate_channels_fixtures.py", ROOT / "fixtures/extensions/channels"),
            (ROOT / "scripts/generate_subscriptions_fixtures.py", ROOT / "fixtures/extensions/subscriptions"),
            (ROOT / "scripts/generate_publications_fixtures.py", ROOT / "fixtures/extensions/publications"),
            (ROOT / "scripts/generate_inbox_fixtures.py", ROOT / "fixtures/extensions/inbox"),
        ]
        for script_path, fixture_dir in generators_or_fixtures:
            if not script_path.exists() and not any(fixture_dir.glob("*.jsonl")):
                failures.append(f"ROADMAP marks M38 shipped, but no generator or fixtures found for {fixture_dir.relative_to(ROOT)}")


    if _has_shipped_milestone(roadmap, "M31"):
        if "conformance/extensions/TW_TRANSCRIPT_WITNESS_0.1.json" not in makefile:
            failures.append("ROADMAP marks M31 shipped, but Makefile conformance-ext does not include TW_TRANSCRIPT_WITNESS_0.1")
        required = [
            ROOT / "docs/extensions/RFC_EXT_TRANSCRIPT_WITNESS.md",
            ROOT / "schemas/extensions/ext-transcript-witness-payloads.schema.json",
            ROOT / "conformance/extensions/TW_TRANSCRIPT_WITNESS_0.1.json",
        ]
        for path in required:
            if not path.exists():
                failures.append(f"ROADMAP marks M31 shipped, but {path.relative_to(ROOT)} is missing")
        if not (ROOT / "scripts/generate_transcript_witness_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/transcript_witness").glob("*.jsonl")):
            failures.append("ROADMAP marks M31 shipped, but no transcript witness fixture generator or deterministic fixtures are present")

        tw_suite_path = ROOT / "conformance/extensions/TW_TRANSCRIPT_WITNESS_0.1.json"
        if tw_suite_path.exists():
            tw_suite = _load_json(tw_suite_path)
            tw_transcripts = tw_suite.get("transcripts", []) if isinstance(tw_suite, dict) else []
            tw_checks = {c.get("test_id") for c in tw_suite.get("checks", []) if isinstance(c, dict)} if isinstance(tw_suite, dict) else set()
            if not any(isinstance(t, dict) and t.get("expect_pass") is False for t in tw_transcripts):
                failures.append("ROADMAP marks M31 shipped, but TW_TRANSCRIPT_WITNESS_0.1 has no expected-fail transcript")
            required_tw_checks = {"TW-CHECKPOINT-01", "TW-RECEIPT-01", "TW-HEAD-01", "TW-INCLUSION-01", "TW-EQUIVOCATION-01"}
            if not required_tw_checks.issubset(tw_checks):
                missing = sorted(required_tw_checks - tw_checks)
                failures.append(f"ROADMAP marks M31 shipped, but TW_TRANSCRIPT_WITNESS_0.1 is missing semantic checks: {', '.join(missing)}")

    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        print("Fix roadmap/Makefile mismatch before claiming shipped milestone coverage.")
        return 1

    print("OK: shipped milestone claims align with conformance-ext suite coverage in Makefile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
