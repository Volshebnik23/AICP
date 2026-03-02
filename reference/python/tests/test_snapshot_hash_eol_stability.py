from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_manifest_module():
    mod_path = Path(__file__).resolve().parents[3] / "scripts/generate_snapshot_manifest.py"
    spec = spec_from_file_location("generate_snapshot_manifest", mod_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def test_snapshot_hash_eol_stability(tmp_path: Path) -> None:
    mod = _load_manifest_module()
    lf = tmp_path / "sample.json"
    crlf = tmp_path / "sample-crlf.json"
    payload = '{"alpha":1}\n{"beta":2}\n'
    lf.write_bytes(payload.encode("utf-8"))
    crlf.write_bytes(payload.replace("\n", "\r\n").encode("utf-8"))

    assert mod._sha256_file(lf) == mod._sha256_file(crlf)
