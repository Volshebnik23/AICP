from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _normalized(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _tree_digest(paths: list[str], *, exclude: set[str] | None = None) -> tuple[int, str]:
    files: set[Path] = set()
    for relative in paths:
        path = ROOT / relative
        if path.is_dir():
            files.update(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and "__pycache__" not in candidate.parts
            )
        else:
            files.add(path)
    excluded = exclude or set()
    files = {
        path for path in files if path.relative_to(ROOT).as_posix() not in excluded
    }
    digest = hashlib.sha256()
    ordered = sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())
    for path in ordered:
        relative = path.relative_to(ROOT).as_posix()
        digest.update(f"{relative}\0".encode("utf-8"))
        digest.update(_normalized(path))
    return len(ordered), digest.hexdigest()


def test_capneg_v01_normative_artifacts_and_fixtures_are_frozen() -> None:
    assert hashlib.sha256(
        _normalized(ROOT / "docs/extensions/RFC_EXT_CAPNEG.md")
    ).hexdigest() == (
        "5634659b8bb4af2cd214da8e1264f8aa521ea20e8b46e5539f42c2f7acb8b356"
    )
    assert _tree_digest(
        ["fixtures/extensions/capneg"],
        exclude={
            "fixtures/extensions/capneg/CN-13_stale_declaration_rollback_expected_fail.jsonl"
        },
    ) == (
        11,
        "84e1bc0dacadbf06f3acd2ffb3e2fb79f3b7f6ec626a3c926419ce5e355da6a5",
    )


def test_core_v02_artifacts_are_frozen_at_merged_m60_bytes() -> None:
    assert _tree_digest(
        [
            "docs/core/AICP_Core_v0.2_Normative.md",
            "schemas/core/aicp-core-contract-v0.2.schema.json",
            "schemas/core/aicp-core-message-v0.2.schema.json",
            "schemas/core/aicp-core-payloads-v0.2.schema.json",
            "conformance/core/CT_CORE_0.2.json",
            "conformance/core_v02_runner",
            "fixtures/core_v0_2",
            "reference/python/aicp_ref_v02",
            "dropins/aicp-core-v0.2",
            "sdk/typescript/src/contract_agreement.js",
            "sdk/typescript/src/contract_agreement.ts",
            "sdk/typescript/test/contract-agreement-v02.test.js",
            "scripts/generate_core_v02_fixtures.py",
        ]
    ) == (
        71,
        "88a58ead87ff42d98ce4f9a022b1bbb008ea4fb7ec15af9cfb4e2f4b6eba2005",
    )


def test_projection_v1_and_product_profile_catalogs_are_frozen() -> None:
    assert _tree_digest(
        [
            "schemas/extensions/ext-object-resync-payloads.schema.json",
            "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json",
            "reference/python/aicp_ref/session_state.py",
            "conformance/runner/_runner_state_projection_checks.py",
            "scripts/generate_session_state_projection_fixtures.py",
            "fixtures/extensions/object_resync/state_projection_v1",
        ]
    ) == (
        17,
        "9268d322b7f02e8b93c8004e1d89f547c73fdbce28d478023607e857f52871f8",
    )
    assert _tree_digest(
        ["registry/aicp_profiles.json", "conformance/profiles"]
    ) == (
        17,
        "7b2a740ee3e9902dfa3b26c6f2d2bca51e5fab455f8be84eeaca8fcaaf9da449",
    )


def test_uat_quickstart_and_default_report_shapes_are_frozen() -> None:
    assert _tree_digest(
        [
            "docs/release/AICP_UAT_Architecture_Freeze.md",
            "docs/release/AICP_UAT_Checklist.md",
            "docs/release/AICP_UAT_Release_Pack.md",
        ]
    ) == (
        3,
        "8f3325b661b6f47f8a365532671dd032010faaac2719dc69f382af2d92b53d41",
    )
    assert _tree_digest(
        [
            "dropins/aicp-core/python/generate_minimal_core_transcript.py",
            "dropins/aicp-core/typescript/scripts/generate_minimal_core_transcript.mjs",
            "dropins/aicp-core-v0.2/python/generate_exact_contract_transcript.py",
            "dropins/aicp-core-v0.2/typescript/scripts/generate_exact_contract_transcript.mjs",
        ]
    ) == (
        4,
        "c51e7d159dab1d4be01b8f731b1aac2052a96e4dc0b84f141c9c2e1513a399c8",
    )
    assert _tree_digest(
        [
            "conformance/conformance_report_schema.json",
            "conformance/conformance_report_v1.schema.json",
            "conformance/profile_report_v1.schema.json",
        ]
    ) == (
        3,
        "1d51243139aef23e8b9dcd93cc5894721d7629564689a543e548eadb34d37a3a",
    )
