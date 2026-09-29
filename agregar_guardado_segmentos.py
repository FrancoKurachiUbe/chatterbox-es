from pathlib import Path

p = Path("multilingual_app.py")
s = p.read_text(encoding="utf-8")

old = '''        audio = wav.squeeze(0).detach().cpu().numpy().astype(np.float32)
        generated_audio.append(audio)

        if i < len(chunks):
'''

new = '''        audio = wav.squeeze(0).detach().cpu().numpy().astype(np.float32)

        # Guardar cada segmento individual
        segments_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "outputs",
            "segments"
        )
        os.makedirs(segments_dir, exist_ok=True)

        segment_path = os.path.join(
            segments_dir,
            f"segment_{i:03d}.wav"
        )

        torchaudio.save(
            segment_path,
            torch.from_numpy(audio).unsqueeze(0),
            current_model.sr
        )

        print(f"Segment {i}/{len(chunks)} saved: {segment_path}")

        generated_audio.append(audio)

        if i < len(chunks):
'''

assert old in s, "No se encontro el bloque esperado."

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")

print("OK - guardado de segmentos agregado.")
