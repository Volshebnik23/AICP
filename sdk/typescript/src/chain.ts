export interface HashChainMessage {
  message_hash?: string;
  prev_msg_hash?: string;
}

export function verifyPrevHashChain(messages: HashChainMessage[]): string[] {
  const errors: string[] = [];
  let prev: string | undefined;
  for (let i = 0; i < messages.length; i += 1) {
    const msg = messages[i];
    const currentPrev = msg.prev_msg_hash;
    if (prev !== undefined) {
      if (currentPrev === undefined || currentPrev === null || currentPrev === "") {
        errors.push(`line ${i + 1}: missing prev_msg_hash for non-first message`);
      } else if (currentPrev !== prev) {
        errors.push(`line ${i + 1}: prev_msg_hash mismatch (expected ${prev}, got ${currentPrev})`);
      }
    }
    prev = msg.message_hash;
  }
  return errors;
}
