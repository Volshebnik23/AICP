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

export function canonicalizeNumber(value: number): string {
  if (!Number.isFinite(value)) throw new Error("Unsupported non-finite number for canonicalization");
  if (Object.is(value, -0) || value === 0) return "0";

  if (Number.isInteger(value)) {
    if (!Number.isSafeInteger(value)) {
      throw new Error("Unsafe integer for AICP canonicalization (must be within IEEE-754 safe integer range)");
    }
    return String(value);
  }

  const raw = value.toString().replace("E", "e");
  const expIndex = raw.indexOf("e");
  if (expIndex < 0) return raw;

  const mantissa = raw.slice(0, expIndex);
  const exponent = Number.parseInt(raw.slice(expIndex + 1), 10);
  return `${mantissa}e${exponent}`;
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

function serialize(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number") return canonicalizeNumber(value);
  if (Array.isArray(value)) return `[${value.map((v) => serialize(v)).join(",")}]`;
  if (value && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    return `{${keys.map((key) => `${JSON.stringify(key)}:${serialize(obj[key])}`).join(",")}}`;
  }
  throw new Error(`Unsupported value type for canonicalization: ${typeof value}`);
}

export function canonicalizeJson(value: unknown): string {
  return serialize(sortDeep(value));
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
