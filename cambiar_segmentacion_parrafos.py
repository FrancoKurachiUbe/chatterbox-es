from pathlib import Path

p = Path("multilingual_app.py")
s = p.read_text(encoding="utf-8")

start = s.index("def split_text_for_tts(")
end = s.index("\ndef generate_tts_audio(", start)

new = r'''def split_text_for_tts(text: str, max_chars: int = 500) -> list[str]:
    """Split text by paragraphs, with a safety fallback for very long paragraphs."""
    text = text.strip()

    if not text:
        return []

    # Primero separar por párrafos reales
    paragraphs = re.split(r'\n\s*\n+', text)

    chunks = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Si el párrafo entra completo, conservarlo como una sola unidad
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue

        # Párrafo demasiado largo: dividir por oraciones
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)

        current = ""

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            if len(current) + len(sentence) + 1 <= max_chars:
                current = (current + " " + sentence).strip()
                continue

            if current:
                chunks.append(current)
                current = ""

            # Si una oración sola supera el límite, dividir por palabras
            if len(sentence) > max_chars:
                words = sentence.split()
                word_chunk = ""

                for word in words:
                    if len(word_chunk) + len(word) + 1 <= max_chars:
                        word_chunk = (word_chunk + " " + word).strip()
                    else:
                        if word_chunk:
                            chunks.append(word_chunk)
                        word_chunk = word

                if word_chunk:
                    current = word_chunk
            else:
                current = sentence

        if current:
            chunks.append(current)

    return chunks
'''

s = s[:start] + new + s[end:]

p.write_text(s, encoding="utf-8")

print("OK - segmentacion por parrafos agregada.")
