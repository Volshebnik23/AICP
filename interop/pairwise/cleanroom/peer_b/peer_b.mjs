#!/usr/bin/env node
// A standalone Node.js implementation used as the second M66 interoperability peer.

import { createHash, createPublicKey, verify as verifySignature } from "node:crypto";
import { readFileSync, readdirSync, renameSync, writeFileSync } from "node:fs";
import { basename, dirname, extname, join } from "node:path";
import { fileURLToPath } from "node:url";
import readline from "node:readline";

const CONTROL = "aicp.pairwise_control.v1";
const ADAPTER = "1.1";
const ID = "aicp-cleanroom-node-b";
const VERSION = "1.0.0-test";
const HERE = dirname(fileURLToPath(import.meta.url));
const CONTRACT_OBJECT = {
  contract_id: "cGT1",
  goal: "golden_demo",
  roles: ["initiator", "responder"],
};

function compareUnicode(left, right) {
  const a = Array.from(left, (character) => character.codePointAt(0));
  const b = Array.from(right, (character) => character.codePointAt(0));
  for (let index = 0; index < Math.min(a.length, b.length); index += 1) {
    if (a[index] !== b[index]) return a[index] - b[index];
  }
  return a.length - b.length;
}

function canonicalValue(value) {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value)) throw new Error("only safe integers are supported");
    return value;
  }
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (typeof value === "object") {
    const result = {};
    for (const key of Object.keys(value).sort(compareUnicode)) result[key] = canonicalValue(value[key]);
    return result;
  }
  throw new Error("unsupported JSON value");
}

function canonical(value) {
  return JSON.stringify(canonicalValue(value));
}

function b64url(bytes) {
  return Buffer.from(bytes).toString("base64url");
}

