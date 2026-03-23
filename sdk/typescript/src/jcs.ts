function rejectUnsupportedNumbers(value: unknown): void {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error("Unsupported non-finite float for canonicalization");
    }
    if (!Number.isSafeInteger(value)) {
      if (Number.isInteger(value)) {
        throw new Error("Integers outside IEEE-754 safe range are not supported by AICP Core v0.1");
      }
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

function compareUnicodeCodePointOrder(left: string, right: string): number {
  const leftPoints = Array.from(left);
  const rightPoints = Array.from(right);
  const limit = Math.min(leftPoints.length, rightPoints.length);

  for (let i = 0; i < limit; i += 1) {
    const leftPoint = leftPoints[i].codePointAt(0)!;
    const rightPoint = rightPoints[i].codePointAt(0)!;
    if (leftPoint !== rightPoint) {
      return leftPoint - rightPoint;
    }
  }

  return leftPoints.length - rightPoints.length;
}

function sortDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortDeep);
  if (value && typeof value === "object") {
    const src = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(src).sort(compareUnicodeCodePointOrder)) {
      out[key] = sortDeep(src[key]);
    }
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
