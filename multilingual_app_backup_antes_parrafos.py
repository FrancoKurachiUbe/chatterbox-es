import random
import os
import re
import numpy as np
import torch
import torchaudio
from chatterbox.mtl_tts import ChatterboxMultilingualTTS, SUPPORTED_LANGUAGES
import gradio as gr

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
T3_MODEL = os.getenv("CHATTERBOX_MULTILINGUAL_T3_MODEL", "v2")
print(f"🚀 Running on device: {DEVICE}")
print(f"Using multilingual T3 model: {T3_MODEL}")

# --- Global Model Initialization ---
MODEL = None

# --- Voice Library ---
VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")

def get_voice_files():
    os.makedirs(VOICES_DIR, exist_ok=True)
    return sorted(
        [
            os.path.join(VOICES_DIR, f)
            for f in os.listdir(VOICES_DIR)
            if f.lower().endswith(".wav")
        ]
    )

def get_voice_choices():
    files = get_voice_files()
    return {os.path.splitext(os.path.basename(f))[0]: f for f in files}



LANGUAGE_CONFIG = {
    "ar": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ar_f/ar_prompts2.flac",
        "text": "في الشهر الماضي، وصلنا إلى معلم جديد بمليارين من المشاهدات على قناتنا على يوتيوب."
    },
    "da": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/da_m1.flac",
        "text": "Sidste måned nåede vi en ny milepæl med to milliarder visninger på vores YouTube-kanal."
    },
    "de": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/de_f1.flac",
        "text": "Letzten Monat haben wir einen neuen Meilenstein erreicht: zwei Milliarden Aufrufe auf unserem YouTube-Kanal."
    },
    "el": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/el_m.flac",
        "text": "Τον περασμένο μήνα, φτάσαμε σε ένα νέο ορόσημο με δύο δισεκατομμύρια προβολές στο κανάλι μας στο YouTube."
    },
    "en": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/en_f1.flac",
        "text": "Last month, we reached a new milestone with two billion views on our YouTube channel."
    },
    "es": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/es_f1.flac",
        "text": "El mes pasado alcanzamos un nuevo hito: dos mil millones de visualizaciones en nuestro canal de YouTube."
    },
    "fi": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/fi_m.flac",
        "text": "Viime kuussa saavutimme uuden virstanpylvään kahden miljardin katselukerran kanssa YouTube-kanavallamme."
    },
    "fr": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/fr_f1.flac",
        "text": "Le mois dernier, nous avons atteint un nouveau jalon avec deux milliards de vues sur notre chaîne YouTube."
    },
    "he": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/he_m1.flac",
        "text": "בחודש שעבר הגענו לאבן דרך חדשה עם שני מיליארד צפיות בערוץ היוטיוב שלנו."
    },
    "hi": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/hi_f1.flac",
        "text": "पिछले महीने हमने एक नया मील का पत्थर छुआ: हमारे YouTube चैनल पर दो अरब व्यूज़।"
    },
    "it": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/it_m1.flac",
        "text": "Il mese scorso abbiamo raggiunto un nuovo traguardo: due miliardi di visualizzazioni sul nostro canale YouTube."
    },
    "ja": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ja/ja_prompts1.flac",
        "text": "先月、私たちのYouTubeチャンネルで二十億回の再生回数という新たなマイルストーンに到達しました。"
    },
    "ko": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ko_f.flac",
        "text": "지난달 우리는 유튜브 채널에서 이십억 조회수라는 새로운 이정표에 도달했습니다."
    },
    "ms": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ms_f.flac",
        "text": "Bulan lepas, kami mencapai pencapaian baru dengan dua bilion tontonan di saluran YouTube kami."
    },
    "nl": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/nl_m.flac",
        "text": "Vorige maand bereikten we een nieuwe mijlpaal met twee miljard weergaven op ons YouTube-kanaal."
    },
    "no": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/no_f1.flac",
        "text": "Forrige måned nådde vi en ny milepæl med to milliarder visninger på YouTube-kanalen vår."
    },
    "pl": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/pl_m.flac",
        "text": "W zeszłym miesiącu osiągnęliśmy nowy kamień milowy z dwoma miliardami wyświetleń na naszym kanale YouTube."
    },
    "pt": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/pt_m1.flac",
        "text": "No mês passado, alcançámos um novo marco: dois mil milhões de visualizações no nosso canal do YouTube."
    },
    "ru": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ru_m.flac",
        "text": "В прошлом месяце мы достигли нового рубежа: два миллиарда просмотров на нашем YouTube-канале."
    },
    "sv": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/sv_f.flac",
        "text": "Förra månaden nådde vi en ny milstolpe med två miljarder visningar på vår YouTube-kanal."
    },
    "sw": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/sw_m.flac",
        "text": "Mwezi uliopita, tulifika hatua mpya ya maoni ya bilioni mbili kweny kituo chetu cha YouTube."
    },
    "tr": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/tr_m.flac",
        "text": "Geçen ay YouTube kanalımızda iki milyar görüntüleme ile yeni bir dönüm noktasına ulaştık."
    },
    "zh": {
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/zh_f2.flac",
        "text": "上个月，我们达到了一个新的里程碑. 我们的YouTube频道观看次数达到了二十亿次，这绝对令人难以置信。"
    },
}

# --- UI Helpers ---
def default_audio_for_ui(lang: str) -> str | None:
    return LANGUAGE_CONFIG.get(lang, {}).get("audio")


def default_text_for_ui(lang: str) -> str:
    return LANGUAGE_CONFIG.get(lang, {}).get("text", "")