function typedHash(type, value) {
  const preimage = Buffer.concat([
    Buffer.from("AICP1\0", "utf8"),
    Buffer.from(type, "utf8"),
    Buffer.from("\0", "utf8"),
    Buffer.from(canonical(value), "utf8"),
  ]);
  return `sha256:${b64url(createHash("sha256").update(preimage).digest())}`;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function envelopeHash(envelope) {
  const body = clone(envelope);
  delete body.message_hash;
  delete body.signatures;
  return typedHash("message", body);
}

function sourceDigest() {
  const hash = createHash("sha256");
  for (const name of readdirSync(HERE).filter((item) => extname(item) === ".mjs").sort(compareUnicode)) {
    hash.update(Buffer.from(`${name}\0`, "utf8"));
    const normalized = readFileSync(join(HERE, name), "utf8").replace(/\r\n?/g, "\n");
    hash.update(Buffer.from(normalized, "utf8"));
    hash.update(Buffer.from("\0", "utf8"));
  }
  return `sha256:${hash.digest("hex")}`;
}

function makeEnvelope({ session, contract, id, sender, type, payload, previous = null, timestamp }) {
  const envelope = {
    session_id: session,
    message_id: id,
    timestamp,
    sender,
    message_type: type,
    contract_id: contract,
    contract_ref: { branch_id: "main", base_version: "v1", head_version: "v1" },
    payload,
  };
  if (previous !== null) envelope.prev_msg_hash = previous;
  envelope.message_hash = envelopeHash(envelope);
  return envelope;
}

function endpointDescriptor(role) {
  return {
    protocol: "aicp.live_endpoint_descriptor.v2",
    binding_id: "BIND-MCP",
    binding_version: "0.1",
    role,
    implementation_kind: "external_implementation",
    implementation_id: ID,
    implementation_version: VERSION,
    implementation_digest: sourceDigest(),
    declared_features: { request_response: true, sse: false, websocket: false, wss: false },
    transport: "stdio",
  };
}

function publishReady(role) {
  const destination = process.env.AICP_LIVE_READY_FILE;
  if (!destination) throw new Error("AICP_LIVE_READY_FILE is required");
  const temporary = `${destination}.tmp`;
  writeFileSync(temporary, canonical(endpointDescriptor(role)), { encoding: "utf8" });
  renameSync(temporary, destination);
}

function rpcResult(id, result) {
  return { jsonrpc: "2.0", id, result };
}

function rpcError(id, code, message) {
  return { jsonrpc: "2.0", id, error: { code, message } };
}

class Mailbox {
  constructor() {
    this.bySession = new Map();
    this.byId = new Map();
    this.cursorOffsets = new Map();
  }

  cursor(session, offset) {
    if (!this.cursorOffsets.has(session)) this.cursorOffsets.set(session, new Map([["c0", 0]]));
    const known = this.cursorOffsets.get(session);
    for (const [token, value] of known.entries()) if (value === offset) return token;
    const suffix = createHash("sha256").update(`${session}:${offset}`, "utf8").digest("hex").slice(0, 16);
    const token = `c${offset}-${suffix}`;
    known.set(token, offset);
    return token;
  }

  dispatch(request) {
    const requestId = request?.id ?? null;
    if (request?.jsonrpc !== "2.0" || request?.method !== "tools/call") return rpcError(requestId, -32600, "invalid request");
    const tool = request.params?.name;
    const args = request.params?.arguments;
    if (typeof args !== "object" || args === null || Array.isArray(args)) return rpcError(requestId, -32602, "invalid params");
    if (tool === "aicp.sendMessage") {
      const message = args.message;
      if (!message || ["session_id", "message_id", "message_hash"].some((field) => typeof message[field] !== "string" || !message[field])) {
        return rpcError(requestId, -32602, "invalid AICP envelope");
      }
      if (envelopeHash(message) !== message.message_hash) return rpcError(requestId, -32602, "message hash mismatch");
      const key = `${message.session_id}\0${message.message_id}`;
      const prior = this.byId.get(key);
      if (prior && canonical(prior) !== canonical(message)) return rpcError(requestId, -32602, "conflicting duplicate message id");
      if (!prior) {
        const stored = clone(message);
        this.byId.set(key, stored);
        if (!this.bySession.has(message.session_id)) this.bySession.set(message.session_id, []);
        this.bySession.get(message.session_id).push(stored);
      }
      return rpcResult(requestId, { accepted: true, message_id: message.message_id, message_hash: message.message_hash });
    }
    if (tool === "aicp.pollMessages") {
      if (typeof args.session_id !== "string" || typeof args.after_cursor !== "string") return rpcError(requestId, -32602, "session_id and after_cursor are required");
      if (!this.cursorOffsets.has(args.session_id)) this.cursorOffsets.set(args.session_id, new Map([["c0", 0]]));
      const cursors = this.cursorOffsets.get(args.session_id);
      if (!cursors.has(args.after_cursor)) return rpcError(requestId, -32602, "unknown after_cursor");
      const limit = Math.max(0, Math.min(Number.isSafeInteger(args.limit) ? args.limit : 1000, 1000));
      const offset = cursors.get(args.after_cursor);
      const selected = clone((this.bySession.get(args.session_id) ?? []).slice(offset, offset + limit));
      return rpcResult(requestId, { messages: selected, next_cursor: this.cursor(args.session_id, offset + selected.length) });
    }
    if (tool === "aicp.getHead") {
      const session = String(args.session_id ?? "");
      const messages = this.bySession.get(session) ?? [];
      return rpcResult(requestId, {
        session_state: { session_id: session },
        branch_heads: [{ branch_id: "main", head_message_id: messages.at(-1)?.message_id ?? null }],
        active_head_version: "v1",
      });
    }
    if (tool === "aicp.getObject") {
      const expected = typedHash("contract", CONTRACT_OBJECT);
      if (args.object_hash !== expected) return rpcResult(requestId, { status: "NOT_FOUND" });
      return rpcResult(requestId, { status: "FOUND", object_type: "contract", object_json: CONTRACT_OBJECT });
    }
    return rpcError(requestId, -32601, "tool not found");
  }
}

async function lineLoop(handler) {
  const lines = readline.createInterface({ input: process.stdin, crlfDelay: Infinity, terminal: false });
  let count = 0;
  for await (const line of lines) {
    count += 1;
    if (count > 256 || Buffer.byteLength(line, "utf8") > 1_048_576) process.exitCode = 2;
    if (process.exitCode) break;
    let response;
    try {
      const request = JSON.parse(line);
      response = handler(request);
      if (response instanceof Promise) response = await response;
    } catch (error) {
      response = rpcError(null, -32700, "parse error");
    }
    process.stdout.write(`${canonical(response)}\n`);
  }
}

async function serverLoop() {
  const mailbox = new Mailbox();
  await lineLoop((request) => mailbox.dispatch(request));
}

function call(id, name, args) {
  return { jsonrpc: "2.0", id, method: "tools/call", params: { name, arguments: args } };
}

async function bindingClient() {
  const scenario = JSON.parse(readFileSync(process.env.AICP_LIVE_SCENARIO_FILE, "utf8"));
  const messages = scenario.input_messages.map((source) => {
    const message = clone(source);
    message.session_id = "sGT1";
    delete message.signatures;
    delete message.message_hash;
    message.message_hash = envelopeHash(message);
    return message;
  });
  const first = [
    call("rpc-send-1", "aicp.sendMessage", { message: messages[0] }),
    call("rpc-send-2", "aicp.sendMessage", { message: messages[0] }),
    call("rpc-send-3", "aicp.sendMessage", { message: messages[1] }),
    call("rpc-poll-1", "aicp.pollMessages", { session_id: "sGT1", after_cursor: "c0", limit: 1 }),
  ];
  const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity, terminal: false });
  const iterator = input[Symbol.asyncIterator]();
  let lastResponse;
  for (const request of first) {
    process.stdout.write(`${canonical(request)}\n`);
    const item = await iterator.next();
    if (item.done) throw new Error("binding runner closed before response");
    lastResponse = JSON.parse(item.value);
  }
  const cursor = lastResponse.result.next_cursor;
  const remaining = [
    call("rpc-poll-2", "aicp.pollMessages", { session_id: "sGT1", after_cursor: cursor, limit: 1 }),
    call("rpc-head-1", "aicp.getHead", { session_id: "sGT1" }),
    call("rpc-object-1", "aicp.getObject", { object_hash: typedHash("contract", CONTRACT_OBJECT) }),
    call("rpc-object-2", "aicp.getObject", { object_hash: `sha256:${"A".repeat(43)}` }),
    call("rpc-invalid-1", "aicp.sendMessage", { message: { session_id: "sGT1" } }),
  ];
  for (const request of remaining) {
    process.stdout.write(`${canonical(request)}\n`);
    const item = await iterator.next();
    if (item.done) throw new Error("binding runner closed before response");
  }
  input.close();
}

