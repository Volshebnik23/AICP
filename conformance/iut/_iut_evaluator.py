from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = ROOT / "conformance/runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from aicp_conformance_runner import run_suite  # noqa: E402


def _write_jsonl(path: Path, messages: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n" for message in messages),
        encoding="utf-8",
    )


def evaluate_transcript(
    messages: list[dict[str, Any]],
    suite_refs: list[str],
) -> tuple[list[dict[str, str]], bool, list[str], list[str]]:
    """Evaluate an arbitrary IUT transcript with the checked-in suite checks.

    The original suite's expected-fail annotations are deliberately not reused: an
    adapter validates the supplied transcript as protocol input and does not receive
    the runner's expected answer or canonical case identity.
    """

    errors: list[dict[str, str]] = []
    degraded = False
    degraded_reasons: list[str] = []
    skipped_checks: list[str] = []
    temp_root = ROOT / "out" / "iut-evaluator"
    temp_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="run-", dir=temp_root) as raw_dir:
        temp_dir = Path(raw_dir)
        transcript_path = temp_dir / "transcript.jsonl"
        _write_jsonl(transcript_path, messages)
        expected_types = [str(message.get("message_type", "")) for message in messages]
        for index, suite_ref in enumerate(suite_refs, start=1):
            suite_path = ROOT / suite_ref
            suite = copy.deepcopy(json.loads(suite_path.read_text(encoding="utf-8")))
            suite["transcripts"] = [
                {
                    "id": f"IUT-RUNTIME-{index}",
                    "path": transcript_path.resolve().as_posix(),
                    "expected_message_types": expected_types,
                }
            ]
            dynamic_suite_path = temp_dir / f"suite-{index}.json"
            dynamic_suite_path.write_text(
                json.dumps(suite, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            report = run_suite(dynamic_suite_path)
            for failure in report.get("failures", []):
                errors.append(
                    {
                        "code": str(failure.get("test_id", "suite_failure")),
                        "message": str(failure.get("message", "suite validation failed")),
                    }
                )
            if report.get("degraded"):
                degraded = True
            for reason in report.get("degraded_reasons", []) or []:
                if isinstance(reason, str) and reason not in degraded_reasons:
                    degraded_reasons.append(reason)
            for check_id in report.get("skipped_checks", []) or []:
                if isinstance(check_id, str) and check_id not in skipped_checks:
                    skipped_checks.append(check_id)
    return errors, degraded, degraded_reasons, skipped_checks


def validate_generated_artifact(
    artifact: Any,
    scenario: dict[str, Any],
    suite_refs: list[str],
) -> list[str]:
    if not isinstance(artifact, list) or not artifact or not all(isinstance(item, dict) for item in artifact):
        return ["generated artifact must be a non-empty transcript array"]
    messages: list[dict[str, Any]] = artifact
    desired_types = scenario.get("desired_message_types")
    actual_types = [message.get("message_type") for message in messages]
    errors: list[str] = []
    if actual_types != desired_types:
        errors.append("generated transcript message-type sequence does not match the neutral scenario")
    participants = set(item for item in scenario.get("participants", []) if isinstance(item, str))
    senders = set(message.get("sender") for message in messages if isinstance(message.get("sender"), str))
    if not senders.issubset(participants):
        errors.append("generated transcript contains a sender outside the scenario participants")
    suite_errors, degraded, reasons, skipped = evaluate_transcript(messages, suite_refs)
    errors.extend(f"{item['code']}: {item['message']}" for item in suite_errors)
    if degraded:
        errors.append("generated transcript validation was degraded: " + "; ".join(reasons))
    if skipped:
        errors.append("generated transcript validation skipped checks: " + ", ".join(skipped))
    return errors
