from __future__ import annotations

from typing import Any


def _add_failure(failures: list[dict[str, Any]], test_id: str, message: str, file: str, line: int | None) -> None:
    failures.append({"test_id": test_id, "message": message, "file": file, "line": line})


def run_execution_transcript_checks(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    enabled_checks: set[str],
    rel_file: str,
    failures: list[dict[str, Any]],
) -> None:
    if not any(
        check in enabled_checks
        for check in {
            "EX-RUN-REF-01",
            "EX-RUN-TRANSITION-01",
            "EX-RUN-TERMINAL-01",
            "EX-THREAD-REF-01",
            "EX-THREAD-CLOSED-01",
            "EX-STORE-REF-01",
            "EX-STORE-LINK-01",
            "EX-CROSS-BIND-01",
        }
    ):
        return

    run_state: dict[str, str] = {}
    run_terminal: set[str] = set()
    run_thread_bind: dict[str, str] = {}
    thread_created: set[str] = set()
    thread_closed: set[str] = set()
    thread_run_bind: dict[str, str] = {}
    resolved_found_hashes: set[str] = set()
    refs_requiring_resolution: list[tuple[int, str, str]] = []

    def _validate_exec_ref(ref_obj: Any, line_no: int, label: str) -> None:
        if not isinstance(ref_obj, dict):
            _add_failure(failures, "EX-STORE-REF-01", f"{label} must be an object", rel_file, line_no)
            return
        ref_id = ref_obj.get("ref_id")
        obj_hash = ref_obj.get("object_hash")
        obj_type = ref_obj.get("object_type")
        access = ref_obj.get("access")
        if not isinstance(ref_id, str) or not ref_id:
            _add_failure(failures, "EX-STORE-REF-01", f"{label}.ref_id must be a non-empty string", rel_file, line_no)
        if not isinstance(obj_hash, str) or not obj_hash:
            _add_failure(
                failures,
                "EX-STORE-REF-01",
                f"{label}.object_hash must be a non-empty string",
                rel_file,
                line_no,
            )
        if not isinstance(obj_type, str) or not obj_type:
            _add_failure(
                failures,
                "EX-STORE-REF-01",
                f"{label}.object_type must be a non-empty string",
                rel_file,
                line_no,
            )
        if not isinstance(access, dict):
            _add_failure(failures, "EX-STORE-REF-01", f"{label}.access must be an object", rel_file, line_no)
            return
        mode = access.get("mode")
        constraint = access.get("constraint")
        if mode not in {"read", "read_write", "delegated"}:
            _add_failure(
                failures,
                "EX-STORE-REF-01",
                f"{label}.access.mode must be one of read/read_write/delegated",
                rel_file,
                line_no,
            )
        if not isinstance(constraint, str) or not constraint:
            _add_failure(
                failures,
                "EX-STORE-REF-01",
                f"{label}.access.constraint must be a non-empty string",
                rel_file,
                line_no,
            )
        if access.get("resolution_required") is True and isinstance(obj_hash, str):
            refs_requiring_resolution.append((line_no, label, obj_hash))

    for line_no, msg in rows:
        mtype = msg.get("message_type")
        payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}

        if mtype == "OBJECT_RESPONSE":
            entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                if entry.get("status") == "FOUND" and isinstance(entry.get("object_hash"), str):
                    resolved_found_hashes.add(entry.get("object_hash"))

        if mtype in {"RUN_CREATE", "RUN_UPDATE", "RUN_CANCEL", "RUN_COMPLETE"}:
            run_id = payload.get("run_id")
            thread_id = payload.get("thread_id")
            if mtype != "RUN_CREATE":
                if "EX-RUN-REF-01" in enabled_checks and (not isinstance(run_id, str) or run_id not in run_state):
                    _add_failure(
                        failures,
                        "EX-RUN-REF-01",
                        f"{mtype}.run_id '{run_id}' must reference prior RUN_CREATE",
                        rel_file,
                        line_no,
                    )
                if "EX-RUN-TERMINAL-01" in enabled_checks and isinstance(run_id, str) and run_id in run_terminal:
                    _add_failure(
                        failures,
                        "EX-RUN-TERMINAL-01",
                        f"{mtype} is not allowed after terminal state for run_id '{run_id}'",
                        rel_file,
                        line_no,
                    )
            else:
                if "EX-RUN-TRANSITION-01" in enabled_checks and isinstance(run_id, str) and run_id in run_state:
                    _add_failure(
                        failures,
                        "EX-RUN-TRANSITION-01",
                        f"RUN_CREATE for run_id '{run_id}' must be unique",
                        rel_file,
                        line_no,
                    )

            if isinstance(run_id, str):
                if mtype == "RUN_CREATE":
                    run_state[run_id] = str(payload.get("status") or "created")
                elif mtype == "RUN_UPDATE":
                    run_state[run_id] = str(payload.get("status") or run_state.get(run_id) or "running")
                elif mtype == "RUN_CANCEL":
                    if "EX-RUN-TRANSITION-01" in enabled_checks and run_id in run_terminal:
                        _add_failure(
                            failures,
                            "EX-RUN-TRANSITION-01",
                            f"RUN_CANCEL cannot repeat terminal transition for run_id '{run_id}'",
                            rel_file,
                            line_no,
                        )
                    run_state[run_id] = "cancelled"
                    run_terminal.add(run_id)
                elif mtype == "RUN_COMPLETE":
                    if "EX-RUN-TRANSITION-01" in enabled_checks and run_id in run_terminal:
                        _add_failure(
                            failures,
                            "EX-RUN-TRANSITION-01",
                            f"RUN_COMPLETE cannot repeat terminal transition for run_id '{run_id}'",
                            rel_file,
                            line_no,
                        )
                    run_state[run_id] = "completed"
                    run_terminal.add(run_id)

            if isinstance(run_id, str) and isinstance(thread_id, str):
                if "EX-CROSS-BIND-01" in enabled_checks:
                    bound_thread = run_thread_bind.get(run_id)
                    if bound_thread is not None and bound_thread != thread_id:
                        _add_failure(
                            failures,
                            "EX-CROSS-BIND-01",
                            f"run_id '{run_id}' cannot rebind from thread_id '{bound_thread}' to '{thread_id}'",
                            rel_file,
                            line_no,
                        )
                    bound_run = thread_run_bind.get(thread_id)
                    if bound_run is not None and bound_run != run_id:
                        _add_failure(
                            failures,
                            "EX-CROSS-BIND-01",
                            f"thread_id '{thread_id}' cannot rebind from run_id '{bound_run}' to '{run_id}'",
                            rel_file,
                            line_no,
                        )
                run_thread_bind[run_id] = thread_id
                thread_run_bind[thread_id] = run_id

        if mtype in {"THREAD_CREATE", "THREAD_APPEND", "THREAD_CLOSE"}:
            thread_id = payload.get("thread_id")
            run_id = payload.get("run_id")

            if mtype in {"THREAD_APPEND", "THREAD_CLOSE"}:
                if "EX-THREAD-REF-01" in enabled_checks and (
                    not isinstance(thread_id, str) or thread_id not in thread_created
                ):
                    _add_failure(
                        failures,
                        "EX-THREAD-REF-01",
                        f"{mtype}.thread_id '{thread_id}' must reference prior THREAD_CREATE",
                        rel_file,
                        line_no,
                    )
            if (
                mtype in {"THREAD_APPEND", "THREAD_CLOSE"}
                and "EX-THREAD-CLOSED-01" in enabled_checks
                and isinstance(thread_id, str)
                and thread_id in thread_closed
            ):
                _add_failure(
                    failures,
                    "EX-THREAD-CLOSED-01",
                    f"{mtype} is not allowed after THREAD_CLOSE for thread_id '{thread_id}'",
                    rel_file,
                    line_no,
                )

            if isinstance(thread_id, str):
                if mtype == "THREAD_CREATE":
                    thread_created.add(thread_id)
                elif mtype == "THREAD_CLOSE":
                    thread_closed.add(thread_id)

            if isinstance(thread_id, str) and isinstance(run_id, str):
                if "EX-CROSS-BIND-01" in enabled_checks:
                    bound_run = thread_run_bind.get(thread_id)
                    if bound_run is not None and bound_run != run_id:
                        _add_failure(
                            failures,
                            "EX-CROSS-BIND-01",
                            f"thread_id '{thread_id}' cannot rebind from run_id '{bound_run}' to '{run_id}'",
                            rel_file,
                            line_no,
                        )
                    bound_thread = run_thread_bind.get(run_id)
                    if bound_thread is not None and bound_thread != thread_id:
                        _add_failure(
                            failures,
                            "EX-CROSS-BIND-01",
                            f"run_id '{run_id}' cannot rebind from thread_id '{bound_thread}' to '{thread_id}'",
                            rel_file,
                            line_no,
                        )
                thread_run_bind[thread_id] = run_id
                run_thread_bind[run_id] = thread_id

        for ref_key in ("store_ref", "memory_ref"):
            ref_obj = payload.get(ref_key)
            if ref_obj is not None and "EX-STORE-REF-01" in enabled_checks:
                _validate_exec_ref(ref_obj, line_no, ref_key)

    if "EX-STORE-LINK-01" in enabled_checks:
        for line_no, label, obj_hash in refs_requiring_resolution:
            if obj_hash not in resolved_found_hashes:
                _add_failure(
                    failures,
                    "EX-STORE-LINK-01",
                    f"{label}.object_hash '{obj_hash}' requires OBJECT_RESPONSE status=FOUND evidence",
                    rel_file,
                    line_no,
                )
