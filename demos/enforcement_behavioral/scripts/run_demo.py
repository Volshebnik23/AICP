#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body  # noqa: E402


@dataclass
class ScenarioResult:
    name: str
    transcript_path: Path
    expectation: str
    rules_triggered: list[str]
    verdicts: list[str]
    alerts: list[str]
    delivery_occurred: str
    resume_outcome: str


class TranscriptBuilder:
    def __init__(self, session_id: str, contract_id: str) -> None:
        self.session_id = session_id
        self.contract_id = contract_id
        self.messages: list[dict[str, Any]] = []
        self._prev_hash: str | None = None
        self._counter = 0

    def add(self, sender: str, message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._counter += 1
        msg = {
            "session_id": self.session_id,
            "message_id": f"m{self._counter:04d}",
            "timestamp": f"t{self._counter:04d}",
            "sender": sender,
            "message_type": message_type,
            "contract_id": self.contract_id,
            "payload": payload,
        }
        if self._prev_hash is not None:
            msg["prev_msg_hash"] = self._prev_hash

        msg["message_hash"] = message_hash_from_body(_message_body_without_hash_and_signatures(msg))
        self._prev_hash = msg["message_hash"]
        self.messages.append(msg)
        return msg


def _message_body_without_hash_and_signatures(message: dict[str, Any]) -> dict[str, Any]:
    body = dict(message)
    body.pop("message_hash", None)
    body.pop("signatures", None)
    return body


def base_contract_payload(contract_id: str) -> dict[str, Any]:
    return {
        "contract": {
            "contract_id": contract_id,
            "goal": "behavioral_enforcement_demo",
            "roles": ["agent", "moderator", "mediator"],
            "ext": {
                "enforcement": {
                    "mode": "blocking",
                    "enforcers": ["moderator:M"],
                    "gated_message_types": ["CONTENT_MESSAGE"],
                }
            },
        },
        "note": "deterministic behavioral demo",
    }


def _issued_at(ix: int) -> str:
    return f"t{ix:04d}"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n", encoding="utf-8")


def scenario_happy_path(out_dir: Path) -> ScenarioResult:
    b = TranscriptBuilder("demo:s1", "demo:c1")
    b.add("agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c1"))
    b.add("chat:mediator", "CONTRACT_ACCEPT", {"accepted": True})
    content = b.add("agent:A", "CONTENT_MESSAGE", {"content": "Hello, I want product info."})
    verdict = b.add(
        "moderator:M",
        "ENFORCEMENT_VERDICT",
        {
            "verdict_id": "v-allow-1",
            "target_message_hash": content["message_hash"],
            "decision": "ALLOW",
            "reason_codes": [],
            "sanctions": [],
            "issued_at": _issued_at(1),
        },
    )
    b.add(
        "chat:mediator",
        "CONTENT_DELIVER",
        {
            "delivery_id": "d-allow-1",
            "original_message": content,
            "original_message_hash": content["message_hash"],
            "verdict_message_id": verdict["message_id"],
            "delivered_at": _issued_at(2),
        },
    )
    path = out_dir / "01_happy_path.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult("01_happy_path", path, "PASS", [], ["ALLOW"], [], "YES", "N/A")


