export function verifyPrevHashChain(messages) {
  const errors = [];
  let prev;
  for (let i = 0; i < messages.length; i += 1) {
    const msg = messages[i];
    if (prev !== undefined && msg.prev_msg_hash !== undefined && msg.prev_msg_hash !== prev) {
      errors.push(`line ${i + 1}: prev_msg_hash mismatch (expected ${prev}, got ${msg.prev_msg_hash})`);
    }
    prev = msg.message_hash;
  }
  return errors;
}
