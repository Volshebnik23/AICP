# AICP Plugfest Interoperability Kit

AICP plugfest submissions let independent implementations prove interoperability using the same conformance and profile reports.

## What is an AICP plugfest?
A plugfest is a coordinated interoperability exercise where multiple independent implementations run the same conformance/profile suites and submit machine-readable results for transparent comparison.

## Required submission artifacts
Each submission must include:
1. **Conformance/profile reports (JSON)** generated from this repository's runners.
2. **Implementation manifest (`implementation.json`)** describing identity, language/runtime, version, and contact.

## Generate reports locally
From the repository root:

```bash
make conformance-all
```

This produces report files under `conformance/`, including `conformance/report*.json` outputs.

## Submit results
1. Create a folder:
   - `interop/submissions/<implementation_id>/`
2. Add implementation manifest:
   - `interop/submissions/<implementation_id>/implementation.json`
3. Add report files:
   - `interop/submissions/<implementation_id>/reports/*.json`
   - Copy selected `conformance/report*.json` outputs.
4. Open a pull request.

## Aggregation into the interop matrix
Run:

```bash
make interop-matrix
```

This aggregates all submission manifests and reports into:
- `interop/interop_matrix.json` (machine-readable)
- `interop/INTEROP_MATRIX.md` (human-readable matrix)


## Before you submit (checklist)
- Run `make conformance-all` (optional but recommended).
- Copy report JSON files into `interop/submissions/<implementation_id>/reports/`.
- Ensure folder name equals `implementation.json:implementation_id`.
- Run `make interop-matrix`.
- Commit `interop/INTEROP_MATRIX.md` and `interop/interop_matrix.json` (CI will enforce freshness).
