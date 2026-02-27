import { messageHashFromBody } from "../../sdk/typescript/src/hashing.js";

function buildMessage({ sessionId, messageId, messageType, payload, prevMsgHash }) {
  const body = {
    session_id: sessionId,
    message_id: messageId,
    message_type: messageType,
    payload,
    ...(prevMsgHash ? { prev_msg_hash: prevMsgHash } : {}),
  };

  const message_hash = messageHashFromBody(body);
  return { ...body, message_hash };
}

// copy-paste minimal thread with chain continuity.
const m1 = buildMessage({
  sessionId: "demo-session-1",
  messageId: "m-001",
  messageType: "CAPABILITIES_DECLARE",
  payload: { supported_profiles: ["core.v0.1"] },
});

const m2 = buildMessage({
  sessionId: "demo-session-1",
  messageId: "m-002",
  messageType: "CAPABILITIES_PROPOSE",
  payload: { proposed_profile: "core.v0.1" },
  prevMsgHash: m1.message_hash,
});

// Enforcement hook example (integrate your own policy engine/enforcer):
// - validate message against Core schema
// - validate profile/extension policy
// - verify signatures when present

console.log(JSON.stringify(m1));
console.log(JSON.stringify(m2));
