import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";

function canonical(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
}

function objectHash(objectType, value) {
  const preimage = Buffer.concat([
    Buffer.from(`AICP1\0${objectType}\0`, "utf8"),
    Buffer.from(canonical(value), "utf8"),
  ]);
  return `sha256:${createHash("sha256").update(preimage).digest("base64url")}`;
}

function addHashes(messages) {
  let previous = null;
  for (const message of messages) {
    delete message.prev_msg_hash;
    delete message.message_hash;
    if (previous !== null) message.prev_msg_hash = previous;
    message.message_hash = objectHash("message", message);
    previous = message.message_hash;
  }
}

function buildTranscript() {
  const contract = {
    contract_id: "quickstart-core-v02",
    contract_version: "v1",
    goal: "Demonstrate exact contract agreement",
    roles: ["initiator", "responder"],
  };
  const contractHash = objectHash("contract", contract);
  const transitionRef = {
    branch_id: "main",
    head: { version: "v1", contract_hash: contractHash },
  };
  const currentRef = structuredClone(transitionRef);
  const common = {
    session_id: "quickstart-core-v02-session",
    contract_id: contract.contract_id,
  };
  const proposal = {
    ...common,
    message_id: "core-v02-proposal",
    timestamp: "2026-01-01T00:00:00Z",
    sender: "agent://initiator",
    message_type: "CONTRACT_PROPOSE",
    contract_ref: transitionRef,
    payload: { contract, contract_hash: contractHash },
  };
  proposal.message_hash = objectHash("message", proposal);
  const acceptance = {
    ...common,
    message_id: "core-v02-acceptance",
    timestamp: "2026-01-01T00:00:01Z",
    sender: "agent://responder",
    message_type: "CONTRACT_ACCEPT",
    contract_ref: transitionRef,
    payload: {
      accepted: true,
      proposal_message_id: proposal.message_id,
      proposal_message_hash: proposal.message_hash,
      contract_hash: contractHash,
    },
  };
  const action = {
    ...common,
    message_id: "core-v02-action",
    timestamp: "2026-01-01T00:00:02Z",
    sender: "agent://initiator",
    message_type: "ATTEST_ACTION",
    contract_ref: currentRef,
    payload: {
      action_id: "quickstart-action",
      action_type: "DEMO",
      result_hash: contractHash,
    },
  };
  const messages = [proposal, acceptance, action];
  addHashes(messages);
  acceptance.payload.proposal_message_hash = proposal.message_hash;
  addHashes(messages);
  return messages;
}

const outIndex = process.argv.indexOf("--out");
if (outIndex < 0 || !process.argv[outIndex + 1]) {
  throw new Error("usage: node generate_exact_contract_transcript.mjs --out <path>");
}
const output = path.resolve(process.argv[outIndex + 1]);
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(
  output,
  `${buildTranscript().map((message) => JSON.stringify(message)).join("\n")}\n`,
  "utf8",
);
console.log(`Wrote Core v0.2 exact-agreement transcript: ${output}`);
