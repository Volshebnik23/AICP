#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
README = ROOT / "README.md"

PREPR_BLOCK_RE = re.compile(r"(?ms)^prepr:\n(.*?)(?=^\S|\Z)")
ONE_COMMAND_CHECKS_RE = re.compile(r"(?ms)^## One-command checks\n\n(.*?)(?=^## |\Z)")


def _load(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> int:
    errors: list[str] = []

    makefile = _load(MAKEFILE)
    ci = _load(CI_WORKFLOW)
    readme = _load(README)

    match = PREPR_BLOCK_RE.search(makefile)
    if not match:
        errors.append("Makefile is missing 'prepr' target block")
    else:
        prepr_block = match.group(1)
        if "$(MAKE) conformance-profiles" not in prepr_block:
            errors.append("Makefile prepr target must include '$(MAKE) conformance-profiles'")
        if "$(MAKE) template-smoke" not in prepr_block:
            errors.append("Makefile prepr target must include '$(MAKE) template-smoke'")

    if "run: make conformance-profiles" not in ci:
        errors.append("CI workflow must include 'run: make conformance-profiles'")

    one_command_match = ONE_COMMAND_CHECKS_RE.search(readme)
    if not one_command_match:
        errors.append("README.md is missing '## One-command checks' section")
    else:
        one_command_block = one_command_match.group(1)
        if "- `make conformance-profiles`" not in one_command_block:
            errors.append("README One-command checks must include 'make conformance-profiles'")
        if "- `make template-smoke`" not in one_command_block:
            errors.append("README One-command checks must include 'make template-smoke'")

    if errors:
        print("[FAIL] verification-gate alignment validation failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print("OK: verification-gate alignment validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