def scenario_policy_violation_matrix(out_dir: Path) -> ScenarioResult:
    b = TranscriptBuilder("demo:s2", "demo:c2")
    b.add("agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c2"))
    b.add("chat:mediator", "CONTRACT_ACCEPT", {"accepted": True})

    markers = [
        "[VIOLATION:BRAND_OFF_POLICY]",
        "[VIOLATION:PII_EMAIL]",
        "[VIOLATION:PII_PHONE]",
        "[VIOLATION:PROMPT_INJECTION]",
        "[VIOLATION:MALWARE]",
        "[VIOLATION:PHISHING]",
        "[VIOLATION:HARASSMENT]",
        "[VIOLATION:SPAM]",
    ]
    for idx, marker in enumerate(markers, start=1):
        content = b.add("agent:A", "CONTENT_MESSAGE", {"content": marker})
        b.add(
            "moderator:M",
            "ENFORCEMENT_VERDICT",
            {
                "verdict_id": f"v-deny-{idx}",
                "target_message_hash": content["message_hash"],
                "decision": "DENY",
                "reason_codes": ["POLICY_DENIED"],
                "sanctions": [{"code": "WARN"}],
                "issued_at": _issued_at(100 + idx),
            },
        )
        b.add(
            "chat:mediator",
            "ALERT",
            {
                "alert_id": f"al-deny-{idx}",
                "code": "POLICY_DENIED",
                "severity": "WARNING",
                "recommended_actions": ["REMEDIATE", "ACK_REQUIRED"],
                "issued_at": _issued_at(200 + idx),
                "target_message_hash": content["message_hash"],
                "target_message_id": content["message_id"],
                "message": f"Violation marker detected: {marker}",
            },
        )

    path = out_dir / "02_policy_violation_matrix.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        "02_policy_violation_matrix",
        path,
        "PASS",
        markers,
        ["DENY+WARN"] * len(markers),
        ["POLICY_DENIED/WARNING"] * len(markers),
        "NO",
        "N/A",
    )


def scenario_escalation_and_resume(out_dir: Path) -> ScenarioResult:
    b = TranscriptBuilder("demo:s3", "demo:c3")
    b.add("agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c3"))
    b.add("chat:mediator", "CONTRACT_ACCEPT", {"accepted": True})

    first = b.add("agent:B", "CONTENT_MESSAGE", {"content": "[VIOLATION:SPAM]"})
    b.add(
        "moderator:M",
        "ENFORCEMENT_VERDICT",
        {
            "verdict_id": "v-b-warn-1",
            "target_message_hash": first["message_hash"],
            "decision": "DENY",
            "reason_codes": ["POLICY_DENIED"],
            "sanctions": [{"code": "WARN"}],
            "issued_at": _issued_at(301),
        },
    )
    b.add(
        "chat:mediator",
        "ALERT",
        {
            "alert_id": "al-b-warn-1",
            "code": "POLICY_DENIED",
            "severity": "WARNING",
            "recommended_actions": ["REMEDIATE", "ACK_REQUIRED"],
            "issued_at": _issued_at(302),
            "target_message_hash": first["message_hash"],
            "target_message_id": first["message_id"],
            "message": "First violation by agent:B",
        },
    )

    second = b.add("agent:B", "CONTENT_MESSAGE", {"content": "[VIOLATION:PROMPT_INJECTION]"})
    b.add(
        "moderator:M",
        "ENFORCEMENT_VERDICT",
        {
            "verdict_id": "v-b-kick-2",
            "target_message_hash": second["message_hash"],
            "decision": "DENY",
            "reason_codes": ["POLICY_DENIED"],
            "sanctions": [{"code": "KICK"}],
            "issued_at": _issued_at(303),
        },
    )
    b.add(
        "chat:mediator",
        "ALERT",
        {
            "alert_id": "al-b-kick-2",
            "code": "SANCTION_APPLIED",
            "severity": "FATAL",
            "recommended_actions": ["DISCONNECT"],
            "issued_at": _issued_at(304),
            "target_message_hash": second["message_hash"],
            "target_message_id": second["message_id"],
            "message": "Escalation sanction applied to agent:B",
        },
    )

    b.add(
        "agent:B",
        "RESUME_REQUEST",
        {
            "resume_id": "resume-b-1",
            "session_id": "demo:s3",
            "last_seen_message_hash": second["message_hash"],
            "contract_id": "demo:c3",
        },
    )
    b.add(
        "chat:mediator",
        "RESUME_RESPONSE",
        {
            "resume_id": "resume-b-1",
            "session_id": "demo:s3",
            "status": "UNKNOWN_SESSION",
            "current_head_hash": "unknown",
            "recommended_actions": ["DISCONNECT", "ESCALATE"],
            "message": "Session cannot be resumed for kicked participant.",
        },
    )

    path = out_dir / "03_escalation_kick_and_resume.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        "03_escalation_kick_and_resume",
        path,
        "PASS",
        ["[VIOLATION:SPAM]", "[VIOLATION:PROMPT_INJECTION]"],
        ["DENY+WARN", "DENY+KICK"],
        ["POLICY_DENIED/WARNING", "SANCTION_APPLIED/FATAL"],
        "NO",
        "UNKNOWN_SESSION with DISCONNECT guidance",
    )


