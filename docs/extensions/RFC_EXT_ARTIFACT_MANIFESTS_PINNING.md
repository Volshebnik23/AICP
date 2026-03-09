# RFC: EXT-ARTIFACT-MANIFESTS-PINNING (M30 baseline)

## Scope
`EXT-ARTIFACT-MANIFESTS-PINNING` defines baseline artifact-manifest pinning semantics for tools/resources/prompts so contracts can bind execution to immutable, issuer-scoped manifest digests.

## Registry entry
- Extension ID: `EXT-ARTIFACT-MANIFESTS-PINNING`
- Compatibility mark family: `AICP-EXT-ARTIFACT-MANIFESTS-PINNING-*`

## Security considerations
Implementations MUST verify manifest digest integrity and issuer-scoped identifiers before admitting pinned artifacts to execution policy.
