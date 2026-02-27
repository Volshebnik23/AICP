17. Reference implementations and conformance harness
Reference implementations and a conformance harness are part of the standard toolkit. They make the protocol executable and reduce integration cost. Reference code is not production-grade security software; production systems MUST undergo security review.
17.1 Required artifacts (normative intent)
•	Reference library implementing Core algorithms: JCS, object_hash, Ed25519 verify/sign, message hash chain.
•	Minimal contract replica implementing CT-01..CT-08 state machine behavior.
•	Fixtures: TV-01..TV-03 synchronized with this spec.
•	Conformance runner suitable for CI (pytest or equivalent).
17.2 Recommended run (Python example)
Example commands:
cd reference/python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