def scenario_inconclusive_escalate(out_dir: Path) -> ScenarioResult:
    b = TranscriptBuilder("demo:s4", "demo:c4")
    b.add("agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c4"))
    b.add("chat:mediator", "CONTRACT_ACCEPT", {"accepted": True})
    content = b.add("agent:A", "CONTENT_MESSAGE", {"content": "[VIOLATION:PROMPT_INJECTION]"})
    b.add(
        "moderator:M",
        "ENFORCEMENT_VERDICT",
        {
            "verdict_id": "v-inconclusive-1",
            "target_message_hash": content["message_hash"],
            "decision": "INCONCLUSIVE",
            "reason_codes": ["POLICY_DENIED"],
            "sanctions": [],
            "issued_at": _issued_at(401),
        },
    )
    b.add(
        "chat:mediator",
        "ALERT",
        {
            "alert_id": "al-inconclusive-1",
            "code": "POLICY_INCONCLUSIVE",
            "severity": "WARNING",
            "recommended_actions": ["ESCALATE", "ACK_REQUIRED"],
            "issued_at": _issued_at(402),
            "target_message_hash": content["message_hash"],
            "target_message_id": content["message_id"],
            "message": "Manual review required.",
        },
    )
    path = out_dir / "04_inconclusive_escalate.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        "04_inconclusive_escalate",
        path,
        "PASS",
        ["[VIOLATION:PROMPT_INJECTION]"],
        ["INCONCLUSIVE"],
        ["POLICY_INCONCLUSIVE/WARNING"],
        "NO",
        "N/A",
    )


def scenario_resume_needs_resync(out_dir: Path) -> ScenarioResult:
    b = TranscriptBuilder("demo:s5", "demo:c5")
    b.add("agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c5"))
    b.add("chat:mediator", "CONTRACT_ACCEPT", {"accepted": True})
    head_a = b.add("agent:A", "CONTENT_MESSAGE", {"content": "sync anchor"})
    b.add("moderator:M", "ENFORCEMENT_VERDICT", {
        "verdict_id": "v-sync-1",
        "target_message_hash": head_a["message_hash"],
        "decision": "ALLOW",
        "reason_codes": [],
        "sanctions": [],
        "issued_at": _issued_at(501),
    })
    b.add("agent:A", "CONTENT_MESSAGE", {"content": "newer head"})
    head_b = b.messages[-1]
    b.add(
        "agent:A",
        "RESUME_REQUEST",
        {
            "resume_id": "resume-a-1",
            "session_id": "demo:s5",
            "last_seen_message_hash": head_a["message_hash"],
            "contract_id": "demo:c5",
        },
    )
    b.add(
        "chat:mediator",
        "RESUME_RESPONSE",
        {
            "resume_id": "resume-a-1",
            "session_id": "demo:s5",
            "status": "NEEDS_RESYNC",
            "current_head_hash": head_b["message_hash"],
            "recommended_actions": ["RETRY", "REMEDIATE"],
            "message": "Client head is behind mediator head.",
        },
    )
    b.add(
        "chat:mediator",
        "ALERT",
        {
            "alert_id": "al-resync-1",
            "code": "RESYNC_REQUIRED",
            "severity": "WARNING",
            "recommended_actions": ["RETRY", "REMEDIATE"],
            "issued_at": _issued_at(502),
            "message": "Resume requires state resynchronization.",
        },
    )

    path = out_dir / "05_resume_needs_resync.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        "05_resume_needs_resync",
        path,
        "PASS",
        [],
        ["ALLOW"],
        ["RESYNC_REQUIRED/WARNING"],
        "N/A",
        "NEEDS_RESYNC with RETRY/REMEDIATE guidance",
    )


