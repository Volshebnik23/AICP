function rejectUnsupportedNumbers(value: unknown): void {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error("Unsupported non-finite float for canonicalization");
    }
    if (!Number.isInteger(value)) {
      throw new Error("Floats are not supported by AICP Core v0.1; see OQ-0001 / RFC8785 numeric handling");
    }
    return;
  }

  if (Array.isArray(value)) {
    for (const item of value) rejectUnsupportedNumbers(item);
    return;
  }

  if (value && typeof value === "object") {
    for (const item of Object.values(value as Record<string, unknown>)) {
      rejectUnsupportedNumbers(item);
    }
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

export function canonicalizeToBytes(value: unknown): Uint8Array {
  return new TextEncoder().encode(canonicalizeJson(value));
}
