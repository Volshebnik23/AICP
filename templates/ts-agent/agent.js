import { createHash } from "node:crypto";

function sortDeep(value) {
  if (Array.isArray(value)) return value.map(sortDeep);
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = sortDeep(value[key]);
    return out;
  }
  return value;
}

function messageHashFromBody(body) {
  const canonical = JSON.stringify(sortDeep(body));
  const preimage = Buffer.concat([Buffer.from("AICP1\0message\0", "utf-8"), Buffer.from(canonical, "utf-8")]);
  return `sha256:${createHash("sha256").update(preimage).digest("base64url")}`;
}

function buildCoreMessage({ sessionId, messageId, timestamp, sender, contractId, contractRef, messageType, payload, prevMsgHash }) {
  const body = {
    session_id: sessionId,
    message_id: messageId,
    timestamp,
    sender,
    message_type: messageType,
    contract_id: contractId,
    contract_ref: contractRef,
    payload,
    ...(prevMsgHash ? { prev_msg_hash: prevMsgHash } : {}),
  };
  return { ...body, message_hash: messageHashFromBody(body) };
}

const contractId = "c-template-demo";
const contractRef = { branch_id: "main", base_version: "v1", head_version: "v1" };

const message = buildCoreMessage({
  sessionId: "s-template-demo",
  messageId: "m0001",
  timestamp: "t0001",
  sender: "agent:A",
  contractId,
  contractRef,
  messageType: "CONTRACT_PROPOSE",
  payload: {
    contract: {
      contract_id: contractId,
      goal: "template_minimal_demo",
      roles: ["initiator", "responder"],
      policies: [{ policy_id: "pol-001", category: "user_consent", parameters: {}, status: "active" }],
    },
  },
});

console.log(JSON.stringify(message, null, 2));
