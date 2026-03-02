import py_compile


def test_snapshot_validator_script_compiles() -> None:
    py_compile.compile("scripts/validate_snapshot_manifest.py", doraise=True)
