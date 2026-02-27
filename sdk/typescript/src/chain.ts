export interface HashChainMessage {
  message_hash?: string;
  prev_msg_hash?: string;
}

export function verifyPrevHashChain(messages: HashChainMessage[]): string[] {
  const errors: string[] = [];
  let prev: string | undefined;
  for (let i = 0; i < messages.length; i += 1) {
    const msg = messages[i];
    if (prev !== undefined && msg.prev_msg_hash !== undefined && msg.prev_msg_hash !== prev) {
      errors.push(`line ${i + 1}: prev_msg_hash mismatch (expected ${prev}, got ${msg.prev_msg_hash})`);
    }
    prev = msg.message_hash;
  }
  return errors;
}
