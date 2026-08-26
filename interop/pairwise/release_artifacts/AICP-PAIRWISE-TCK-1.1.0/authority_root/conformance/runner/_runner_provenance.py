from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
REPORT_FORMAT_VERSION = "1.0"
RUNNER_VERSION = "1.0"


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return sha256_bytes(data)


def canonical_content_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def runner_source_revision(extra_paths: Iterable[Path] = ()) -> str:
    digest = hashlib.sha256()
    paths = set(Path(__file__).resolve().parent.glob("*.py"))
    paths.update(Path(path).resolve() for path in extra_paths)
    for path in sorted(paths, key=lambda item: item.as_posix()):
        try:
            label = path.relative_to(ROOT).as_posix()
        except ValueError:
            label = path.as_posix()
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(data)
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _suite_input_artifacts(suite: dict[str, Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for transcript in suite.get("transcripts", []):
        if not isinstance(transcript, dict):
            continue
        path_ref = transcript.get("path")
        if not isinstance(path_ref, str) or not path_ref:
            continue
        path = ROOT / path_ref
        records.append(
            {
                "artifact_id": str(transcript.get("id") or Path(path_ref).stem),
                "path": path_ref.replace("\\", "/"),
                "content_digest": sha256_file(path),
            }
        )
    for path_ref in suite.get("cases", []):
        if not isinstance(path_ref, str) or not path_ref:
            continue
        path = ROOT / path_ref
        records.append(
            {
                "artifact_id": Path(path_ref).stem,
                "path": path_ref.replace("\\", "/"),
                "content_digest": sha256_file(path),
            }
        )
    return records


def build_suite_provenance(
    suite_path: Path | None,
    suite: dict[str, Any],
    *,
    runner_name: str = "aicp-conformance-runner",
) -> dict[str, Any]:
    if suite_path is not None and suite_path.exists():
        suite_digest = sha256_file(suite_path)
    else:
        suite_digest = canonical_content_digest(suite)
    input_artifacts = _suite_input_artifacts(suite) if suite_path is not None else []
    subject_digest = canonical_content_digest(
        {"suite_digest": suite_digest, "input_artifacts": input_artifacts}
    )
    version_path = ROOT / "VERSION"
    implementation_version = version_path.read_text(encoding="utf-8").strip() if version_path.exists() else "unknown"
    return {
        "report_format_version": REPORT_FORMAT_VERSION,
        "execution_subject": {
            "kind": "reference_corpus",
            "implementation_id": "aicp-reference-corpus",
            "implementation_version": implementation_version,
            "implementation_digest": subject_digest,
        },
        "runner": {
            "name": runner_name,
            "version": RUNNER_VERSION,
            "source_revision": runner_source_revision(),
        },
        "suite": {
            "suite_id": str(suite.get("suite_id", "unknown")),
            "suite_version": str(suite.get("suite_version", "unknown")),
            "suite_digest": suite_digest,
        },
        "input_artifacts": input_artifacts,
        "generated_artifacts": [],
    }


def build_profile_provenance(profile_path: Path, profile: dict[str, Any]) -> dict[str, Any]:
    profile_ref = profile_path.relative_to(ROOT).as_posix() if profile_path.is_relative_to(ROOT) else str(profile_path)
    inputs = [
        {
            "artifact_id": f"{profile.get('profile_id')}@{profile.get('profile_version')}",
            "path": profile_ref,
            "content_digest": sha256_file(profile_path),
        }
    ]
    for suite_ref in profile.get("required_suites", []):
        if isinstance(suite_ref, str) and suite_ref:
            inputs.append(
                {
                    "artifact_id": Path(suite_ref).stem,
                    "path": suite_ref.replace("\\", "/"),
                    "content_digest": sha256_file(ROOT / suite_ref),
                }
            )
    profile_digest = canonical_content_digest(
        {"profile_catalog_digest": inputs[0]["content_digest"], "required_suite_digests": inputs[1:]}
    )
    version_path = ROOT / "VERSION"
    return {
        "report_format_version": REPORT_FORMAT_VERSION,
        "execution_subject": {
            "kind": "reference_corpus",
            "implementation_id": "aicp-reference-corpus",
            "implementation_version": version_path.read_text(encoding="utf-8").strip(),
            "implementation_digest": profile_digest,
        },
        "runner": {
            "name": "aicp-profile-runner",
            "version": RUNNER_VERSION,
            "source_revision": runner_source_revision(),
        },
        "profile": {
            "profile_id": profile.get("profile_id"),
            "profile_version": profile.get("profile_version"),
            "profile_digest": profile_digest,
        },
        "input_artifacts": inputs,
        "generated_artifacts": [],
    }
