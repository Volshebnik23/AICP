# ERRATA

Track discovered inconsistencies or bugs across spec text, schemas, fixtures, tests, and tooling.

## How to file an erratum
- Open an issue or PR describing the erratum.
- Include affected spec/doc path(s).
- Include a minimal reproduction (transcript/fixture if possible).
- Link related conformance failures/reports when applicable.

## Template
- **ID:** ER-XXXX
- **Area:** spec | schema | fixture | transcript | conformance | tooling | docs
- **Description:**
- **Impact:** low | medium | high
- **Fix plan:**
- **Status:** open | in_progress | fixed | wont_fix
- **Target milestone:**
- **References:**

## Entries
- **ID:** ER-0001
- **Area:** docs
- **Description:** `docs/core/AICP_Core_v0.1_Normative_0.1.0.docx` may contain legacy branding text (`Agent Interconnector Protocol`) and is not part of the normal Codex PR flow.
- **Impact:** low
- **Fix plan:** Keep Markdown (`docs/core/AICP_Core_v0.1_Normative.md`) as canonical normative source. Regenerate/update DOCX as an optional release artifact outside Codex text-only PR flow.
- **Status:** open
- **Target milestone:** M7.4
- **References:** `docs/core/README.md`, `docs/core/AICP_Core_v0.1_Normative.md`
