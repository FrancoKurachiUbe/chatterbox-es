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
# PROJECT / PROCESSING SYSTEM
# ---------------------------------------------------------

OUTPUTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "outputs"
)

PROJECT_FILE = os.path.join(
    OUTPUTS_DIR,
    "project.json"
)

SEGMENTS_DIR = os.path.join(
    OUTPUTS_DIR,
    "segments"
)

MAX_CHARS = 250
DEFAULT_SEED = 737219296


# =========================================================
# TEXT SPLITTER
# =========================================================

def split_text_for_tts(
    text: str,
    max_chars: int = MAX_CHARS
) -> list[str]:

    text = text.strip()

    if not text:
        return []

    sentences = re.findall(
        r".+?(?:[.!?]+(?=\s|$)|$)",
        text,
        flags=re.DOTALL
    )

    chunks = []
    current_chunk = ""

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        # -------------------------------------------------
        # ORACIÓN DEMASIADO LARGA
        # -------------------------------------------------

        if len(sentence) > max_chars:

            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            words = sentence.split()
            word_chunk = ""

            for word in words:

                candidate = (
                    f"{word_chunk} {word}"
                ).strip()

                if len(candidate) <= max_chars:
                    word_chunk = candidate

                else:

                    if word_chunk:
                        chunks.append(
                            word_chunk.strip()
                        )

                    word_chunk = word

            if word_chunk:
                chunks.append(
                    word_chunk.strip()
                )

            continue

        # -------------------------------------------------
        # INTENTAR AGREGAR ORACIÓN
        # -------------------------------------------------

        candidate = (
            f"{current_chunk} {sentence}"
        ).strip()

        if len(candidate) <= max_chars:

            current_chunk = candidate

        else:

            if current_chunk:
                chunks.append(
                    current_chunk.strip()
                )

            current_chunk = sentence

    if current_chunk:
        chunks.append(
            current_chunk.strip()
        )

    return chunks


# =========================================================
# NUMBER NORMALIZATION
# =========================================================

UNITS = [
    "cero",
    "uno",
    "dos",
    "tres",
    "cuatro",
    "cinco",
    "seis",
    "siete",
    "ocho",
    "nueve"
]

TEENS = {
    10: "diez",
    11: "once",
    12: "doce",
    13: "trece",
    14: "catorce",
    15: "quince",
    16: "dieciséis",
    17: "diecisiete",
    18: "dieciocho",
    19: "diecinueve"
}

TENS = {
    20: "veinte",
    30: "treinta",
    40: "cuarenta",
    50: "cincuenta",
    60: "sesenta",
    70: "setenta",
    80: "ochenta",
    90: "noventa"
}

HUNDREDS = {
    100: "cien",
    200: "doscientos",
    300: "trescientos",
    400: "cuatrocientos",
    500: "quinientos",
    600: "seiscientos",
    700: "setecientos",
    800: "ochocientos",
    900: "novecientos"
}


