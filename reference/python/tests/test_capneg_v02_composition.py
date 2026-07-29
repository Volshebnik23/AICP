from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref_capneg_v02.profile_composition import (  # noqa: E402
    COMPOSITION_HASH_DOMAIN,
    COMPOSITION_VERSION,
    resolve_profile_composition,
)


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _ref(profile_id: str, version: str = "0.1") -> dict[str, str]:
    return {"profile_id": profile_id, "profile_version": version}


def _composition(*profiles: dict[str, str]) -> dict:
    return {
        "composition_version": COMPOSITION_VERSION,
        "profiles": sorted(
            profiles,
            key=lambda profile: (
                profile["profile_id"],
                profile["profile_version"],
            ),
        ),
    }


def _error_ids(result: dict) -> list[str]:
    return [error["code"] for error in result["errors"]]


def test_generated_registry_covers_every_profile_exactly_once() -> None:
    rules = _load("registry/aicp_profile_composition_rules.json")
    profiles = _load("registry/aicp_profiles.json")
    rule_keys = [
        (
            record["profile"]["profile_id"],
            record["profile"]["profile_version"],
        )
        for record in rules["profiles"]
    ]
    registry_keys = [
        (record["profile_id"], record["profile_version"])
        for record in profiles
    ]
    assert rule_keys == sorted(registry_keys)
    assert len(rule_keys) == len(set(rule_keys)) == 16
    assert rules["composition_hash_domain"] == COMPOSITION_HASH_DOMAIN
    assert rules["supported_core_suites"] == [
        {
            "suite_id": "CT-CORE-0.1",
            "suite_version": "0.1.0-dev",
            "path": "conformance/core/CT_CORE_0.1.json",
        }
    ]


def test_recommended_compositions_resolve_deterministically() -> None:
    recommendations = [
        (_ref("AICP-BASE"),),
        (
            _ref("AICP-MEDIATED-BLOCKING"),
            _ref("AICP-RESUMABLE-SESSIONS"),
        ),
        (
            _ref("AICP-AUTHENTICATED-BASE"),
            _ref("AICP-MEDIATED-BLOCKING"),
        ),
        (
            _ref("AICP-DELEGATED-IDENTITY"),
            _ref("AICP-WORKFLOW-ORCHESTRATION-DELEGATION"),
        ),
        (
            _ref("AICP-AGENT-MEDIA"),
            _ref("AICP-BAZAAR-RECEPTION"),
        ),
    ]
    for profiles in recommendations:
        composition = _composition(*profiles)
        first = resolve_profile_composition(composition)
        second = resolve_profile_composition(copy.deepcopy(composition))
        assert first == second
        assert first["errors"] == []
        assert first["composition_hash"].startswith("sha256:")
        assert first["core_suite"]["suite_id"] == "CT-CORE-0.1"


def test_resolver_rejects_core_redundancy_exclusivity_and_version_conflicts() -> None:
    assert "CAPNEG_CORE_FAMILY_UNSUPPORTED" in _error_ids(
        resolve_profile_composition(
            _composition(_ref("AICP-BASE", "0.2"))
        )
    )
    assert "PROFILE_CORE_VERSION_CONFLICT" in _error_ids(
        resolve_profile_composition(
            _composition(
                _ref("AICP-BASE", "0.2"),
                _ref("AICP-MEDIATED-BLOCKING"),
            )
        )
    )
    assert "PROFILE_COMPOSITION_REDUNDANT" in _error_ids(
        resolve_profile_composition(
            _composition(
                _ref("AICP-BASE"),
                _ref("AICP-MEDIATED-BLOCKING"),
            )
        )
    )
    assert "PROFILE_COMPOSITION_EXCLUSIVE_CONFLICT" in _error_ids(
        resolve_profile_composition(
            _composition(
                _ref("AICP-POLICY-ABAC-RBAC"),
                _ref("AICP-POLICY-LLM-SAFETY"),
            )
        )
    )
    assert "PROFILE_FAMILY_VERSION_CONFLICT" in _error_ids(
        resolve_profile_composition(
            _composition(
                _ref("AICP-BASE"),
                _ref("AICP-BASE", "0.2"),
            )
        )
    )


def test_resolver_never_awards_component_marks() -> None:
    resolved = resolve_profile_composition(
        _composition(
            _ref("AICP-MEDIATED-BLOCKING"),
            _ref("AICP-RESUMABLE-SESSIONS"),
        )
    )
    assert resolved["component_compatibility_marks"] == [
        "AICP-Profile-MEDIATED-BLOCKING-0.1",
        "AICP-Profile-RESUMABLE-SESSIONS-0.1",
    ]
    assert "compatibility_marks" not in resolved
    assert "awarded_marks" not in resolved


def test_public_submission_schema_rejects_unsupported_composition_claim() -> None:
    schema = _load("interop/submissions/submission.schema.json")
    manifest = _load(
        "interop/submissions/examples/single_profile_claim/submission.json"
    )
    manifest["profile_composition"] = _composition(
        _ref("AICP-MEDIATED-BLOCKING"),
        _ref("AICP-RESUMABLE-SESSIONS"),
    )
    manifest["profile_composition_hash"] = "sha256:" + ("A" * 43)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )
    assert errors
    assert any(
        error.validator == "additionalProperties"
        and "profile_composition" in error.message
        and "profile_composition_hash" in error.message
        for error in errors
    )
