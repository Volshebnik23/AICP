import { createHash } from "node:crypto";

export const CORE_MESSAGE_TYPES = new Set([
  "CONTRACT_PROPOSE",
  "CONTRACT_ACCEPT",
  "CONTEXT_AMEND",
  "ATTEST_ACTION",
  "RESOLVE_CONFLICT",
  "ERROR",
]);

function rejectUnsupportedNumbers(value) {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("Unsupported non-finite float");
    if (Number.isInteger(value) && !Number.isSafeInteger(value)) {
      throw new Error("Integers outside IEEE-754 safe range are not supported by AICP Core v0.1");
    }
    return;
  }
  if (Array.isArray(value)) {
    value.forEach(rejectUnsupportedNumbers);
    return;
  }
  if (value && typeof value === "object") {
    Object.values(value).forEach(rejectUnsupportedNumbers);
  }
}

function sortDeep(value) {
  if (Array.isArray(value)) return value.map(sortDeep);
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = sortDeep(value[key]);
    return out;
  }
  return value;
}

export function canonicalizeJson(value) {
  rejectUnsupportedNumbers(value);
  return JSON.stringify(sortDeep(value));
}

function b64urlNoPad(input) {
  return input.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function objectHash(objectType, objectValue) {
  const canonical = Buffer.from(canonicalizeJson(objectValue), "utf-8");
  const prefix = Buffer.from(`AICP1\0${objectType}\0`, "utf-8");
  const digest = createHash("sha256").update(Buffer.concat([prefix, canonical])).digest();
  return `sha256:${b64urlNoPad(digest)}`;
}

export function messageHashFromBody(body) {
  return objectHash("message", body);
}

export function buildCoreMessage(params) {
  if (!CORE_MESSAGE_TYPES.has(params.message_type)) {
    throw new Error(`Unsupported core message_type: ${params.message_type}`);
  }
  const body = {
    session_id: params.session_id,
    message_id: params.message_id,
    timestamp: params.timestamp,
    sender: params.sender,
    message_type: params.message_type,
    contract_id: params.contract_id,
    contract_ref: params.contract_ref,
    payload: params.payload,
  };
  if (params.prev_msg_hash) body.prev_msg_hash = params.prev_msg_hash;
  return { ...body, message_hash: messageHashFromBody(body) };
}