def number_to_spanish(n: int) -> str:

    if n < 10:
        return UNITS[n]

    if n in TEENS:
        return TEENS[n]

    if n < 30:

        return (
            "veinti"
            + UNITS[n - 20]
        )

    if n < 100:

        tens = (n // 10) * 10
        units = n % 10

        if units == 0:
            return TENS[tens]

        return (
            f"{TENS[tens]} y "
            f"{UNITS[units]}"
        )

    if n < 1000:

        hundreds = (n // 100) * 100
        remainder = n % 100

        if n == 100:
            return "cien"

        prefix = HUNDREDS[hundreds]

        if remainder == 0:
            return prefix

        return (
            f"{prefix} "
            f"{number_to_spanish(remainder)}"
        )

    if n < 2000:

        remainder = n % 1000

        if remainder == 0:
            return "mil"

        return (
            f"mil "
            f"{number_to_spanish(remainder)}"
        )

    if n < 1000000:

        thousands = n // 1000
        remainder = n % 1000

        result = (
            f"{number_to_spanish(thousands)} "
            f"mil"
        )

        if remainder:
            result += (
                f" {number_to_spanish(remainder)}"
            )

        return result

    # Para números extremadamente grandes,
    # dejamos el número original.
    return str(n)


def normalize_numbers_for_tts(
    text: str,
    language_id: str
) -> str:

    if language_id != "es":
        return text

    def replace_number(match):

        number = match.group(0)

        try:
            value = int(number)

            if value > 999999:
                return number

            return number_to_spanish(value)

        except Exception:
            return number

    return re.sub(
        r"\b\d{1,6}\b",
        replace_number,
        text
    )


# =========================================================
# PARAGRAPH PARSER
# =========================================================

def parse_paragraphs_from_script(
    text_input: str
) -> list[dict]:

    text_input = (
        text_input
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )

    if not text_input:
        raise ValueError(
            "El guion está vacío."
        )

    paragraphs = re.split(
        r"\n\s*\n",
        text_input
    )

    result = []

    number = 1

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        result.append({
            "number": number,
            "title": "",
            "text": paragraph
        })

        number += 1

    if not result:
        raise ValueError(
            "No se encontraron párrafos."
        )

    return result


# =========================================================
# SCENE PARSER
# =========================================================

def parse_scenes_from_script(
    text_input: str
) -> list[dict]:

    text_input = (
        text_input
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )

    if not text_input:
        raise ValueError(
            "El guion está vacío."
        )

    lines = text_input.split("\n")

    scene_pattern = re.compile(
        r"^\s*ESCENA\s+(\d+)"
        r"(?:\s*[—–:-]\s*(.*))?\s*$",
        re.IGNORECASE
    )

    scenes = []

    current_scene = None

    content_before_first_scene = []

    for line in lines:

        match = scene_pattern.match(line)

        if match:

            if current_scene is not None:

                current_scene["text"] = (
                    "\n".join(
                        current_scene["text_lines"]
                    ).strip()
                )

                del current_scene["text_lines"]

                scenes.append(
                    current_scene
                )

            scene_number = int(
                match.group(1)
            )

            scene_title = (
                match.group(2) or ""
            ).strip()

            current_scene = {
                "number": scene_number,
                "title": scene_title,
                "text_lines": []
            }

        else:

            if current_scene is not None:

                current_scene[
                    "text_lines"
                ].append(line)

            elif line.strip():

                content_before_first_scene.append(
                    line.strip()
                )

    if current_scene is not None:

        current_scene["text"] = (
            "\n".join(
                current_scene["text_lines"]
            ).strip()
        )

        del current_scene["text_lines"]

        scenes.append(
            current_scene
        )

    if content_before_first_scene:

        raise ValueError(
            "Hay texto antes de la primera ESCENA. "
            "El guion debe comenzar con "
            "'ESCENA 1 — Título'."
        )

    if not scenes:

        raise ValueError(
            "No se encontraron escenas. "
            "Usá el formato "
            "'ESCENA 1 — Título'."
        )

    for scene in scenes:

        if not scene["text"]:

            raise ValueError(
                f"La ESCENA "
                f"{scene['number']} "
                f"no tiene texto."
            )

    return scenes


# =========================================================
# BUILD PROJECT STRUCTURE
# =========================================================

def build_project_structure(
    text_input: str,
    processing_mode: str,
    language_id: str
):

    if processing_mode == "scene":

        sections = (
            parse_scenes_from_script(
                text_input
            )
        )

    else:

        sections = (
            parse_paragraphs_from_script(
                text_input
            )
        )

    processed_sections = []

    for section in sections:

        normalized_text = (
            normalize_numbers_for_tts(
                section["text"],
                language_id
            )
        )

        parts = split_text_for_tts(
            normalized_text,
            max_chars=MAX_CHARS
        )

        processed_sections.append({

            "number": section["number"],

            "title": section.get(
                "title",
                ""
            ),

            "text": section["text"],

            "normalized_text": normalized_text,

            "parts": [

                {
                    "number": index + 1,
                    "text": part
                }

                for index, part
                in enumerate(parts)

            ]

        })

    return processed_sections


# =========================================================
# SAVE PROJECT
# =========================================================

def save_project(
    text_input,
    processing_mode,
    language_id,
    audio_prompt_path_input,
    exaggeration_input,
    temperature_input,
    seed_num_input,
    cfgw_input
):

    os.makedirs(
        OUTPUTS_DIR,
        exist_ok=True
    )

    sections = build_project_structure(
        text_input,
        processing_mode,
        language_id
    )

    project = {

        "last_script": text_input,

        "processing_mode": (
            processing_mode
        ),

        "settings": {

            "language": language_id,

            "audio_prompt_path":
                audio_prompt_path_input,

            "exaggeration":
                exaggeration_input,

            "temperature":
                temperature_input,

            "seed":
                seed_num_input,

            "cfg_weight":
                cfgw_input

        },

        "sections": sections

    }

    with open(
        PROJECT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            project,
            f,
            ensure_ascii=False,
            indent=2
        )

    return project


# =========================================================
# LOAD PROJECT
# =========================================================

def load_project():

    if not os.path.exists(
        PROJECT_FILE
    ):

        print(
            "No saved project found."
        )

        return None

    try:

        with open(
            PROJECT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            project = json.load(f)

        print(
            f"Project loaded from: "
            f"{PROJECT_FILE}"
        )

        return project

    except Exception as e:

        print(
            f"Could not load project: {e}"
        )

        return None


# =========================================================
# AUDIO PROMPT
# =========================================================

def resolve_audio_prompt(
    language_id: str,
    provided_path: str | None
):

    if (
        provided_path
        and str(provided_path).strip()
    ):

        return provided_path

    return (
        LANGUAGE_CONFIG
        .get(language_id, {})
        .get("audio")
    )


# =========================================================
# FILE NAMING
# =========================================================

def get_section_label(
    processing_mode
):

    if processing_mode == "scene":
        return "Escena"

    return "Parrafo"


def get_section_filename(
    processing_mode,
    section_number,
    part_number
):

    prefix = get_section_label(
        processing_mode
    )

    return (
        f"{prefix}_"
        f"{section_number:03d}_"
        f"Parte_"
        f"{part_number:02d}.wav"
    )


def get_section_path(
    processing_mode,
    section_number,
    part_number
):

    filename = get_section_filename(
        processing_mode,
        section_number,
        part_number
    )

    os.makedirs(
        SEGMENTS_DIR,
        exist_ok=True
    )

    return os.path.join(
        SEGMENTS_DIR,
        filename
    )


# =========================================================
# GENERATE TTS
# =========================================================

def generate_tts_audio(
    text_input: str,
    processing_mode: str,
    language_id: str,
    audio_prompt_path_input: str = None,
    exaggeration_input: float = 0.35,
    temperature_input: float = 0.55,
    seed_num_input: int = DEFAULT_SEED,
    cfgw_input: float = 0.5
):

    current_model = (
        get_or_load_model()
    )

    if current_model is None:

        raise RuntimeError(
            "TTS model is not loaded."
        )

    if (
        not text_input
        or not text_input.strip()
    ):

        raise ValueError(
            "No text was provided."
        )

    project = save_project(

        text_input=text_input,

        processing_mode=
            processing_mode,

        language_id=language_id,

        audio_prompt_path_input=
            audio_prompt_path_input,

        exaggeration_input=
            exaggeration_input,

        temperature_input=
            temperature_input,

        seed_num_input=
            seed_num_input,

        cfgw_input=
            cfgw_input
    )

    sections = project[
        "sections"
    ]

    chosen_prompt = (
        resolve_audio_prompt(
            language_id,
            audio_prompt_path_input
        )
    )

    generate_kwargs = {

        "exaggeration":
            float(exaggeration_input),

        "temperature":
            float(temperature_input),

        "cfg_weight":
            float(cfgw_input)

    }

    if chosen_prompt:

        generate_kwargs[
            "audio_prompt_path"
        ] = chosen_prompt

    fixed_seed = int(
        seed_num_input
    )

    total_generated = 0
    total_skipped = 0

    print("")
    print("=" * 60)
    print(
        f"MODO: "
        f"{'ESCENAS' if processing_mode == 'scene' else 'PÁRRAFOS'}"
    )
    print("=" * 60)

    for section in sections:

        section_number = int(
            section["number"]
        )

        parts = section[
            "parts"
        ]

        title = section.get(
            "title",
            ""
        )

        label = get_section_label(
            processing_mode
        )

        print("")
        print("=" * 60)

        if processing_mode == "scene":

            print(
                f"ESCENA "
                f"{section_number}"
                f" — {title}"
            )

        else:

            print(
                f"PÁRRAFO "
                f"{section_number}"
            )

        print(
            f"Partes: {len(parts)}"
        )

        print("=" * 60)

        for part in parts:

            part_number = int(
                part["number"]
            )

            chunk = part["text"]

            segment_path = (
                get_section_path(
                    processing_mode,
                    section_number,
                    part_number
                )
            )

            filename = os.path.basename(
                segment_path
            )

            if os.path.exists(
                segment_path
            ):

                print(
                    f"[YA EXISTE] "
                    f"{filename}"
                )

                total_skipped += 1

                continue

            set_seed(
                fixed_seed
            )

            print("")
            print(
                f"Generando "
                f"{label} "
                f"{section_number} "
                f"Parte "
                f"{part_number}/"
                f"{len(parts)}"
            )

            print(
                f"Characters: "
                f"{len(chunk)}"
            )

            wav = (
                current_model.generate(
                    chunk,
                    language_id=
                        language_id,
                    **generate_kwargs
                )
            )

            audio = (
                wav.squeeze(0)
                .detach()
                .cpu()
                .numpy()
                .astype(np.float32)
            )

            torchaudio.save(

                segment_path,

                torch.from_numpy(
                    audio
                ).unsqueeze(0),

                current_model.sr

            )

            print(
                f"[GUARDADO] "
                f"{filename}"
            )

            total_generated += 1

    print("")
    print("=" * 60)
    print("PROCESO COMPLETADO")
    print("=" * 60)

    print(
        f"Audios nuevos: "
        f"{total_generated}"
    )

    print(
        f"Audios omitidos: "
        f"{total_skipped}"
    )

    print(
        f"Seed: {fixed_seed}"
    )

    return None


# =========================================================
# REGENERATE ONE PART
# =========================================================

# =========================================================
# REGENERATE ONE PART
# =========================================================

def regenerate_tts_part(
    processing_mode,
    section_number,
    part_number,
    language_id,
    audio_prompt_path_input,
    exaggeration_input,
    temperature_input,
    seed_num_input,
    cfgw_input
):

    current_model = get_or_load_model()

    project = load_project()

    if not project:
        raise ValueError(
            "No hay ningún proyecto guardado."
        )

    section_number = int(section_number)
    part_number = int(part_number)

    selected_text = None

    for section in project.get("sections", []):

        if int(section.get("number", 0)) != section_number:
            continue

        for part in section.get("parts", []):

            if int(part.get("number", 0)) == part_number:

                selected_text = part.get("text")
                break

        break

    if not selected_text:

        raise ValueError(
            "No se encontró el texto seleccionado."
        )

    segment_path = get_section_path(
        processing_mode,
        section_number,
        part_number
    )

    chosen_prompt = resolve_audio_prompt(
        language_id,
        audio_prompt_path_input
    )

    generate_kwargs = {
        "exaggeration": float(exaggeration_input),
        "temperature": float(temperature_input),
        "cfg_weight": float(cfgw_input)
    }

    if chosen_prompt:

        generate_kwargs["audio_prompt_path"] = chosen_prompt

    fixed_seed = int(seed_num_input)

    set_seed(fixed_seed)

    print("")
    print("=" * 60)
    print("REGENERANDO AUDIO")
    print("=" * 60)

    print(
        f"Modo: {processing_mode}"
    )

    print(
        f"Sección: {section_number}"
    )

    print(
        f"Parte: {part_number}"
    )

    wav = current_model.generate(
        selected_text,
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

    torchaudio.save(
        segment_path,
        torch.from_numpy(audio).unsqueeze(0),
        current_model.sr
    )

    print(
        f"[REGENERADO] "
        f"{os.path.basename(segment_path)}"
    )

    return segment_path


# =========================================================
# BATCH REGENERATE
# =========================================================

def batch_regenerate_tts_parts(
    selected_items,
    processing_mode,
    language_id,
    audio_prompt_path_input,
    exaggeration_input,
    temperature_input,
    seed_num_input,
    cfgw_input
):

    if not selected_items:
        raise ValueError(
            "No seleccionaste ninguna parte."
        )

    current_model = get_or_load_model()

    project = load_project()

    if not project:
        raise ValueError(
            "No hay ningún proyecto guardado."
        )

    chosen_prompt = resolve_audio_prompt(
        language_id,
        audio_prompt_path_input
    )

    generate_kwargs = {
        "exaggeration": float(exaggeration_input),
        "temperature": float(temperature_input),
        "cfg_weight": float(cfgw_input)
    }

    if chosen_prompt:
        generate_kwargs["audio_prompt_path"] = chosen_prompt

    fixed_seed = int(seed_num_input)

    generated = 0
    errors = []

    print("")
    print("=" * 60)
    print("REGENERACIÓN MÚLTIPLE")
    print("=" * 60)

    for item in selected_items:

        try:

            section_number = int(item[0])
            part_number = int(item[1])

            selected_text = None

            for section in project.get("sections", []):

                if int(section.get("number", 0)) != section_number:
                    continue

                for part in section.get("parts", []):

                    if int(part.get("number", 0)) == part_number:

                        selected_text = part.get("text")
                        break

                break

            if not selected_text:

                raise ValueError(
                    "No se encontró el texto."
                )

            segment_path = get_section_path(
                processing_mode,
                section_number,
                part_number
            )

            set_seed(fixed_seed)

            print(
                f"Regenerando "
                f"{get_section_label(processing_mode)} "
                f"{section_number} "
                f"Parte {part_number}"
            )

            wav = current_model.generate(
                selected_text,
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

            torchaudio.save(
                segment_path,
                torch.from_numpy(audio).unsqueeze(0),
                current_model.sr
            )

            generated += 1

            print(
                f"[OK] "
                f"{os.path.basename(segment_path)}"
            )

        except Exception as e:

            error_text = (
                f"{item}: {str(e)}"
            )

            errors.append(error_text)

            print(
                f"[ERROR] {error_text}"
            )

            continue

    message = (
        f"Regeneración terminada. "
        f"{generated} parte(s) procesada(s)."
    )

    if errors:

        message += (
            f" {len(errors)} con error."
        )

    return message


# =========================================================
# JOIN SECTION
# =========================================================

def join_section_audio(
    processing_mode,
    section_number
):

    project = load_project()

    if not project:
        raise ValueError(
            "No hay ningún proyecto guardado."
        )

    section_number = int(section_number)

    selected_section = None

    for section in project.get("sections", []):

        if int(section.get("number", 0)) == section_number:

            selected_section = section
            break

    if selected_section is None:

        raise ValueError(
            "No se encontró la sección."
        )

    parts = selected_section.get(
        "parts",
        []
    )

    if not parts:

        raise ValueError(
            "La sección no tiene partes."
        )

    audio_parts = []

    sample_rate = None

    for part in parts:

        part_number = int(
            part.get("number", 0)
        )

        part_path = get_section_path(
            processing_mode,
            section_number,
            part_number
        )

        if not os.path.exists(part_path):

            raise ValueError(
                f"Falta el audio de la "
                f"Parte {part_number}."
            )

        waveform, sr = torchaudio.load(
            part_path
        )

        if sample_rate is None:

            sample_rate = sr

        elif sr != sample_rate:

            raise ValueError(
                "Las partes tienen distintas "
                "frecuencias de muestreo."
            )

        audio_parts.append(
            waveform
        )

    joined_audio = torch.cat(
        audio_parts,
        dim=1
    )

    os.makedirs(
        SEGMENTS_DIR,
        exist_ok=True
    )

    prefix = get_section_label(
        processing_mode
    )

    final_filename = (
        f"{prefix}_"
        f"{section_number:03d}.wav"
    )

    final_path = os.path.join(
        SEGMENTS_DIR,
        final_filename
    )

    torchaudio.save(
        final_path,
        joined_audio,
        sample_rate
    )

    print("")
    print(
        f"[UNIDO] {final_filename}"
    )

    return final_path


# =========================================================
# PROJECT STATUS
# =========================================================

def get_project_status(
    processing_mode
):

    project = load_project()

    if not project:

        return (
            "🟡 **Sin proyecto generado todavía.**"
        )

    sections = project.get(
        "sections",
        []
    )

    label = get_section_label(
        processing_mode
    )

    total_parts = 0
    generated_parts = 0
    missing_parts = 0

    for section in sections:

        for part in section.get(
            "parts",
            []
        ):

            total_parts += 1

            part_number = int(
                part["number"]
            )

            section_number = int(
                section["number"]
            )

            path = get_section_path(
                processing_mode,
                section_number,
                part_number
            )

            if os.path.exists(path):

                generated_parts += 1

            else:

                missing_parts += 1

    return (
        f"🟢 **{label}s:** {len(sections)}  \n"
        f"🎧 **Partes generadas:** {generated_parts} / {total_parts}  \n"
        f"⏳ **Partes faltantes:** {missing_parts}"
    )
/* ===== GLOBAL ===== */

body {
    background: #0b0d10 !important;
}

.gradio-container {
    max-width: 1500px !important;
    background: #0b0d10 !important;
}

/* ===== HEADER ===== */

.cm-header {
    text-align: center;
    padding: 28px 20px 20px 20px;
    margin-bottom: 20px;
    border-bottom: 1px solid #252a31;
}

.cm-title {
    font-size: 34px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #f1f1f1;
    margin-bottom: 5px;
}

.cm-subtitle {
    font-size: 15px;
    color: #8d96a3;
    letter-spacing: 3px;
    text-transform: uppercase;
}

/* ===== SECTION TITLES ===== */

.cm-section-title {
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 1px;
    color: #d8dde5;
    margin-top: 8px;
    margin-bottom: 10px;
}

/* ===== CARDS ===== */

.cm-card {
    background: #12161b;
    border: 1px solid #252a31;
    border-radius: 12px;
    padding: 18px;
}

/* ===== SCRIPT BOX ===== */

.cm-script textarea {
    background: #0f1216 !important;
    border: 1px solid #292f37 !important;
    border-radius: 10px !important;
    color: #e7eaf0 !important;
    font-size: 15px !important;
    line-height: 1.55 !important;
}

/* ===== MAIN BUTTON ===== */

.cm-generate button {
    height: 52px !important;
    border-radius: 9px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
}

/* ===== SECONDARY BUTTONS ===== */

.cm-secondary button {
    border-radius: 8px !important;
}

/* ===== AUDIO PANEL ===== */

.cm-audio-panel {
    background: #0f1216;
    border: 1px solid #252a31;
    border-radius: 12px;
    padding: 16px;
}

/* ===== PARAGRAPH HEADER ===== */

.cm-paragraph {
    background: #151a20;
    border: 1px solid #2a3038;
    border-radius: 10px;
    padding: 12px 15px;
    margin-top: 15px;
}

/* ===== STATUS ===== */

.cm-status {
    background: #101419;
    border: 1px solid #252a31;
    border-radius: 10px;
    padding: 14px;
}

/* ===== SMALL TEXT ===== */

.cm-muted {
    color: #7f8996;
    font-size: 13px;
}

/* ===== ACCORDION ===== */

.cm-settings {
    border: 1px solid #252a31 !important;
    border-radius: 10px !important;
}



with gr.Blocks(
    title="Crónicas Mundiales — Narration Studio",
    css=CUSTOM_CSS
) as demo:

    # =====================================================
    # HEADER
    # =====================================================

    gr.HTML(
        """
        <div class="cm-header">
            <div class="cm-title">CRÓNICAS MUNDIALES</div>
            <div class="cm-subtitle">Narration Studio</div>
        </div>
        """
    )

    # =====================================================
    # PROJECT STATE
    # =====================================================

    saved_project = load_project()
    panel_refresh = gr.State(0)
    initial_lang = "es"

    initial_processing_mode = (
        saved_project.get(
            "processing_mode",
            "paragraph"
        )
        if saved_project
        else "paragraph"
    )

    initial_text = (
        saved_project.get("last_script")
        if saved_project and saved_project.get("last_script")
        else default_text_for_ui(initial_lang)
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

    # =====================================================
    # MAIN LAYOUT
    # =====================================================

    with gr.Row():

        # =================================================
        # LEFT — SCRIPT / SETTINGS
        # =================================================

        with gr.Column(scale=5):

            gr.HTML(
                '<div class="cm-section-title">🎬 MODO DE PROCESAMIENTO</div>'
)

            with gr.Group(elem_classes="cm-card"):

                processing_mode = gr.Radio(
                    choices=[
                        ("📄 Por párrafos", "paragraph"),
                        ("🎬 Por escenas", "scene")
                    ],
                    value=initial_processing_mode,
                    label="Cómo organizar el guion",
                    info=(
                        "Por párrafos usa líneas en blanco. "
                        "Por escenas usa encabezados ESCENA 1 — Título."
                    )
                )

            gr.HTML(
                '<div class="cm-section-title">📝 GUION</div>'
            )

            with gr.Group(elem_classes="cm-card"):

                text = gr.Textbox(
                    value=initial_text,
                    label="Texto de narración",
                    placeholder=(
                        "Pegá aquí el guion. "
                        "Separá cada párrafo con una línea en blanco."
                    ),
                    lines=18,
                    max_lines=30,
                    elem_classes="cm-script"
                )

                gr.Markdown(
                    """
                    <div class="cm-muted">
                        <b>Por párrafos:</b><br>
                        Separá cada párrafo con una línea en blanco.<br><br>

                        <b>Por escenas:</b><br>
                        Usá el formato <b>ESCENA 1 — Título</b>.
                        El título sirve para organizar el proyecto y no se envía a Chatterbox.
                    </div>
                    """
                )

            # =============================================
            # VOICE
            # =============================================

            gr.HTML(
                '<div class="cm-section-title">🎙️ VOZ</div>'
            )

            with gr.Group(elem_classes="cm-card"):

                language_id = gr.Dropdown(
                    choices=list(
                        ChatterboxMultilingualTTS
                        .get_supported_languages()
                        .keys()
                    ),
                    value=initial_lang,
                    label="Idioma",
                    info="Idioma utilizado para la síntesis"
                )

                voice_dropdown = gr.Dropdown(
                    choices=list(voice_choices.keys()),
                    value=initial_voice,
                    label="Voz",
                    info="Voz de referencia"
                )

                ref_wav = gr.Audio(
                    sources=["upload", "microphone"],
                    type="filepath",
                    label="Audio de referencia",
                    value=initial_ref
                )

            # =============================================
            # SETTINGS
            # =============================================

            with gr.Accordion(
                "⚙️ Configuración de narración",
                open=False,
                elem_classes="cm-settings"
            ):

                exaggeration = gr.Slider(
                    0.25,
                    2,
                    step=0.05,
                    label="Exaggeration",
                    value=0.35
                )

                cfg_weight = gr.Slider(
                    0.2,
                    1,
                    step=0.05,
                    label="CFG / Pace",
                    value=0.5
                )

                temp = gr.Slider(
                    0.05,
                    5,
                    step=0.05,
                    label="Temperature",
                    value=0.55
                )

                seed_num = gr.Number(
                    value=737219296,
                    precision=0,
                    label="Seed fija"
                )

            # =============================================
            # GENERATE
            # =============================================

            run_btn = gr.Button(
                "🎙️ GENERAR NARRACIÓN",
                variant="primary",
                elem_classes="cm-generate"
            )


        # =================================================
        # RIGHT — PRODUCTION
        # =================================================

        with gr.Column(scale=6):

            gr.HTML(
                '<div class="cm-section-title">🎧 PRODUCCIÓN</div>'
            )

            # =============================================
            # MAIN OUTPUT
            # =============================================

            with gr.Group(elem_classes="cm-card"):

                audio_output = gr.Audio(
                    label="Último audio generado",
                    type="filepath"
                )

                open_folder_btn = gr.Button(
                    "📂 Abrir carpeta de audios",
                    elem_classes="cm-secondary"
                )

            # =============================================
            # STATUS
            # =============================================

            with gr.Group(elem_classes="cm-status"):

                gr.Markdown(
                    """
                    ### Estado del proyecto

                    🟢 **Listo para generar**

                    <span class="cm-muted">
                    Los audios generados aparecerán aquí.
                    </span>
                    """
                )

            # =============================================
            # AUDIO PANEL
            # =============================================

            gr.HTML(
                '<div class="cm-section-title">'
                '🎚️ PRODUCCIÓN DE AUDIO'
                '</div>'
            )

            with gr.Group(
                elem_classes="cm-audio-panel"
            ):

                gr.Markdown(
                    """
                    ### 🎧 Revisión y producción

                    <span class="cm-muted">
                    Revisá cada parte antes de unir el párrafo
                    o la escena. Podés regenerar partes individuales
                    o seleccionar varias para regenerarlas juntas.
                    </span>
                    """
                )

                with gr.Row():

                    batch_regenerate_btn = gr.Button(
                        "🔄 Regenerar seleccionadas",
                        variant="primary",
                        elem_classes="cm-secondary"
                    )

                    refresh_panel_btn = gr.Button(
                        "↻ Actualizar panel",
                        elem_classes="cm-secondary"
                    )

                panel_status = gr.Markdown(
                    get_project_status(
                        initial_processing_mode
                    )
                )

    def on_voice_change(voice_name):
        return voice_choices.get(voice_name)


    voice_dropdown.change(
        fn=on_voice_change,
        inputs=[voice_dropdown],
        outputs=[ref_wav],
        show_progress=False
    )


    def on_language_change(
        lang,
        current_ref,
        current_text
    ):

        return (
            current_ref or default_audio_for_ui(lang),
            current_text
        )


    language_id.change(
        fn=on_language_change,
        inputs=[
            language_id,
            ref_wav,
            text
        ],
        outputs=[
            ref_wav,
            text
        ],
        show_progress=False
    )


    # =====================================================
    # GENERATE EVENT
    # =====================================================

    run_btn.click(
        fn=generate_tts_audio,
        inputs=[
            text,
            processing_mode,
            language_id,
            ref_wav,
            exaggeration,
            temp,
            seed_num,
            cfg_weight,
        ],
        outputs=[audio_output]
    )


    # =====================================================
    # OPEN AUDIO FOLDER
    # =====================================================

    def open_audio_folder():

        segments_dir = os.path.join(
            os.path.dirname(
                os.path.abspath(__file__)
            ),
            "outputs",
            "segments"
        )

        os.makedirs(
            segments_dir,
            exist_ok=True
        )

        os.startfile(segments_dir)

        return None


    open_folder_btn.click(
        fn=open_audio_folder,
        inputs=[],
        outputs=[]
    )


# =========================================================
# LAUNCH
# =========================================================

demo.launch()