function createProducerTranscript(scenario) {
  const output = [];
  const amendments = [];
  let prior = null;
  for (let index = 0; index < scenario.desired_message_types.length; index += 1) {
    const type = scenario.desired_message_types[index];
    const ordinal = index + 1;
    let payload;
    if (type === "CONTRACT_PROPOSE") {
      const contract = { contract_id: scenario.contract_id, goal: scenario.deterministic_seed, roles: [...scenario.participants] };
      if (scenario.deterministic_seed.includes("consent-grant")) contract.policies = [{ policy_id: "consent", category: "user_consent", parameters: { required: true, scope: "share_profile" }, status: "active" }];
      if (scenario.deterministic_seed.includes("consent-revoke")) contract.policies = [{ policy_id: "consent", category: "user_consent", parameters: { required: true, scope: "payments" }, status: "active" }];
      payload = { contract, contract_hash: typedHash("contract", contract) };
    } else if (type === "CONTRACT_ACCEPT") payload = { accepted: true };
    else if (type === "CONTEXT_AMEND") {
      if (scenario.deterministic_seed.includes("consent-grant")) payload = { amendment: { consent_ref: "consent:a", consent_status: "granted", consent_scope: "share_profile" } };
      else if (scenario.deterministic_seed.includes("consent-revoke")) {
        payload = amendments.length === 0
          ? { amendment: { consent_ref: "consent:a", consent_status: "granted", consent_scope: "payments" } }
          : { amendment: { consent_ref: "consent:a", consent_status: "revoked", reason: "user_revoked" } };
      } else payload = { amendment: { amend_id: `a${ordinal}`, base_version: "v1", changes: { choice: ordinal } } };
      amendments.push(`m${ordinal}`);
    } else if (type === "RESOLVE_CONFLICT") {
      const candidates = amendments.slice(-2).map((messageId) => ({ message_id: messageId, message_hash: output[Number(messageId.slice(1)) - 1].message_hash }));
      payload = { conflict_id: "conflict-a", conflict_class: "CONCURRENT_AMEND", candidates, resolution: { type: "CHOOSE", chosen_message_id: candidates[0].message_id, chosen_message_hash: candidates[0].message_hash } };
    } else if (type === "STATE_SYNC_REQUEST") payload = { request_id: "sync-a", known_heads: ["v999"] };
    else if (type === "STATE_SYNC_RESPONSE") payload = { request_id: "sync-a", session_state: "active", branch_heads: ["v1"], active_head_version: "v1" };
    else if (type === "ATTEST_ACTION") {
      if (scenario.deterministic_seed.includes("consent-grant")) payload = { action_id: "act-a", action_type: "share_profile", consent_ref: "consent:a" };
      else if (scenario.deterministic_seed.includes("consent-revoke")) payload = { action_id: "act-a", action_type: "payment_attempt", consent_ref: "consent:a" };
      else payload = { action_id: "act-a", action_type: "tools/call", result_hash: typedHash("result", { seed: scenario.deterministic_seed }) };
    } else if (type === "ERROR") payload = { error_code: "TEST_ERROR", error_class: "VALIDATION", severity: "low", applies_to: { message_id: "none" }, disposition: "REJECTED" };
    else throw new Error(`unsupported producer message type: ${type}`);
    const message = makeEnvelope({
      session: String(scenario.session_id), contract: String(scenario.contract_id), id: `m${ordinal}`,
      sender: ordinal % 2 === 1 ? "agent:A" : "agent:B", type, payload, previous: prior,
      timestamp: `2026-01-01T00:00:${String(ordinal).padStart(2, "0")}Z`,
    });
    output.push(message);
    prior = message.message_hash;
  }
  return output;
}

