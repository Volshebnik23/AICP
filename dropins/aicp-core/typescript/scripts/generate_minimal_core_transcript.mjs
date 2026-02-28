import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { buildCoreMessage } from "../src/aicp_core.mjs";

const outIdx = process.argv.indexOf("--out");
const outPath = outIdx >= 0 ? process.argv[outIdx + 1] : "out/minimal_core.jsonl";

const contract_id = "c-quickstart";
const contract_ref = { branch_id: "main", base_version: "v1", head_version: "v1" };

const m1 = buildCoreMessage({
  session_id: "s-quickstart",
  message_id: "m0001",
  timestamp: "t0001",
  sender: "agent:A",
  message_type: "CONTRACT_PROPOSE",
  contract_id,
  contract_ref,
  payload: {
    contract: {
      contract_id,
      goal: "minimal_quickstart",
      roles: ["initiator", "responder"],
      policies: [{ policy_id: "pol-001", category: "user_consent", parameters: {}, status: "active" }],
    },
  },
});

const m2 = buildCoreMessage({
  session_id: "s-quickstart",
  message_id: "m0002",
  timestamp: "t0002",
  sender: "agent:B",
  message_type: "CONTRACT_ACCEPT",
  contract_id,
  contract_ref,
  payload: { accepted: true },
  prev_msg_hash: m1.message_hash,
});

const m3 = buildCoreMessage({
  session_id: "s-quickstart",
  message_id: "m0003",
  timestamp: "t0003",
  sender: "agent:A",
  message_type: "CONTEXT_AMEND",
  contract_id,
  contract_ref,
  payload: { amendment: { note: "minimal_update" } },
  prev_msg_hash: m2.message_hash,
});

const out = resolve(outPath);
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, [m1, m2, m3].map((m) => JSON.stringify(m)).join("\n") + "\n", "utf-8");
console.log(`Wrote 3 records to ${out}`);
