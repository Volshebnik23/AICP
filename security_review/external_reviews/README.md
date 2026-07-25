# Independent External Security Review Artifact Contract

This directory defines the only repository location from which the repository-truth status
may claim a completed independent external security review. It is a contract for future real
review evidence; no completed review is currently recorded.

Completed review reports belong under:

```text
security_review/external_reviews/completed/
```

The tracked `docs/process/repo_truth_status.json` entry for each completed review must be an
object with:

- `path`: a resolving file below `security_review/external_reviews/completed/`;
- `review_type`: exactly `independent_external`;
- `reviewer`: the reviewer identity or organization supplied by the real reviewer;
- `completion_date`: an ISO `YYYY-MM-DD` date;
- `reviewed_scope`: a non-empty list identifying the reviewed protocol/repository scope;
- `final_status`: `completed` or `completed_with_findings`;
- `findings_remediation_ref`: required for `completed_with_findings`, otherwise optional; when
  present it must resolve to the corresponding findings or remediation record.

The following never establish completion:

- `security_review/SELF_REVIEW.md`;
- this contract, a checklist, coverage map, threat model, or unrelated repository file;
- an artifact outside the `completed/` location;
- a record with placeholder, missing, or incomplete reviewer/scope/date/status metadata;
- a draft or in-progress review;
- a findings-bearing review without a resolving findings/remediation reference.

The machine-readable completion flag must remain `false` and the completed-artifact list must
remain empty until a real reviewer supplies a contract-complete artifact.