function checkSignatures(message, materials) {
  if (!message.signatures) return true;
  try {
    for (const signature of message.signatures) {
      if (signature.object_type !== "message" || signature.object_hash !== message.message_hash) return false;
      const material = materials[signature.signer];
      if (!material || material.kid !== signature.kid) return false;
      const raw = Buffer.from(material.public_key_b64url, "base64url");
      const prefix = Buffer.from("302a300506032b6570032100", "hex");
      const key = createPublicKey({ key: Buffer.concat([prefix, raw]), format: "der", type: "spki" });
      const signed = Buffer.from(`AICP1\0SIG\0${message.message_hash}`, "utf8");
      if (!verifySignature(null, signed, key, Buffer.from(signature.sig_b64url, "base64url"))) return false;
    }
    return true;
  } catch {
    return false;
  }
}

function inspectTranscript(input) {
  const errors = [];
  if (!Array.isArray(input.transcript)) errors.push({ code: "schema", message: "transcript must be an array" });
  else {
    const seen = new Set();
    let prior = null;
    input.transcript.forEach((message, index) => {
      if (!message || typeof message !== "object" || Array.isArray(message)) {
        errors.push({ code: "schema", message: `message ${index} is not an object` });
        return;
      }
      for (const field of ["session_id", "message_id", "timestamp", "sender", "message_type", "contract_id"]) {
        if (typeof message[field] !== "string" || message[field].length === 0) errors.push({ code: "schema", message: `message ${index} has invalid ${field}` });
      }
      if (seen.has(message.message_id)) errors.push({ code: "replay", message: "duplicate message_id" });
      seen.add(message.message_id);
      if (index > 0 && message.prev_msg_hash !== prior) errors.push({ code: "chain", message: "prev_msg_hash mismatch" });
      if (message.message_hash !== envelopeHash(message)) errors.push({ code: "hash", message: "message_hash mismatch" });
      if (!checkSignatures(message, input.public_verification_material ?? {})) errors.push({ code: "signature", message: "signature verification failed" });
      prior = message.message_hash;
    });
  }
  return { accepted: errors.length === 0, errors, degraded: false, degraded_reasons: [], skipped_checks: [] };
}

function iutResponse(request) {
  const operation = request.operation;
  const input = request.input ?? {};
  let result;
  if (operation === "describe") result = {
    adapter_protocol_version: ADAPTER, implementation_kind: "external_implementation", implementation_id: ID,
    implementation_version: VERSION, implementation_digest: sourceDigest(), supported_aicp_profiles: ["AICP-BASE@0.1"],
    supported_crypto_profiles: ["aicp.crypto.ed25519.v1"], supported_capabilities: [],
  };
  else if (operation === "canonicalize_hash") result = { canonical_json: canonical(input.object), object_hash: typedHash(String(input.object_type), input.object) };
  else if (operation === "validate_transcript") result = inspectTranscript(input);
  else if (operation === "generate_scenario") result = { artifact: createProducerTranscript(input.scenario) };
  else throw new Error(`unsupported operation: ${operation}`);
  return { adapter_protocol_version: ADAPTER, request_id: request.request_id, operation, success: true, result };
}