def get_supported_languages_display() -> str:
    """Generate a formatted display of all supported languages."""
    language_items = []
    for code, name in sorted(SUPPORTED_LANGUAGES.items()):
        language_items.append(f"**{name}** (`{code}`)")
    
    # Split into 2 lines
    mid = len(language_items) // 2
    line1 = " • ".join(language_items[:mid])
    line2 = " • ".join(language_items[mid:])
    
    return f"""
### 🌍 Supported Languages ({len(SUPPORTED_LANGUAGES)} total)
{line1}

{line2}
"""


def get_or_load_model():
    """Loads the ChatterboxMultilingualTTS model if it hasn't been loaded already,
    and ensures it's on the correct device."""
    global MODEL
    if MODEL is None:
        print("Model not loaded, initializing...")
        try:
            MODEL = ChatterboxMultilingualTTS.from_pretrained(DEVICE, t3_model=T3_MODEL)
            if hasattr(MODEL, 'to') and str(MODEL.device) != DEVICE:
                MODEL.to(DEVICE)
            print(f"Model loaded successfully. Internal device: {getattr(MODEL, 'device', 'N/A')}")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    return MODEL

# Attempt to load the model at startup.
try:
    get_or_load_model()
except Exception as e:
    print(f"CRITICAL: Failed to load model on startup. Application may not function. Error: {e}")

def set_seed(seed: int):
    """Sets the random seed for reproducibility across torch, numpy, and random."""
    torch.manual_seed(seed)
    if DEVICE == "cuda":
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    np.random.seed(seed)
    
def resolve_audio_prompt(language_id: str, provided_path: str | None) -> str | None:
    """
    Decide which audio prompt to use:
    - If user provided a path (upload/mic/url), use it.
    - Else, fall back to language-specific default (if any).
    """
    if provided_path and str(provided_path).strip():
        return provided_path
    return LANGUAGE_CONFIG.get(language_id, {}).get("audio")


def split_text_for_tts(text: str, max_chars: int = 250) -> list[str]:
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
            generated_audio.append(pause)

        print(f"Chunk {i}/{len(chunks)} complete.")

    final_audio = np.concatenate(generated_audio)

    print("All chunks generated successfully.")
    print(f"Final audio duration: {len(final_audio) / current_model.sr:.1f} seconds")

    return (current_model.sr, final_audio)

with gr.Blocks() as demo:
    gr.Markdown(
        """
        # Chatterbox Multilingual Demo
        Generate high-quality multilingual speech from text with reference audio styling, supporting 23 languages.
        """
    )
    
    # Display supported languages
    gr.Markdown(get_supported_languages_display())
    with gr.Row():
        with gr.Column():
            initial_lang = "es"
            text = gr.Textbox(
                value=default_text_for_ui(initial_lang),
                label="Text to synthesize (max chars 300)",
                max_lines=5
            )
            
            language_id = gr.Dropdown(
                choices=list(ChatterboxMultilingualTTS.get_supported_languages().keys()),
                value=initial_lang,
                label="Language",
                info="Select the language for text-to-speech synthesis"
            )
            
            voice_choices = get_voice_choices()
            preferred_voice = "Brian Warm Clonacion Voz"
            initial_voice = (
                preferred_voice
                if preferred_voice in voice_choices
                else next(iter(voice_choices), None)
            )
            initial_ref = (
                voice_choices.get(initial_voice)
                if initial_voice
                else default_audio_for_ui(initial_lang)
            )

            voice_dropdown = gr.Dropdown(
                choices=list(voice_choices.keys()),
                value=initial_voice,
                label="Voice",
                info="Select a voice from the voices folder"
            )

            ref_wav = gr.Audio(
                sources=["upload", "microphone"],
                type="filepath",
                label="Reference Audio File (Optional)",
                value=initial_ref
            )
            
            gr.Markdown(
                "💡 **Note**: Ensure that the reference clip matches the specified language tag. Otherwise, language transfer outputs may inherit the accent of the reference clip's language. To mitigate this, set the CFG weight to 0.",
                elem_classes=["audio-note"]
            )
            
            exaggeration = gr.Slider(
                0.25, 2, step=.05, label="Exaggeration (Neutral = 0.5, extreme values can be unstable)", value=.5
            )
            cfg_weight = gr.Slider(
                0.2, 1, step=.05, label="CFG/Pace", value=0.5
            )

            with gr.Accordion("More options", open=False):
                seed_num = gr.Number(value=0, label="Random seed (0 for random)")
                temp = gr.Slider(0.05, 5, step=.05, label="Temperature", value=.8)

            run_btn = gr.Button("Generate", variant="primary")

        with gr.Column():
            audio_output = gr.Audio(label="Output Audio")

        def on_voice_change(voice_name):
            return voice_choices.get(voice_name)

        voice_dropdown.change(
            fn=on_voice_change,
            inputs=[voice_dropdown],
            outputs=[ref_wav],
            show_progress=False
        )

        def on_language_change(lang, current_ref, current_text):
            return current_ref or default_audio_for_ui(lang), default_text_for_ui(lang)

        language_id.change(
            fn=on_language_change,
            inputs=[language_id, ref_wav, text],
            outputs=[ref_wav, text],
            show_progress=False
        )

    run_btn.click(
        fn=generate_tts_audio,
        inputs=[
            text,
            language_id,
            ref_wav,
            exaggeration,
            temp,
            seed_num,
            cfg_weight,
        ],
        outputs=[audio_output],
    )

demo.launch(mcp_server=True)

