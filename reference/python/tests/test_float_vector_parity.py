from __future__ import annotations

import json
import math
import struct
import pytest
from pathlib import Path

from aicp_ref.jcs import canonicalize_json


def test_float_vectors_match_expected_tokens() -> None:
    vec = json.loads(Path('conformance/vectors/rfc8785_float64_vectors.json').read_text(encoding='utf-8'))
    for row in vec['vectors']:
        bits = int(row['bits'], 16)
        value = struct.unpack('>d', bits.to_bytes(8, 'big'))[0]
        assert canonicalize_json({'n': value}) == f'{{"n":{row["expected"]}}}'