def scenario_malicious_mediator_delivers_after_deny(out_dir: Path) -> ScenarioResult:
    b = TranscriptBuilder("demo:s6", "demo:c6")
    b.add("agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c6"))
    b.add("chat:mediator", "CONTRACT_ACCEPT", {"accepted": True})
    content = b.add("agent:A", "CONTENT_MESSAGE", {"content": "[VIOLATION:SPAM]"})
    verdict = b.add(
        "moderator:M",
        "ENFORCEMENT_VERDICT",
        {
            "verdict_id": "v-deny-malicious-1",
            "target_message_hash": content["message_hash"],
            "decision": "DENY",
            "reason_codes": ["POLICY_DENIED"],
            "sanctions": [{"code": "WARN"}],
            "issued_at": _issued_at(601),
        },
    )
    b.add(
        "chat:mediator",
        "CONTENT_DELIVER",
        {
            "delivery_id": "d-malicious-1",
            "original_message": content,
            "original_message_hash": content["message_hash"],
            "verdict_message_id": verdict["message_id"],
            "delivered_at": _issued_at(602),
        },
    )

    path = out_dir / "06_malicious_mediator_delivers_after_deny_expected_fail.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        "06_malicious_mediator_delivers_after_deny_expected_fail",
        path,
        "EXPECTED_FAIL",
        ["malicious mediator delivery after deny"],
        ["DENY"],
        [],
        "YES (invalid behavior)",
        "N/A",
    )


def scenario_spoofed_verdict_sender(out_dir: Path) -> ScenarioResult:
    b = TranscriptBuilder("demo:s7", "demo:c7")
    b.add("agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c7"))
    b.add("chat:mediator", "CONTRACT_ACCEPT", {"accepted": True})
    content = b.add("agent:A", "CONTENT_MESSAGE", {"content": "Hello from A"})
    spoofed_verdict = b.add(
        "agent:B",
        "ENFORCEMENT_VERDICT",
        {
            "verdict_id": "v-spoofed-1",
            "target_message_hash": content["message_hash"],
            "decision": "ALLOW",
            "reason_codes": [],
            "sanctions": [],
            "issued_at": _issued_at(701),
        },
    )
    b.add(
        "chat:mediator",
        "CONTENT_DELIVER",
        {
            "delivery_id": "d-spoofed-1",
            "original_message": content,
            "original_message_hash": content["message_hash"],
            "verdict_message_id": spoofed_verdict["message_id"],
            "delivered_at": _issued_at(702),
        },
    )

    path = out_dir / "07_spoofed_verdict_sender_expected_fail.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        "07_spoofed_verdict_sender_expected_fail",
        path,
        "EXPECTED_FAIL",
        ["spoofed verdict sender"],
        ["ALLOW (spoofed)"],
        [],
        "YES (invalid behavior)",
        "N/A",
    )


def scenario_duplicate_message_id_replay(out_dir: Path) -> ScenarioResult:
    b = TranscriptBuilder("demo:s8", "demo:c8")
    b.add("agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c8"))
    b.add("chat:mediator", "CONTRACT_ACCEPT", {"accepted": True})
    b.add("agent:A", "CONTENT_MESSAGE", {"content": "Hello"})

    replay = {
        "session_id": "demo:s8",
        "message_id": "m0003",
        "timestamp": "t9999",
        "sender": "agent:A",
        "message_type": "CONTENT_MESSAGE",
        "contract_id": "demo:c8",
        "payload": {"content": "Replay with duplicate id"},
        "prev_msg_hash": b.messages[-1]["message_hash"],
    }
    replay["message_hash"] = message_hash_from_body(_message_body_without_hash_and_signatures(replay))
    b.messages.append(replay)

    path = out_dir / "08_duplicate_message_id_replay_expected_fail.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        "08_duplicate_message_id_replay_expected_fail",
        path,
        "EXPECTED_FAIL",
        ["protocol misuse: duplicate message_id"],
        [],
        [],
        "N/A",
        "N/A",
    )


