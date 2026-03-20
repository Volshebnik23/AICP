# AICP licensing map

This repository uses a small, explicit licensing split so vendors can determine what they may ship without ambiguity.

## Default license map

- **Code and software-oriented materials** are licensed under the Apache License 2.0 in [`LICENSE`](LICENSE).
  This includes source code, scripts, SDKs, reference implementations, CI helpers, build tooling, and runnable templates unless a file says otherwise.
- **Documentation and reference artifacts** are licensed under Creative Commons Attribution 4.0 International in [`LICENSE-docs`](LICENSE-docs).
  This includes narrative specifications, RFCs, guides, prose documentation, schemas, registries, fixtures, golden transcripts, examples, and other repository reference artifacts unless a file says otherwise.

## How to read the split

AICP's goal for this baseline is simple vendor clarity:

- software you execute or embed as software defaults to **Apache-2.0**;
- prose and reference artifacts you read, quote, package, or adapt as specification/reference material default to **CC BY 4.0**.

If you create a derivative distribution that combines both categories, comply with the license that applies to each included artifact class.

## NOTICE and attribution

- Apache-licensed material is accompanied by [`NOTICE`](NOTICE) for project identification and any repository-level attribution notices.
- CC BY 4.0 material requires preservation of attribution and license notices in the manner required by that license.

## Inbound contributions

Contributions are accepted under the repository license terms that apply to the files being changed. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`DCO`](DCO).

## Maintainer review note

This file is a project-maintainer policy summary for repository discoverability. The governing legal texts are the license files themselves.
