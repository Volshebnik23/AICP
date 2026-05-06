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
COMPATIBILITY_GATE_BLOCK_RE = re.compile(r"(?ms)^compatibility-gate:\n(.*?)(?=^\S|\Z)")
RELEASE_GATE_BLOCK_RE = re.compile(r"(?ms)^release-gate:\n(.*?)(?=^\S|\Z)")
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
        for required in (
            "$(MAKE) validate",
            "$(MAKE) conformance-all",
            "$(MAKE) test",
            "$(MAKE) quickstart-py",
            "$(MAKE) quickstart-ts",
            "$(MAKE) template-smoke",
            "cd sdk/typescript && npm ci && npm test",
        ):
            if required not in prepr_block:
                errors.append(f"Makefile prepr target must include '{required}'")

    compatibility_match = COMPATIBILITY_GATE_BLOCK_RE.search(makefile)
    if not compatibility_match:
        errors.append("Makefile is missing 'compatibility-gate' target block")
    else:
        compatibility_block = compatibility_match.group(1)
        for required in ("$(MAKE) validate", "$(MAKE) conformance-all", "$(MAKE) snapshot"):
            if required not in compatibility_block:
                errors.append(f"Makefile compatibility-gate target must include '{required}'")

    release_match = RELEASE_GATE_BLOCK_RE.search(makefile)
    if not release_match:
        errors.append("Makefile is missing 'release-gate' target block")
    else:
        release_block = release_match.group(1)
        for required in ("$(MAKE) compatibility-gate", "$(MAKE) test", "$(MAKE) release-check"):
            if required not in release_block:
                errors.append(f"Makefile release-gate target must include '{required}'")

    if "run: make conformance-all" not in ci:
        errors.append("CI workflow must include 'run: make conformance-all'")

    one_command_match = ONE_COMMAND_CHECKS_RE.search(readme)
    if not one_command_match:
        errors.append("README.md is missing '## One-command checks' section")
    else:
        one_command_block = one_command_match.group(1)
        for required in (
            "- `make conformance-all`",
            "- `make prepr`",
            "- `make compatibility-gate`",
            "- `make release-gate`",
        ):
            if required not in one_command_block:
                errors.append(f"README One-command checks must include '{required}'")

    if errors:
        print("[FAIL] verification-gate alignment validation failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print("OK: verification-gate alignment validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
