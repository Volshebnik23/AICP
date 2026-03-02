from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GEN_PATH = ROOT / "scripts/generate_snapshot_manifest.py"


def _load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_snapshot_manifest_test", GEN_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def test_snapshot_hash_normalizes_eol_for_text_artifacts(tmp_path: Path) -> None:
    generator = _load_generator_module()

    lf_path = tmp_path / "a.json"
    crlf_path = tmp_path / "b.json"

    content_lf = '{\n  "x": 1,\n  "y": [1,2,3]\n}\n'
    content_crlf = content_lf.replace("\n", "\r\n")

    lf_path.write_text(content_lf, encoding="utf-8", newline="\n")
    crlf_path.write_text(content_crlf, encoding="utf-8", newline="")

    assert generator._sha256_file(lf_path) == generator._sha256_file(crlf_path)
