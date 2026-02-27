# AICP Protocol Repository

This repository is the canonical source of truth for AICP artifacts under Agent-First SDD.

## Canonical layout

- Core normative document: `docs/core/AICP_Core_v0.1_Normative_0.1.0.docx`
- Core schemas: `schemas/core/`
- Core fixtures and golden transcripts: `fixtures/`
- Conformance suite and runner: `conformance/`
- Python reference implementation: `reference/python/`

## Quickstart

- `make validate`
- `make test`
- `make conformance`

## Notes

Release bundles belong under `dist/` and should not be used as the working source of truth.
