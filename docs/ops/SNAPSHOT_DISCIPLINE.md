# Snapshot discipline (M10)

AICP snapshot manifests provide a deterministic release-time fingerprint of shipped protocol artifacts.

## What the snapshot covers

The snapshot manifest at `dist/releases/snapshots/AICP_SNAPSHOT_0.1.0-dev.json` records, per artifact set:

- file path
- per-file sha256
- deterministic combined sha256 over sorted `<sha256> <path>\n` lines

Covered sets:

- `registry/*.json`
- `schemas/**/*.json`
- `conformance/**/*.json`
- `fixtures/**/*.json` and `fixtures/**/*.jsonl`

It also records compatibility marks from conformance suites and profiles.

## Why this exists

Snapshot discipline improves:

- release candidate integrity checks,
- interop reproducibility,
- external auditability of protocol artifacts.

## How to update

When protocol artifacts change, regenerate and validate:

```bash
make snapshot
make validate
```

## Policy

Any PR changing registries, schemas, conformance suites, or fixtures MUST update the snapshot manifest.

Local-only escape hatch: set `AICP_SKIP_SNAPSHOT=1` to skip snapshot validation while iterating; CI should not set this variable.
