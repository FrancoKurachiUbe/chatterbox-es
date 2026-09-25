import random
import os
import re
import json
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

# ---------------------------------------------------------
# PROJECT SAVE / LOAD
# ---------------------------------------------------------

OUTPUTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "outputs"
)

PROJECT_FILE = os.path.join(
    OUTPUTS_DIR,
    "project.json"
)

MAX_CHARS = 250
DEFAULT_SEED = 737219296


def save_project(
    text_input,
    language_id,
    seed,
    exaggeration,
    temperature,
    cfg_weight
):
    """
    Save the current script and settings to project.json.
    """

    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    normalized_text = text_input.replace("\r\n", "\n").strip()

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(
            r"\n\s*\n",
            normalized_text
        )
        if paragraph.strip()
    ]

    project = {
        "last_script": normalized_text,

        "settings": {
            "language": language_id,
            "seed": int(seed),
            "max_chars": MAX_CHARS,
            "exaggeration": float(exaggeration),
            "temperature": float(temperature),
            "cfg_weight": float(cfg_weight)
        },

        "paragraphs": []
    }

    for paragraph_number, paragraph in enumerate(
        paragraphs,
        start=1
    ):

        parts = [
            part.strip()
            for part in split_text_for_tts(
                paragraph,
                max_chars=MAX_CHARS
            )
            if part and part.strip()
        ]

        paragraph_data = {
            "number": paragraph_number,
            "parts": []
        }

        for part_number, part in enumerate(
            parts,
            start=1
        ):

            paragraph_data["parts"].append({
                "number": part_number,
                "text": part
            })

        project["paragraphs"].append(
            paragraph_data
        )

    with open(
        PROJECT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            project,
            f,
            ensure_ascii=False,
            indent=4
        )

    print(f"Project saved to: {PROJECT_FILE}")

    return project


def load_project():
    """
    Load the last saved project.

    Returns None if no project exists yet.
    """

    if not os.path.exists(PROJECT_FILE):
        print("No saved project found.")
        return None

    try:

        with open(
            PROJECT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            project = json.load(f)

        print(
            f"Project loaded from: {PROJECT_FILE}"
        )

        return project

    except Exception as e:

        print(
            f"Could not load project: {e}"
        )

        return None

    
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
    """Split text by paragraphs, not by sentences."""

    text = text.strip()

    if not text:
        return []

    # Cada párrafo separado por una línea en blanco = un audio
    paragraphs = re.split(r"\n\s*\n", text)

    chunks = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # Si el párrafo entra completo, queda como UN solo audio.
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue

        # Si supera el límite, se divide por palabras.
        # Nunca se divide por puntos o frases.
        words = paragraph.split()
        current = ""

        for word in words:
            candidate = (current + " " + word).strip()

            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)

                current = word

        if current:
            chunks.append(current)

    return chunks

