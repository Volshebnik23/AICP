#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../..");
const source = path.join(
  root,
  "fixtures/extensions/capneg_v0_2/positive_cases.json",
);
const args = process.argv.slice(2);
const outIndex = args.indexOf("--out");
const relativeOut =
  outIndex >= 0 && args[outIndex + 1]
    ? args[outIndex + 1]
    : "out/quickstart/capneg-v02-ts/profile-composition.jsonl";
const catalog = JSON.parse(fs.readFileSync(source, "utf8"));
const fixture = catalog.cases.find((entry) => entry.id === "P09");
if (!fixture) {
  throw new Error("generated quickstart case P09 is missing");
}
const output = path.resolve(root, relativeOut);
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(
  output,
  fixture.messages.map((message) => JSON.stringify(message)).join("\n") + "\n",
  "utf8",
);
console.log(
  `Generated CAPNEG v0.2 TypeScript quickstart: ${path.relative(root, output)}`,
);
