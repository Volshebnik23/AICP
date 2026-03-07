import { messageHashFromBody } from "../../sdk/typescript/src/hashing.js";

function buildCoreMessage({
  sessionId,
  messageId,
  timestamp,
  sender,
  contractId,
  contractRef,
  messageType,
  payload,
  prevMsgHash,
}) {
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

const m1 = buildCoreMessage({
  sessionId: "s-template-demo",
  messageId: "m0001",
  timestamp: "2026-01-01T00:00:00Z",
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

const m2 = buildCoreMessage({
  sessionId: "s-template-demo",
  messageId: "m0002",
  timestamp: "2026-01-01T00:00:01Z",
  sender: "agent:B",
  contractId,
  contractRef,
  messageType: "CONTRACT_ACCEPT",
  payload: { accepted: true },
  prevMsgHash: m1.message_hash,
});

for (const message of [m1, m2]) {
  process.stdout.write(`${JSON.stringify(message)}\n`);
}