def generate_tts_audio(
    text_input: str,
    language_id: str,
    audio_prompt_path_input: str = None,
    exaggeration_input: float = 0.35,
    temperature_input: float = 0.55,
    seed_num_input: int = 737219296,
    cfgw_input: float = 0.5
):
    """
    Generate one audio file per paragraph/part.

    Paragraphs are separated by a blank line.
    Each paragraph is divided into parts of approximately
    250 characters maximum.

    The same fixed seed is used for every part.

    Existing audio files are skipped automatically.
    """

    current_model = get_or_load_model()

    if current_model is None:
        raise RuntimeError("TTS model is not loaded.")

    if not text_input or not text_input.strip():
        raise ValueError("No text was provided.")
    
    save_project(
        text_input=text_input,
        language_id=language_id,
        seed=seed_num_input,
        exaggeration=exaggeration_input,
        temperature=temperature_input,
        cfg_weight=cfgw_input
    )

    # ---------------------------------------------------------
    # PARAGRAPH DETECTION
    # Paragraphs are separated by a blank line
    # ---------------------------------------------------------

    normalized_text = text_input.replace("\r\n", "\n")

    paragraphs = [
        paragraph.strip()
        for paragraph in normalized_text.split("\n\n")
        if paragraph.strip()
    ]

    print(f"Total text: {len(text_input)} characters")
    print(f"Total paragraphs: {len(paragraphs)}")
    print("Maximum characters per part: 250")
    print(f"Fixed seed: {seed_num_input}")

    # ---------------------------------------------------------
    # AUDIO PROMPT
    # ---------------------------------------------------------

    chosen_prompt = (
        audio_prompt_path_input
        or default_audio_for_ui(language_id)
    )

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

    # ---------------------------------------------------------
    # OUTPUT DIRECTORY
    # ---------------------------------------------------------

    segments_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "outputs",
        "segments"
    )

    os.makedirs(segments_dir, exist_ok=True)

    # ---------------------------------------------------------
    # FIXED SEED
    # ---------------------------------------------------------

    fixed_seed = int(seed_num_input)

    print(f"Using fixed seed for all parts: {fixed_seed}")

    # ---------------------------------------------------------
    # PROCESS EACH PARAGRAPH
    # ---------------------------------------------------------

    total_generated = 0
    total_skipped = 0

    for paragraph_number, paragraph in enumerate(
        paragraphs,
        start=1
    ):

        # Split this paragraph into parts of max ~250 chars
        parts = [
            part.strip()
            for part in split_text_for_tts(
                paragraph,
                max_chars=250
            )
            if part and part.strip()
        ]

        print("")
        print("=" * 60)
        print(
            f"PÁRRAFO {paragraph_number}/{len(paragraphs)} "
            f"- {len(parts)} parte(s)"
        )
        print("=" * 60)

        # -----------------------------------------------------
        # PROCESS EACH PART
        # -----------------------------------------------------

        for part_number, chunk in enumerate(
            parts,
            start=1
        ):

            # File name WITHOUT the seed
            filename = (
                f"Parrafo_{paragraph_number:03d}_"
                f"Parte_{part_number:02d}.wav"
            )

            segment_path = os.path.join(
                segments_dir,
                filename
            )

            # -------------------------------------------------
            # SKIP IF ALREADY EXISTS
            # -------------------------------------------------

            if os.path.exists(segment_path):

                print(
                    f"[YA EXISTE] "
                    f"Parrafo {paragraph_number} "
                    f"Parte {part_number}"
                )

                total_skipped += 1

                continue

            # -------------------------------------------------
            # APPLY SAME SEED
            # -------------------------------------------------

            set_seed(fixed_seed)

            print("")
            print(
                f"Generando "
                f"Parrafo {paragraph_number}/{len(paragraphs)} "
                f"Parte {part_number}/{len(parts)}"
            )

            print(f"Characters: {len(chunk)}")
            print(f"Seed: {fixed_seed}")
            print(f"Text: '{chunk[:100]}...'")

            # -------------------------------------------------
            # GENERATE AUDIO
            # -------------------------------------------------

            wav = current_model.generate(
                chunk,
                language_id=language_id,
                **generate_kwargs
            )

            audio = (
                wav.squeeze(0)
                .detach()
                .cpu()
                .numpy()
                .astype(np.float32)
            )

            # -------------------------------------------------
            # SAVE AUDIO
            # -------------------------------------------------

            torchaudio.save(
                segment_path,
                torch.from_numpy(audio).unsqueeze(0),
                current_model.sr
            )

            print(
                f"[GUARDADO] "
                f"{filename}"
            )

            total_generated += 1

    # ---------------------------------------------------------
    # FINISH
    # ---------------------------------------------------------

    print("")
    print("=" * 60)
    print("PROCESO COMPLETADO")
    print("=" * 60)

    print(f"Audios nuevos generados: {total_generated}")
    print(f"Audios ya existentes omitidos: {total_skipped}")
    print(f"Semilla utilizada: {fixed_seed}")
    print(f"Carpeta: {segments_dir}")

    return None


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

            saved_project = load_project()

            initial_text = (
                saved_project.get("last_script")
                if saved_project and saved_project.get("last_script")
                else default_text_for_ui(initial_lang)
            )

        text = gr.Textbox(
            value=initial_text,
            label="Text to synthesize (max chars 300)",
            max_lines=5
        )

        language_id = gr.Dropdown(
            choices=list(
                ChatterboxMultilingualTTS.get_supported_languages().keys()
            ),
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
            " **Note**: Ensure that the reference clip matches the specified language tag. Otherwise, language transfer outputs may inherit the accent of the reference clip's language. To mitigate this, set the CFG weight to 0.",
            elem_classes=["audio-note"]
        )
            
        exaggeration = gr.Slider(
            0.25,
            2,
            step=.05,
            label="Exaggeration (Neutral = 0.5, extreme values can be unstable)",
            value=0.35
        )
        
        cfg_weight = gr.Slider(
            0.2,
            1,
            step=.05,
            label="CFG/Pace",
            value=0.5
        )

        with gr.Accordion("More options", open=False):
            seed_num = gr.Number(
                value=737219296,
                precision=0,
                label="Seed"
                    )
            
            temp = gr.Slider(
                0.05,
                5,
                step=.05,
                label="Temperature",
                value=0.55
            )

        run_btn = gr.Button(
            "Generate",
            variant="primary"
        )

        with gr.Column():
            audio_output = gr.Audio(
                label="Output Audio"
            )

            open_folder_btn = gr.Button(
                "📂 Abrir carpeta de audios"
            )

        def on_voice_change(voice_name):
            return voice_choices.get(voice_name)

        voice_dropdown.change(
            fn=on_voice_change,
            inputs=[voice_dropdown],
            outputs=[ref_wav],
            show_progress=False
        )

        def on_language_change(lang, current_ref, current_text):
            return (
                current_ref or default_audio_for_ui(lang),
                current_text
            )

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

    def open_audio_folder():
        segments_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "outputs",
            "segments"
        )

        os.makedirs(segments_dir, exist_ok=True)

        os.startfile(segments_dir)

        return None

    open_folder_btn.click(
        fn=open_audio_folder,
        inputs=[],
        outputs=[]
    )

demo.launch(mcp_server=True)


