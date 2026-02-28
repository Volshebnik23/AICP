# Interop submissions folder contract

Each implementation submission must follow:

- `interop/submissions/<implementation_id>/implementation.json`
- `interop/submissions/<implementation_id>/reports/*.json`

Where:
- `<implementation_id>` should be stable and lowercase-with-dashes when possible.
- Folder name **MUST** match `implementation.json:implementation_id` exactly.
- `implementation.json` should follow `interop/schemas/implementation_manifest.schema.json`.
- `reports/*.json` should contain conformance/profile report outputs generated from this repo tooling.


CI validates changed implementation manifests against the schema.
Run locally if needed:
`python interop/tools/validate_manifests.py --schema interop/schemas/implementation_manifest.schema.json interop/submissions/<implementation_id>/implementation.json`