def write_run_results(path: Path, results: list[ScenarioResult], run_dir: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Behavioral demo results",
        "",
        "This file is generated by `demos/enforcement_behavioral/scripts/run_demo.py`.",
        "",
    ]
    for r in results:
        lines.extend(
            [
                f"## {r.name}",
                f"- Transcript: `{r.transcript_path.relative_to(run_dir).as_posix()}`",
                f"- Expected status: **{r.expectation}**",
                f"- Rules triggered: {', '.join(r.rules_triggered) if r.rules_triggered else 'none'}",
                f"- Verdicts/sanctions: {', '.join(r.verdicts) if r.verdicts else 'none'}",
                f"- Alerts emitted: {', '.join(r.alerts) if r.alerts else 'none'}",
                f"- Delivery occurred: {r.delivery_occurred}",
                f"- Resume outcome: {r.resume_outcome}",
                "",
            ]
        )

    lines.extend(
        [
            "## Notes",
            "- Violation markers are safe placeholders (e.g., `[VIOLATION:PII_EMAIL]`) and not real harmful content.",
            "- Expected-fail scenarios are intentionally invalid and should only be used as negative evidence.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_latest_pointer(path: Path, run_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Behavioral demo results",
        "",
        "Canonical demo outputs are stored as immutable run history.",
        "",
        f"- Latest run: `demos/enforcement_behavioral/history/{run_name}/`",
        f"- Results file: `demos/enforcement_behavioral/history/{run_name}/results/RESULTS.md`",
        "",
        "Re-run demo generator to create a new run folder; do not edit historical run outputs by hand.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def next_run_dir(out_root: Path) -> Path:
    history = out_root / "history"
    history.mkdir(parents=True, exist_ok=True)
    nums = []
    for p in history.glob("run_*"):
        if p.is_dir() and p.name.startswith("run_"):
            suffix = p.name[4:]
            if suffix.isdigit():
                nums.append(int(suffix))
    nxt = max(nums, default=0) + 1
    return history / f"run_{nxt:04d}"


def run(out_root: Path) -> tuple[list[ScenarioResult], Path]:
    run_dir = next_run_dir(out_root)
    transcripts_dir = run_dir / "transcripts"
    results_md = run_dir / "results" / "RESULTS.md"
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "rules").mkdir(parents=True, exist_ok=True)

    shutil.copy2(out_root / "rules" / "CHAT_RULES.md", run_dir / "rules" / "CHAT_RULES.md")
    shutil.copy2(out_root / "PERSONA_VALUE_FEATURE_TEST.md", run_dir / "PERSONA_VALUE_FEATURE_TEST.md")

    scenarios = [
        scenario_happy_path(transcripts_dir),
        scenario_policy_violation_matrix(transcripts_dir),
        scenario_escalation_and_resume(transcripts_dir),
        scenario_inconclusive_escalate(transcripts_dir),
        scenario_resume_needs_resync(transcripts_dir),
        scenario_malicious_mediator_delivers_after_deny(transcripts_dir),
        scenario_spoofed_verdict_sender(transcripts_dir),
        scenario_duplicate_message_id_replay(transcripts_dir),
    ]
    write_run_results(results_md, scenarios, run_dir)
    write_latest_pointer(out_root / "results" / "RESULTS.md", run_dir.name)
    return scenarios, run_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic behavioral enforcement demo transcripts")
    parser.add_argument(
        "--out-root",
        default=str(ROOT / "demos/enforcement_behavioral"),
        help="Output root containing history/, rules/, and results/",
    )
    args = parser.parse_args()

    out_root = Path(args.out_root)
    scenarios, run_dir = run(out_root)
    print(f"Generated {len(scenarios)} scenarios under {run_dir}")
    for s in scenarios:
        print(f"- {s.name}: {s.expectation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
