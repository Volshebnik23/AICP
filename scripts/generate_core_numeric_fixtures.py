#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'reference/python'))
from aicp_ref.hashing import message_hash_from_body

FIXTURES = [
    ROOT / 'fixtures/core/numeric/NUM-01_float_in_payload.jsonl',
]


def rewrite(path: Path) -> None:
    out = []
    prev = None
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        msg = json.loads(line)
        if prev is None:
            msg.pop('prev_msg_hash', None)
        else:
            msg['prev_msg_hash'] = prev
        body = {k: v for k, v in msg.items() if k != 'message_hash'}
        msg['message_hash'] = message_hash_from_body(body)
        prev = msg['message_hash']
        out.append(json.dumps(msg, separators=(',', ':'), ensure_ascii=False))
    path.write_text('\n'.join(out) + '\n', encoding='utf-8')


def main() -> int:
    for p in FIXTURES:
        rewrite(p)
        print(f'updated {p.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
