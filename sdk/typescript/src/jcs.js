function rejectUnsupportedNumbers(value) {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error("Unsupported non-finite float for canonicalization");
    }
    if (!Number.isInteger(value)) {
      throw new Error("Float canonicalization beyond current fixture scope is not implemented");
    }
    return;
  }

  if (Array.isArray(value)) {
    for (const item of value) rejectUnsupportedNumbers(item);
    return;
  }

  if (value && typeof value === "object") {
    for (const item of Object.values(value)) rejectUnsupportedNumbers(item);
  }
}

function sortDeep(value) {
  if (Array.isArray(value)) return value.map(sortDeep);
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      out[key] = sortDeep(value[key]);
    }
    return out;
  }
  return value;
}

export function canonicalizeJson(value) {
  rejectUnsupportedNumbers(value);
  return JSON.stringify(sortDeep(value));
}

export function canonicalizeToBytes(value) {
  return new TextEncoder().encode(canonicalizeJson(value));
}
