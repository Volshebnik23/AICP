export function canonicalizeNumber(value: number): string {
  if (!Number.isFinite(value)) {
    throw new Error("Unsupported non-finite number for canonicalization");
  }

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
  const expRaw = raw.slice(expIndex + 1);
  const exponent = Number.parseInt(expRaw, 10);
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
  if (Array.isArray(value)) return `[${value.map((item) => serialize(item)).join(",")}]`;
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

export function canonicalizeToBytes(value: unknown): Uint8Array {
  return new TextEncoder().encode(canonicalizeJson(value));
}
