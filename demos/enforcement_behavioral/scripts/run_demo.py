#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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


def _body_without_hash_and_signatures(msg: dict[str, Any]) -> dict[str, Any]:
    d = dict(msg)
    d.pop("message_hash", None)
    d.pop("signatures", None)
    return d


class TranscriptBuilder:
    def __init__(self, session_id: str, contract_id: str, start_ts: datetime) -> None:
        self.session_id = session_id
        self.contract_id = contract_id
        self.start_ts = start_ts
        self.messages: list[dict[str, Any]] = []
        self._prev_hash: str | None = None

    def add(self, message_id: str, sender: str, message_type: str, payload: dict[str, Any], ts_offset_s: int) -> dict[str, Any]:
        msg = {
            "session_id": self.session_id,
            "message_id": message_id,
            "timestamp": (self.start_ts + timedelta(seconds=ts_offset_s)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sender": sender,
            "message_type": message_type,
            "contract_id": self.contract_id,
            "payload": payload,
        }
        if self._prev_hash is not None:
            msg["prev_msg_hash"] = self._prev_hash

        msg["message_hash"] = message_hash_from_body(_body_without_hash_and_signatures(msg))
        self._prev_hash = msg["message_hash"]
        self.messages.append(msg)
        return msg


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n", encoding="utf-8")


def scenario_happy_path(out_dir: Path, base_ts: datetime) -> ScenarioResult:
    b = TranscriptBuilder("demo:s1", "demo:c1", base_ts)
    b.add("m1", "agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c1"), 0)
    b.add("m2", "chat:mediator", "CONTRACT_ACCEPT", {"accepted": True}, 1)
    content = b.add("m3", "agent:A", "CONTENT_MESSAGE", {"content": "Hello, I want product info."}, 2)
    verdict = b.add(
        "m4",
        "moderator:M",
        "ENFORCEMENT_VERDICT",
        {
            "verdict_id": "v-allow-1",
            "target_message_hash": content["message_hash"],
            "decision": "ALLOW",
            "reason_codes": [],
            "sanctions": [],
            "issued_at": (base_ts + timedelta(seconds=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        3,
    )
    b.add(
        "m5",
        "chat:mediator",
        "CONTENT_DELIVER",
        {
            "delivery_id": "d-allow-1",
            "original_message": content,
            "original_message_hash": content["message_hash"],
            "verdict_message_id": verdict["message_id"],
            "delivered_at": (base_ts + timedelta(seconds=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        4,
    )
    path = out_dir / "01_happy_path.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        name="01_happy_path",
        transcript_path=path,
        expectation="PASS",
        rules_triggered=[],
        verdicts=["ALLOW"],
        alerts=[],
        delivery_occurred="YES",
        resume_outcome="N/A",
    )


def scenario_policy_violation_matrix(out_dir: Path, base_ts: datetime) -> ScenarioResult:
    b = TranscriptBuilder("demo:s2", "demo:c2", base_ts)
    b.add("m1", "agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c2"), 0)
    b.add("m2", "chat:mediator", "CONTRACT_ACCEPT", {"accepted": True}, 1)

    markers = [
        "[VIOLATION:BRAND_OFF_POLICY]",
        "[VIOLATION:PII_EMAIL]",
        "[VIOLATION:PROMPT_INJECTION]",
        "[VIOLATION:MALWARE]",
        "[VIOLATION:HARASSMENT]",
        "[VIOLATION:SPAM]",
    ]
    rules_triggered: list[str] = []

    offset = 2
    counter = 3
    for idx, marker in enumerate(markers, start=1):
        content = b.add(f"m{counter}", "agent:A", "CONTENT_MESSAGE", {"content": marker}, offset)
        counter += 1
        offset += 1
        b.add(
            f"m{counter}",
            "moderator:M",
            "ENFORCEMENT_VERDICT",
            {
                "verdict_id": f"v-deny-{idx}",
                "target_message_hash": content["message_hash"],
                "decision": "DENY",
                "reason_codes": ["POLICY_DENIED"],
                "sanctions": [{"code": "WARN"}],
                "issued_at": (base_ts + timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            offset,
        )
        counter += 1
        offset += 1
        b.add(
            f"m{counter}",
            "chat:mediator",
            "ALERT",
            {
                "alert_id": f"al-deny-{idx}",
                "code": "POLICY_DENIED",
                "severity": "WARNING",
                "recommended_actions": ["REMEDIATE", "ACK_REQUIRED"],
                "issued_at": (base_ts + timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "target_message_hash": content["message_hash"],
                "target_message_id": content["message_id"],
                "message": f"Violation marker detected: {marker}",
            },
            offset,
        )
        counter += 1
        offset += 1
        rules_triggered.append(marker)

    path = out_dir / "02_policy_violation_matrix.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        name="02_policy_violation_matrix",
        transcript_path=path,
        expectation="PASS",
        rules_triggered=rules_triggered,
        verdicts=["DENY+WARN"] * len(markers),
        alerts=["POLICY_DENIED/WARNING"] * len(markers),
        delivery_occurred="NO",
        resume_outcome="N/A",
    )


def scenario_escalation_and_resume(out_dir: Path, base_ts: datetime) -> ScenarioResult:
    b = TranscriptBuilder("demo:s3", "demo:c3", base_ts)
    b.add("m1", "agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c3"), 0)
    b.add("m2", "chat:mediator", "CONTRACT_ACCEPT", {"accepted": True}, 1)

    # First violation from agent:B -> WARN
    first = b.add("m3", "agent:B", "CONTENT_MESSAGE", {"content": "[VIOLATION:SPAM]"}, 2)
    b.add(
        "m4",
        "moderator:M",
        "ENFORCEMENT_VERDICT",
        {
            "verdict_id": "v-b-warn-1",
            "target_message_hash": first["message_hash"],
            "decision": "DENY",
            "reason_codes": ["POLICY_DENIED"],
            "sanctions": [{"code": "WARN"}],
            "issued_at": (base_ts + timedelta(seconds=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        3,
    )
    b.add(
        "m5",
        "chat:mediator",
        "ALERT",
        {
            "alert_id": "al-b-warn-1",
            "code": "POLICY_DENIED",
            "severity": "WARNING",
            "recommended_actions": ["REMEDIATE", "ACK_REQUIRED"],
            "issued_at": (base_ts + timedelta(seconds=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target_message_hash": first["message_hash"],
            "target_message_id": first["message_id"],
            "message": "First violation by agent:B",
        },
        4,
    )

    # Second violation from agent:B -> KICK and fatal alert
    second = b.add("m6", "agent:B", "CONTENT_MESSAGE", {"content": "[VIOLATION:PROMPT_INJECTION]"}, 5)
    b.add(
        "m7",
        "moderator:M",
        "ENFORCEMENT_VERDICT",
        {
            "verdict_id": "v-b-kick-2",
            "target_message_hash": second["message_hash"],
            "decision": "DENY",
            "reason_codes": ["POLICY_DENIED"],
            "sanctions": [{"code": "KICK"}],
            "issued_at": (base_ts + timedelta(seconds=6)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        6,
    )
    b.add(
        "m8",
        "chat:mediator",
        "ALERT",
        {
            "alert_id": "al-b-kick-2",
            "code": "SANCTION_APPLIED",
            "severity": "FATAL",
            "recommended_actions": ["DISCONNECT"],
            "issued_at": (base_ts + timedelta(seconds=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target_message_hash": second["message_hash"],
            "target_message_id": second["message_id"],
            "message": "Escalation sanction applied to agent:B",
        },
        7,
    )

    # Resume attempt after kick -> UNKNOWN_SESSION guidance
    b.add(
        "m9",
        "agent:B",
        "RESUME_REQUEST",
        {
            "resume_id": "resume-b-1",
            "session_id": "demo:s3",
            "last_seen_message_hash": second["message_hash"],
            "contract_id": "demo:c3",
        },
        8,
    )
    b.add(
        "m10",
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
        9,
    )

    path = out_dir / "03_escalation_kick_and_resume.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        name="03_escalation_kick_and_resume",
        transcript_path=path,
        expectation="PASS",
        rules_triggered=["[VIOLATION:SPAM]", "[VIOLATION:PROMPT_INJECTION]"],
        verdicts=["DENY+WARN", "DENY+KICK"],
        alerts=["POLICY_DENIED/WARNING", "SANCTION_APPLIED/FATAL"],
        delivery_occurred="NO",
        resume_outcome="UNKNOWN_SESSION with DISCONNECT guidance",
    )


def scenario_protocol_misuse_expected_fail(out_dir: Path, base_ts: datetime) -> ScenarioResult:
    b = TranscriptBuilder("demo:s4", "demo:c4", base_ts)
    b.add("m1", "agent:A", "CONTRACT_PROPOSE", base_contract_payload("demo:c4"), 0)
    b.add("m2", "chat:mediator", "CONTRACT_ACCEPT", {"accepted": True}, 1)
    b.add("m3", "agent:A", "CONTENT_MESSAGE", {"content": "Hello"}, 2)
    # Protocol misuse: duplicate message_id replay
    b.add("m3", "agent:A", "CONTENT_MESSAGE", {"content": "Replay with duplicate id"}, 3)

    path = out_dir / "04_protocol_misuse_expected_fail.jsonl"
    write_jsonl(path, b.messages)
    return ScenarioResult(
        name="04_protocol_misuse_expected_fail",
        transcript_path=path,
        expectation="EXPECTED_FAIL",
        rules_triggered=["protocol misuse: duplicate message_id"],
        verdicts=[],
        alerts=[],
        delivery_occurred="N/A",
        resume_outcome="N/A",
    )


def write_results(path: Path, results: list[ScenarioResult], out_root: Path) -> None:
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
                f"- Transcript: `{r.transcript_path.relative_to(out_root).as_posix()}`",
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
            "- `04_protocol_misuse_expected_fail` is intentionally invalid and should be treated as expected-failure evidence only.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(out_root: Path) -> list[ScenarioResult]:
    transcripts_dir = out_root / "transcripts"
    results_md = out_root / "results" / "RESULTS.md"
    base_ts = datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)

    scenarios = [
        scenario_happy_path(transcripts_dir, base_ts),
        scenario_policy_violation_matrix(transcripts_dir, base_ts + timedelta(minutes=10)),
        scenario_escalation_and_resume(transcripts_dir, base_ts + timedelta(minutes=20)),
        scenario_protocol_misuse_expected_fail(transcripts_dir, base_ts + timedelta(minutes=30)),
    ]
    write_results(results_md, scenarios, out_root)
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic behavioral enforcement demo transcripts")
    parser.add_argument(
        "--out-root",
        default=str(ROOT / "demos/enforcement_behavioral"),
        help="Output root containing transcripts/ and results/",
    )
    args = parser.parse_args()

    out_root = Path(args.out_root)
    scenarios = run(out_root)
    print(f"Generated {len(scenarios)} scenarios under {out_root}")
    for s in scenarios:
        print(f"- {s.name}: {s.expectation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
