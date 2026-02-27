import { createHash } from "node:crypto";
import { base64UrlNoPad } from "./base64url.js";
import { canonicalizeToBytes } from "./jcs.js";

export function objectHash(objectType: string, objectValue: unknown): string {
  const canonical = canonicalizeToBytes(objectValue);
  const prefix = new TextEncoder().encode(`AICP1\0${objectType}\0`);
  const preimage = Buffer.concat([Buffer.from(prefix), Buffer.from(canonical)]);
  const digest = createHash("sha256").update(preimage).digest();
  return `sha256:${base64UrlNoPad(digest)}`;
}

export function messageHashFromBody(messageBody: Record<string, unknown>): string {
  return objectHash("message", messageBody);
}
