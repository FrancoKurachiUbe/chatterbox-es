export const MAX_CHARS = 250;

/**
 * Splits text into chunks of at most max_chars for TTS synthesis,
 * prioritizing punctuation and sentence boundaries.
 */
export function splitTextForTTS(text: string, maxChars: number = MAX_CHARS): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];

  // Sentence splitting matching Python regex: r".+?(?:[.!?]+(?=\s|$)|$)"
  const regex = /.+?(?:[.!?]+(?=\s|$)|$)/gs;
  const matches = trimmed.match(regex);
  const sentences = matches ? matches.map(s => s.trim()).filter(Boolean) : [trimmed];

  const chunks: string[] = [];
  let currentChunk = "";

  for (const sentence of sentences) {
    if (!sentence) continue;

    // Sentence is longer than maxChars: split by words
    if (sentence.length > maxChars) {
      if (currentChunk) {
        chunks.push(currentChunk.trim());
        currentChunk = "";
      }

      const words = sentence.split(/\s+/);
      let wordChunk = "";

      for (const word of words) {
        const candidate = `${wordChunk} ${word}`.trim();
        if (candidate.length <= maxChars) {
          wordChunk = candidate;
        } else {
          if (wordChunk) {
            chunks.push(wordChunk.trim());
          }
          wordChunk = word;
        }
      }

      if (wordChunk) {
        chunks.push(wordChunk.trim());
      }
      continue;
    }

    // Try adding sentence to currentChunk
    const candidate = `${currentChunk} ${sentence}`.trim();
    if (candidate.length <= maxChars) {
      currentChunk = candidate;
    } else {
      if (currentChunk) {
        chunks.push(currentChunk.trim());
      }
      currentChunk = sentence;
    }
  }

  if (currentChunk) {
    chunks.push(currentChunk.trim());
  }

  return chunks;
}
