import { createHash } from "node:crypto";

export type Json = null | boolean | number | string | Json[] | { [k: string]: Json };

export const CORE_MESSAGE_TYPES = new Set([
  "CONTRACT_PROPOSE",
  "CONTRACT_ACCEPT",
  "CONTEXT_AMEND",
  "ATTEST_ACTION",
  "RESOLVE_CONFLICT",
  "ERROR",
]);

function rejectUnsupportedNumbers(value: unknown): void {
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
    Object.values(value as Record<string, unknown>).forEach(rejectUnsupportedNumbers);
  }
}

function sortDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortDeep);
  if (value && typeof value === "object") {
    const src = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(src).sort()) out[key] = sortDeep(src[key]);
    return out;
  }
  return value;
}

export function canonicalizeJson(value: unknown): string {
  rejectUnsupportedNumbers(value);
  return JSON.stringify(sortDeep(value));
}

function b64urlNoPad(input: Buffer): string {
  return input.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function objectHash(objectType: string, objectValue: unknown): string {
  const canonical = Buffer.from(canonicalizeJson(objectValue), "utf-8");
  const prefix = Buffer.from(`AICP1\0${objectType}\0`, "utf-8");
  const digest = createHash("sha256").update(Buffer.concat([prefix, canonical])).digest();
  return `sha256:${b64urlNoPad(digest)}`;
}

export function messageHashFromBody(body: Record<string, unknown>): string {
  return objectHash("message", body);
}

export function buildCoreMessage(params: {
  session_id: string;
  message_id: string;
  timestamp: string;
  sender: string;
  message_type: string;
  payload: Record<string, unknown>;
  contract_id: string;
  contract_ref: { branch_id: string; base_version: string; head_version: string };
  prev_msg_hash?: string;
}): Record<string, unknown> {
  if (!CORE_MESSAGE_TYPES.has(params.message_type)) {
    throw new Error(`Unsupported core message_type: ${params.message_type}`);
  }
  const body: Record<string, unknown> = {
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
