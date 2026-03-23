# AICP Python Reference ↔ TypeScript SDK Helper Parity

This note records the intentionally shared helper contract between:

- `reference/python/aicp_ref/`
- `sdk/typescript/src/`

It is deliberately narrow. The goal is to keep overlapping helpers explicit and testable without turning the TypeScript SDK into the full Python reference validator.

## Shared helper contract

| Helper area | Python reference | TypeScript SDK | Shared expectation |
| --- | --- | --- | --- |
| Canonicalization | `aicp_ref/jcs.py` | `src/jcs.ts` | Deterministic JSON canonicalization with lexicographic object-key sorting by Unicode code point order, UTF-8 output, safe-integer enforcement, finite-float support, and non-finite rejection. |
| Hashing | `aicp_ref/hashing.py` | `src/hashing.ts` | `sha256:` object/message hashes over `AICP1\0<object_type>\0<canonical-json>`. `message_hash` is computed from the message body excluding transport-added signature material. |
| Prev-hash chain helper | `aicp_ref/chain.py` | `src/chain.ts` | First transcript record may omit `prev_msg_hash`; each later record must include a non-empty `prev_msg_hash` equal to the immediately previous `message_hash`. |
| Fixture-backed overlap | Python tests + Core TVs | TypeScript tests + Core TVs | Shared helper behavior is anchored to `fixtures/core_tv.json` and regression tests instead of prose-only expectations. |

## Intentional boundary

The Python reference layer remains the stronger semantic helper surface.

Python-only checks currently include:

- transcript-level message-hash recomputation via `aicp_ref/validate.py`
- signature verification via `aicp_ref/signatures.py`
- signature `object_hash == message_hash` enforcement
- signer/`kid` consistency checks when signatures are present

The TypeScript SDK intentionally stays narrower:

- it exposes canonicalization, hashing, base64url helpers, and `prev_msg_hash` verification
- it does **not** attempt to be a full transcript validator or signature verifier

That split is intentional because the SDK is positioned as a minimal validator-focused helper surface, while the Python layer is the correctness-first reference implementation.

## Regression anchors added for drift prevention

- Unicode non-BMP key ordering is now tested explicitly so both surfaces stay aligned with the Core requirement to sort keys by Unicode code point order.
- `TV-03` is used as a shared hash + chain anchor so message-hash and `prev_msg_hash` overlap stays fixture-backed in both implementations.
