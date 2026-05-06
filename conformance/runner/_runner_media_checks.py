from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _add_failure(failures: list[dict[str, Any]], test_id: str, message: str, file: str, line: int | None) -> None:
    failures.append({"test_id": test_id, "message": message, "file": file, "line": line})


def run_media_delivery_transcript_checks(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    enabled_checks: set[str],
    policy_reason_codes: set[str],
    is_namespaced_identifier_fn: Callable[[str], bool],
    rel_file: str,
    failures: list[dict[str, Any]],
) -> None:
    if any(check in enabled_checks for check in {"CH-HIER-01", "CH-LIFECYCLE-01"}):
        declared_channels: dict[str, dict[str, Any]] = {}
        deprecated_channels: set[str] = set()
        for line_no, msg in rows:
            mtype = msg.get("message_type")
            payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
            if mtype == "CHANNEL_DECLARE":
                channel_id = payload.get("channel_id") if isinstance(payload.get("channel_id"), str) else None
                if isinstance(channel_id, str):
                    parent_id = payload.get("parent_channel_id") if isinstance(payload.get("parent_channel_id"), str) else None
                    if "CH-HIER-01" in enabled_checks and isinstance(parent_id, str) and parent_id not in declared_channels:
                        _add_failure(
                            failures,
                            "CH-HIER-01",
                            f"CHANNEL_DECLARE.parent_channel_id '{parent_id}' must reference prior declared channel",
                            rel_file,
                            line_no,
                        )
                    vis = payload.get("visibility_class")
                    if "CH-HIER-01" in enabled_checks and isinstance(parent_id, str) and parent_id in declared_channels:
                        parent_vis = declared_channels[parent_id].get("visibility_class")
                        if parent_vis == "private" and vis == "public":
                            _add_failure(
                                failures,
                                "CH-HIER-01",
                                "child channel visibility_class cannot escalate from parent private to public",
                                rel_file,
                                line_no,
                            )
                    declared_channels[channel_id] = payload
            elif mtype == "CHANNEL_UPDATE":
                channel_id = payload.get("channel_id") if isinstance(payload.get("channel_id"), str) else None
                if "CH-LIFECYCLE-01" in enabled_checks and (
                    not isinstance(channel_id, str) or channel_id not in declared_channels
                ):
                    _add_failure(
                        failures,
                        "CH-LIFECYCLE-01",
                        f"CHANNEL_UPDATE.channel_id '{channel_id}' must reference prior CHANNEL_DECLARE",
                        rel_file,
                        line_no,
                    )
                if isinstance(channel_id, str) and channel_id in deprecated_channels and "CH-LIFECYCLE-01" in enabled_checks:
                    _add_failure(
                        failures,
                        "CH-LIFECYCLE-01",
                        f"CHANNEL_UPDATE.channel_id '{channel_id}' is already deprecated",
                        rel_file,
                        line_no,
                    )
                parent_id = payload.get("parent_channel_id") if isinstance(payload.get("parent_channel_id"), str) else None
                if "CH-HIER-01" in enabled_checks and isinstance(parent_id, str) and parent_id not in declared_channels:
                    _add_failure(
                        failures,
                        "CH-HIER-01",
                        f"CHANNEL_UPDATE.parent_channel_id '{parent_id}' must reference prior declared channel",
                        rel_file,
                        line_no,
                    )
            elif mtype == "CHANNEL_DEPRECATE":
                channel_id = payload.get("channel_id") if isinstance(payload.get("channel_id"), str) else None
                if "CH-LIFECYCLE-01" in enabled_checks and (
                    not isinstance(channel_id, str) or channel_id not in declared_channels
                ):
                    _add_failure(
                        failures,
                        "CH-LIFECYCLE-01",
                        f"CHANNEL_DEPRECATE.channel_id '{channel_id}' must reference prior CHANNEL_DECLARE",
                        rel_file,
                        line_no,
                    )
                if isinstance(channel_id, str):
                    deprecated_channels.add(channel_id)

    if any(check in enabled_checks for check in {"SB-STATE-01", "SB-CURSOR-01"}):
        known_subscriptions: set[str] = set()
        cursor_order: dict[str, str] = {}

        def _cursor_rank(value: str) -> int:
            digits = "".join(ch for ch in value if ch.isdigit())
            return int(digits) if digits else 0

        for line_no, msg in rows:
            mtype = msg.get("message_type")
            payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
            if mtype == "SUBSCRIBE":
                sub_id = payload.get("subscription_id")
                if isinstance(sub_id, str):
                    known_subscriptions.add(sub_id)
            elif mtype == "SUBSCRIPTION_STATE":
                sub_id = payload.get("subscription_id")
                cursor = payload.get("cursor")
                if "SB-STATE-01" in enabled_checks and (
                    not isinstance(sub_id, str) or sub_id not in known_subscriptions
                ):
                    _add_failure(
                        failures,
                        "SB-STATE-01",
                        f"SUBSCRIPTION_STATE.subscription_id '{sub_id}' must reference prior SUBSCRIBE",
                        rel_file,
                        line_no,
                    )
                if "SB-CURSOR-01" in enabled_checks and isinstance(sub_id, str) and isinstance(cursor, str):
                    prev_cursor = cursor_order.get(sub_id)
                    if isinstance(prev_cursor, str) and _cursor_rank(cursor) < _cursor_rank(prev_cursor):
                        _add_failure(
                            failures,
                            "SB-CURSOR-01",
                            f"SUBSCRIPTION_STATE.cursor '{cursor}' regressed from '{prev_cursor}'",
                            rel_file,
                            line_no,
                        )
                    cursor_order[sub_id] = cursor
            elif mtype == "UNSUBSCRIBE":
                sub_id = payload.get("subscription_id")
                if "SB-STATE-01" in enabled_checks and (
                    not isinstance(sub_id, str) or sub_id not in known_subscriptions
                ):
                    _add_failure(
                        failures,
                        "SB-STATE-01",
                        f"UNSUBSCRIBE.subscription_id '{sub_id}' must reference prior SUBSCRIBE",
                        rel_file,
                        line_no,
                    )
                if isinstance(sub_id, str):
                    known_subscriptions.discard(sub_id)

    if any(check in enabled_checks for check in {"PB-LIFECYCLE-01", "PB-REASON-01", "PB-DELIVERY-01"}):
        publication_versions: dict[str, str] = {}
        must_reach = False
        for _, msg in rows:
            if msg.get("message_type") == "CONTRACT_PROPOSE":
                contract = ((msg.get("payload") or {}).get("contract") or {})
                ext = contract.get("ext") if isinstance(contract, dict) else None
                pubs = ext.get("publications") if isinstance(ext, dict) else None
                if isinstance(pubs, dict) and pubs.get("must_reach") is True:
                    must_reach = True
                break

        for line_no, msg in rows:
            mtype = msg.get("message_type")
            payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
            if mtype == "PUBLICATION_PUBLISH":
                publication_id = payload.get("publication_id")
                version_id = payload.get("version_id")
                if isinstance(publication_id, str) and isinstance(version_id, str):
                    publication_versions[publication_id] = version_id
                if must_reach and "PB-DELIVERY-01" in enabled_checks:
                    proof = payload.get("delivery_proof_ref")
                    if not isinstance(proof, str) or not proof:
                        _add_failure(
                            failures,
                            "PB-DELIVERY-01",
                            "must_reach publication requires payload.delivery_proof_ref",
                            rel_file,
                            line_no,
                        )
            elif mtype == "PUBLICATION_UPDATE":
                publication_id = payload.get("publication_id")
                version_id = payload.get("version_id")
                prior_version_id = payload.get("prior_version_id")
                if "PB-LIFECYCLE-01" in enabled_checks:
                    if not isinstance(publication_id, str) or publication_id not in publication_versions:
                        _add_failure(
                            failures,
                            "PB-LIFECYCLE-01",
                            f"PUBLICATION_UPDATE.publication_id '{publication_id}' must reference prior PUBLICATION_PUBLISH",
                            rel_file,
                            line_no,
                        )
                    else:
                        expected_prior = publication_versions[publication_id]
                        if prior_version_id != expected_prior:
                            _add_failure(
                                failures,
                                "PB-LIFECYCLE-01",
                                f"PUBLICATION_UPDATE.prior_version_id '{prior_version_id}' must equal current version '{expected_prior}'",
                                rel_file,
                                line_no,
                            )
                        if version_id == prior_version_id:
                            _add_failure(
                                failures,
                                "PB-LIFECYCLE-01",
                                "PUBLICATION_UPDATE.version_id must progress beyond prior_version_id",
                                rel_file,
                                line_no,
                            )
                if must_reach and "PB-DELIVERY-01" in enabled_checks:
                    proof = payload.get("delivery_proof_ref")
                    if not isinstance(proof, str) or not proof:
                        _add_failure(
                            failures,
                            "PB-DELIVERY-01",
                            "must_reach publication requires payload.delivery_proof_ref",
                            rel_file,
                            line_no,
                        )
                if isinstance(publication_id, str) and isinstance(version_id, str):
                    publication_versions[publication_id] = version_id
            elif mtype == "PUBLICATION_RETRACT":
                publication_id = payload.get("publication_id")
                prior_version_id = payload.get("prior_version_id")
                if "PB-LIFECYCLE-01" in enabled_checks:
                    if not isinstance(publication_id, str) or publication_id not in publication_versions:
                        _add_failure(
                            failures,
                            "PB-LIFECYCLE-01",
                            f"PUBLICATION_RETRACT.publication_id '{publication_id}' must reference known publication",
                            rel_file,
                            line_no,
                        )
                    else:
                        expected_prior = publication_versions[publication_id]
                        if prior_version_id != expected_prior:
                            _add_failure(
                                failures,
                                "PB-LIFECYCLE-01",
                                f"PUBLICATION_RETRACT.prior_version_id '{prior_version_id}' must equal current version '{expected_prior}'",
                                rel_file,
                                line_no,
                            )
                if "PB-REASON-01" in enabled_checks:
                    reason_code = payload.get("reason_code")
                    if not isinstance(reason_code, str) or not reason_code:
                        _add_failure(
                            failures,
                            "PB-REASON-01",
                            "PUBLICATION_RETRACT.reason_code must be a non-empty string",
                            rel_file,
                            line_no,
                        )
                    elif reason_code not in policy_reason_codes and not is_namespaced_identifier_fn(reason_code):
                        _add_failure(
                            failures,
                            "PB-REASON-01",
                            f"unknown reason_code '{reason_code}' (must be registered or namespaced vendor:/org:)",
                            rel_file,
                            line_no,
                        )
                if must_reach and "PB-DELIVERY-01" in enabled_checks:
                    proof = payload.get("delivery_proof_ref")
                    if not isinstance(proof, str) or not proof:
                        _add_failure(
                            failures,
                            "PB-DELIVERY-01",
                            "must_reach publication requires payload.delivery_proof_ref",
                            rel_file,
                            line_no,
                        )

    if any(check in enabled_checks for check in {"IB-LINK-01", "IB-LEASE-01"}):
        queued_items: dict[str, str] = {}
        leased_items: dict[str, str] = {}
        lease_by_id: dict[str, dict[str, Any]] = {}
        require_queue_lease_ref = False
        require_admission_ref = False
        for _, msg in rows:
            if msg.get("message_type") == "CONTRACT_PROPOSE":
                contract = ((msg.get("payload") or {}).get("contract") or {})
                ext = contract.get("ext") if isinstance(contract, dict) else None
                inbox_ext = ext.get("inbox") if isinstance(ext, dict) else None
                if isinstance(inbox_ext, dict):
                    require_queue_lease_ref = inbox_ext.get("require_queue_lease_ref") is True
                    require_admission_ref = inbox_ext.get("require_admission_ref") is True
                break

        for line_no, msg in rows:
            mtype = msg.get("message_type")
            payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
            if mtype == "INBOX_ENQUEUE":
                inbox_id = payload.get("inbox_id")
                item_id = payload.get("item_id")
                if isinstance(item_id, str) and isinstance(inbox_id, str):
                    queued_items[item_id] = inbox_id
            elif mtype == "INBOX_ROUTE":
                item_id = payload.get("item_id")
                if "IB-LINK-01" in enabled_checks and (not isinstance(item_id, str) or item_id not in queued_items):
                    _add_failure(
                        failures,
                        "IB-LINK-01",
                        f"INBOX_ROUTE.item_id '{item_id}' must reference prior INBOX_ENQUEUE",
                        rel_file,
                        line_no,
                    )
            elif mtype == "INBOX_LEASE_GRANT":
                inbox_id = payload.get("inbox_id")
                lease_id = payload.get("lease_id")
                item_id = payload.get("item_id")
                if isinstance(lease_id, str):
                    lease_by_id[lease_id] = payload
                if isinstance(item_id, str) and isinstance(lease_id, str):
                    leased_items[item_id] = lease_id
                if "IB-LINK-01" in enabled_checks and isinstance(item_id, str):
                    if item_id not in queued_items:
                        _add_failure(
                            failures,
                            "IB-LINK-01",
                            f"INBOX_LEASE_GRANT.item_id '{item_id}' must reference prior INBOX_ENQUEUE",
                            rel_file,
                            line_no,
                        )
                    elif isinstance(inbox_id, str) and queued_items[item_id] != inbox_id:
                        _add_failure(
                            failures,
                            "IB-LINK-01",
                            "INBOX_LEASE_GRANT.inbox_id must match enqueue inbox_id for item",
                            rel_file,
                            line_no,
                        )
                if "IB-LEASE-01" in enabled_checks:
                    if require_queue_lease_ref:
                        qref = payload.get("queue_lease_ref")
                        if not isinstance(qref, str) or not qref:
                            _add_failure(
                                failures,
                                "IB-LEASE-01",
                                "policy requires INBOX_LEASE_GRANT.queue_lease_ref",
                                rel_file,
                                line_no,
                            )
                    if require_admission_ref:
                        aref = payload.get("admission_ref")
                        if not isinstance(aref, str) or not aref:
                            _add_failure(
                                failures,
                                "IB-LEASE-01",
                                "policy requires INBOX_LEASE_GRANT.admission_ref",
                                rel_file,
                                line_no,
                            )
            elif mtype == "INBOX_ACK":
                item_id = payload.get("item_id")
                lease_id = payload.get("lease_id")
                if "IB-LINK-01" in enabled_checks:
                    if not isinstance(item_id, str) or item_id not in queued_items:
                        _add_failure(
                            failures,
                            "IB-LINK-01",
                            f"INBOX_ACK.item_id '{item_id}' must reference prior INBOX_ENQUEUE",
                            rel_file,
                            line_no,
                        )
                    if isinstance(lease_id, str):
                        if lease_id not in lease_by_id:
                            _add_failure(
                                failures,
                                "IB-LINK-01",
                                f"INBOX_ACK.lease_id '{lease_id}' must reference prior INBOX_LEASE_GRANT",
                                rel_file,
                                line_no,
                            )
                    else:
                        if isinstance(item_id, str) and item_id in leased_items:
                            _add_failure(
                                failures,
                                "IB-LINK-01",
                                "INBOX_ACK.lease_id required when item has active lease",
                                rel_file,
                                line_no,
                            )
