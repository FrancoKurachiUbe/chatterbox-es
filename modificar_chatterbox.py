from pathlib import Path

p = Path("multilingual_app.py")
s = p.read_text(encoding="utf-8")

start = s.index("def generate_tts_audio(")
end = s.index("\nwith gr.Blocks()", start)

new = r'''def split_text_for_tts(text: str, max_chars: int = 250) -> list[str]:
    """Split long text into natural chunks suitable for Chatterbox generation."""
    text = text.strip()

    if not text:
        return []

    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
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


def generate_tts_audio(
    text_input: str,
    language_id: str,
    audio_prompt_path_input: str = None,
    exaggeration_input: float = 0.5,
    temperature_input: float = 0.8,
    seed_num_input: int = 0,
    cfgw_input: float = 0.5
) -> tuple[int, np.ndarray]:
    """
    Generate speech from a complete script by automatically splitting it
    into safe chunks and joining the resulting audio.
    """
    current_model = get_or_load_model()

    if current_model is None:
        raise RuntimeError("TTS model is not loaded.")

    if not text_input or not text_input.strip():
        raise ValueError("No text was provided.")

    if seed_num_input != 0:
        set_seed(int(seed_num_input))

    chunks = split_text_for_tts(text_input, max_chars=250)

    print(f"Total text: {len(text_input)} characters")
    print(f"Total chunks: {len(chunks)}")

    chosen_prompt = audio_prompt_path_input or default_audio_for_ui(language_id)

    generate_kwargs = {
        "exaggeration": exaggeration_input,
        "temperature": temperature_input,
        "cfg_weight": cfgw_input,
    }

    if chosen_prompt:
        generate_kwargs["audio_prompt_path"] = chosen_prompt
        print(f"Using audio prompt: {chosen_prompt}")
    else:
        print("No audio prompt provided; using default voice.")

    generated_audio = []
    pause = np.zeros(int(current_model.sr * 0.12), dtype=np.float32)

    for i, chunk in enumerate(chunks, start=1):
        print(f"Generating chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
        print(f"Text: '{chunk[:80]}...'")

        wav = current_model.generate(
            chunk,
            language_id=language_id,
            **generate_kwargs
        )

        audio = wav.squeeze(0).detach().cpu().numpy().astype(np.float32)
        generated_audio.append(audio)

        if i < len(chunks):
            generated_audio.append(pause)

        print(f"Chunk {i}/{len(chunks)} complete.")

    final_audio = np.concatenate(generated_audio)

    print("All chunks generated successfully.")
    print(f"Final audio duration: {len(final_audio) / current_model.sr:.1f} seconds")

    return (current_model.sr, final_audio)
'''

p.write_text(s[:start] + new + s[end:], encoding="utf-8")

print("OK - segmentacion automatica agregada.")