function pairwiseMessage(request, behavior) {
  const input = request.input ?? {};
  let payload;
  let previous = null;
  let type;
  if (input.phase === "propose") {
    const contract = { contract_id: String(input.contract_id), goal: String(input.challenge), roles: ["initiator", "responder"] };
    if (behavior === "missing_contract_goal") delete contract.goal;
    else if (["ignore_challenge", "prebuilt_proposal"].includes(behavior)) contract.goal = "static-prebuilt-pairwise-goal";
    else if (behavior === "previous_run_challenge") contract.goal = "challenge-from-a-previous-run";
    payload = { contract, contract_hash: typedHash("contract", contract) };
    type = "CONTRACT_PROPOSE";
  } else if (input.phase === "accept") {
    if (!input.peer_message || input.peer_message.message_type !== "CONTRACT_PROPOSE" || envelopeHash(input.peer_message) !== input.peer_message.message_hash) throw new Error("actual valid proposal required");
    payload = { accepted: true };
    previous = input.peer_message.message_hash;
    type = "CONTRACT_ACCEPT";
  } else if (input.phase === "attest") {
    if (!input.peer_message || input.peer_message.message_type !== "CONTRACT_ACCEPT" || envelopeHash(input.peer_message) !== input.peer_message.message_hash) throw new Error("actual valid acceptance required");
    payload = { action_id: `${input.run_id}:${input.side}:final`, action_type: "pairwise_cross_consumption", result_hash: typedHash("result", { peer_hash: input.peer_message.message_hash }) };
    previous = input.peer_message.message_hash;
    type = "ATTEST_ACTION";
  } else throw new Error("unsupported construction phase");
  if (behavior === "hardcoded_hash" && input.phase !== "propose") previous = `sha256:${"A".repeat(43)}`;
  const message = makeEnvelope({ session: String(input.session_id), contract: String(input.contract_id), id: String(input.message_id), sender: ID, type, payload, previous, timestamp: String(input.timestamp) });
  if (behavior === "wrong_session" && input.phase !== "propose") {
    message.session_id = "wrong-session";
    message.message_hash = envelopeHash(message);
  }
  if (behavior === "wrong_contract" && input.phase !== "propose") {
    message.contract_id = "wrong-contract";
    message.message_hash = envelopeHash(message);
  }
  if (behavior === "malformed_contract_ref" && input.phase === "propose") {
    message.contract_ref = { branch_id: "main" };
    message.message_hash = envelopeHash(message);
  }
  if (behavior === "invalid_contract_accept_payload" && input.phase === "accept") {
    message.payload = { accepted: true, unexpected: "not-in-Core-v0.1" };
    message.message_hash = envelopeHash(message);
  }
  if (behavior === "invalid_attest_action_payload" && input.phase === "attest") {
    message.payload.unexpected = "not-in-Core-v0.1";
    message.message_hash = envelopeHash(message);
  }
  return message;
}

function controlResponse(request, behavior) {
  if (request.control_version !== CONTROL) throw new Error("unsupported control version");
  let result;
  if (request.operation === "describe") result = {
    implementation_kind: "external_implementation", implementation_id: ID, implementation_version: VERSION,
    implementation_digest: sourceDigest(), supported_target: "AICP-BASE@0.1+BIND-MCP@0.1",
  };
  else if (request.operation === "construct") result = { message: pairwiseMessage(request, behavior) };
  else throw new Error(`unsupported control operation: ${request.operation}`);
  return { control_version: CONTROL, request_id: request.request_id, operation: request.operation, success: true, result };
}

async function adapterLoop(kind, behavior = "good") {
  await lineLoop((request) => {
    try {
      return kind === "iut" ? iutResponse(request) : controlResponse(request, behavior);
    } catch (error) {
      return kind === "iut"
        ? { adapter_protocol_version: ADAPTER, request_id: request?.request_id, operation: request?.operation, success: false, error: { code: "adapter_error", message: String(error.message) } }
        : { control_version: CONTROL, request_id: request?.request_id, operation: request?.operation, success: false, error: { code: "peer_error", message: String(error.message) } };
    }
  });
}

async function main() {
  const [mode, ...rest] = process.argv.slice(2);
  const behaviorIndex = rest.indexOf("--behavior");
  const behavior = behaviorIndex >= 0 ? rest[behaviorIndex + 1] : "good";
  if (mode === "iut") await adapterLoop("iut");
  else if (mode === "binding-server") { publishReady("server_under_test"); await serverLoop(); }
  else if (mode === "binding-client") { publishReady("client_under_test"); await bindingClient(); }
  else if (mode === "pairwise-server") await serverLoop();
  else if (mode === "pairwise-control") await adapterLoop("control", behavior);
  else if (mode === "self-test") {
    if (typedHash("contract", CONTRACT_OBJECT) !== "sha256:wKY_CpI6-HtaTMTpufl-eTjXYQXv8Igzv7DFBjdDkS4") throw new Error("canonical hashing self-test failed");
    process.stdout.write("peer B self-test passed\n");
  } else throw new Error("expected iut, binding-server, binding-client, pairwise-server, pairwise-control, or self-test");
}

await main();
