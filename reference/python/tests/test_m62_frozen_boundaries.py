from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _normalized(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _tree_digest(paths: list[str]) -> tuple[int, str]:
    files: set[Path] = set()
    for relative in paths:
        path = ROOT / relative
        if path.is_dir():
            files.update(
                item
                for item in path.rglob("*")
                if item.is_file() and "__pycache__" not in item.parts
            )
        else:
            files.add(path)
    digest = hashlib.sha256()
    ordered = sorted(
        files,
        key=lambda item: item.relative_to(ROOT).as_posix(),
    )
    for path in ordered:
        digest.update(
            (
                path.relative_to(ROOT).as_posix() + "\0"
            ).encode("utf-8")
        )
        digest.update(_normalized(path))
    return len(ordered), digest.hexdigest()


def test_existing_profile_iut_v1_family_is_frozen() -> None:
    assert _tree_digest(
        [
            "conformance/iut/_iut_evaluator.py",
            "conformance/iut/adapter_protocol.schema.json",
            "conformance/iut/aicp_iut_catalog.py",
            "conformance/iut/aicp_iut_runner.py",
            "conformance/iut/cases.json",
            "conformance/iut/iut_report_v1.schema.json",
            "conformance/iut/reference_adapter.py",
            "conformance/iut/tck_releases.json",
        ]
    ) == (
        8,
        "7c5b97397f4de91dc43d7b978fd2dad2e98f58260a916a8ca111a78eb9ab4fc1",
    )


def test_core_v01_semantic_surface_is_frozen() -> None:
    assert _tree_digest(
        [
            "docs/core/AICP_Core_v0.1_Normative.md",
            "schemas/core/aicp-core-message.schema.json",
            "schemas/core/aicp-core-contract.schema.json",
            "schemas/core/aicp-core-payloads.schema.json",
            "conformance/core/CT_CORE_0.1.json",
            "fixtures/core_tv.json",
            "fixtures/golden_transcripts",
            "reference/python/aicp_ref",
            "conformance/runner/_runner_core_checks.py",
        ]
    ) == (
        24,
        "bc7b502b2804d1ad3b8629425e30fece4ef2dc2f2f5e7d20ab8d9f1132c0a192",
    )


def test_capneg_v02_semantic_surface_is_frozen() -> None:
    assert _tree_digest(
        [
            "docs/extensions/RFC_EXT_CAPNEG_v0.2.md",
            "docs/architecture/ADR_CAPNEG_v0.2_Profile_Composition.md",
            "schemas/extensions/ext-capneg-v0.2-payloads.schema.json",
            "conformance/extensions/CN_CAPNEG_0.2.json",
            "conformance/capneg_v02_runner",
            "fixtures/extensions/capneg_v0_2",
            "reference/python/aicp_ref_capneg_v02",
            "scripts/capneg_v02_fixture_model.py",
            "scripts/generate_capneg_v02_fixtures.py",
            "sdk/typescript/src/capneg_v02.js",
            "sdk/typescript/test/capneg-v02.test.js",
        ]
    ) == (
        22,
        "344542648d55b8b7e0426484144876e9a1c19df1890129e4a8108b63ae581d8e",
    )


def test_projection_v2_semantic_surface_is_frozen() -> None:
    assert _tree_digest(
        [
            "conformance/extensions/OR_SESSION_STATE_PROJECTION_V2.json",
            "fixtures/extensions/object_resync/state_projection_v2",
            "reference/python/aicp_ref_capneg_v02/session_state_v2.py",
            "docs/extensions/SESSION_STATE_PROJECTION_v2.md",
        ]
    ) == (
        5,
        "64d4a33977461551dcae9259b806d3d962ef4b75f6604d60066a9da8f3c18575",
    )
