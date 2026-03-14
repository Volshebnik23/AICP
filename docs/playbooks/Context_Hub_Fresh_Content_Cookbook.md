# Context Hub Fresh-Content Cookbook (Adjacent System)

This cookbook describes a safe integration pattern for using an adjacent fresh-content system (Context Hub) in an AICP-governed workflow.

## Important boundary

- **AICP** is the governed shared context/transcript protocol.
- **Context Hub** is an adjacent content/docs/skills source.

Do not treat Context Hub state as implicitly shared session truth unless it is explicitly recorded in AICP transcript/workflow artifacts.

## Why/when to query fresh content

Use adjacent fresh-content lookup when:
- policy/runbook/tool docs change frequently,
- execution safety depends on latest published operational guidance,
- local cache age exceeds your freshness SLO for the action class.

Use cached/local knowledge when:
- the action is low-risk and cache is within freshness budget,
- external source is unavailable and fallback policy allows cached mode,
- deterministic replay requires fixed previously-selected artifacts.

## Provenance recording pattern (required)

When content is selected from an adjacent system, record (in workflow state or transcript ext object):
- source system identifier,
- selected document/skill identifier,
- selected version/revision/hash,
- language/variant (if applicable),
- retrieval timestamp,
- trust class (e.g., pinned-approved / unpinned-reference).

This prevents hidden local-only dependency and makes decisions externally auditable.

## End-to-end scenario (fresh then governed)

1. Agent needs up-to-date remediation runbook before a risky tool action.
2. Agent queries adjacent content source and selects a specific doc/skill version.
3. Agent writes selection metadata into AICP-governed workflow/transcript state.
4. Policy/approval checks evaluate using that explicit provenance.
5. Action proceeds only if governance checks pass.

## Offline / reduced-freshness operation

If fresh-content source is unavailable:
- switch to cached mode only when policy allows,
- record fallback reason and cache artifact metadata,
- tighten execution scope (read-only or reduced-risk operations),
- require explicit operator approval for sensitive actions,
- schedule revalidation when source connectivity returns.

## Avoiding hidden local-only annotations

- Do not rely on local notes/private annotations as if they were shared truth.
- If local annotations influenced a decision, summarize the relevant decision inputs into transcript-visible structured evidence.
- Keep local enrichment explicitly marked as local/non-authoritative.

## Separation-of-concerns checklist

- Adjacent system answers: “what fresh content exists?”
- AICP answers: “what governed decision was made, by whom, with what evidence?”
- Deployment policy answers: “what freshness/risk threshold is acceptable?”

## Grounding note

This cookbook is intentionally conservative: it documents integration boundaries and provenance patterns without prescribing unverified, repo-internal implementation details of Context Hub.
