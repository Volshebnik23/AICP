import test from 'node:test';
import assert from 'node:assert/strict';

import { verifyPrevHashChain } from '../src/chain.js';

function message(messageHash, prevMsgHash) {
  const msg = { message_hash: messageHash };
  if (prevMsgHash !== undefined) {
    msg.prev_msg_hash = prevMsgHash;
  }
  return msg;
}

test('first message may omit prev_msg_hash', () => {
  assert.deepEqual(verifyPrevHashChain([message('sha256:m1')]), []);
});

test('non-first message requires prev_msg_hash', () => {
  const errors = verifyPrevHashChain([
    message('sha256:m1'),
    message('sha256:m2'),
  ]);
  assert.deepEqual(errors, ['line 2: missing prev_msg_hash for non-first message']);
});

test('non-first message rejects empty prev_msg_hash', () => {
  const errors = verifyPrevHashChain([
    message('sha256:m1'),
    message('sha256:m2', ''),
  ]);
  assert.deepEqual(errors, ['line 2: missing prev_msg_hash for non-first message']);
});

test('non-first message rejects wrong prev_msg_hash', () => {
  const errors = verifyPrevHashChain([
    message('sha256:m1'),
    message('sha256:m2', 'sha256:wrong'),
  ]);
  assert.deepEqual(errors, ['line 2: prev_msg_hash mismatch (expected sha256:m1, got sha256:wrong)']);
});

test('valid two-message chain passes', () => {
  assert.deepEqual(verifyPrevHashChain([
    message('sha256:m1'),
    message('sha256:m2', 'sha256:m1'),
  ]), []);
});

test('valid longer chain passes', () => {
  assert.deepEqual(verifyPrevHashChain([
    message('sha256:m1'),
    message('sha256:m2', 'sha256:m1'),
    message('sha256:m3', 'sha256:m2'),
  ]), []);
});
