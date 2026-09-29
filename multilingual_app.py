#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
CRÓNICAS MUNDIALES — NARRATION STUDIO
Backend Python & API Local para Frontend Moderno y Gradio Fallback
Basado en Chatterbox Multilingual TTS con PyTorch y procesamiento local.
=============================================================================
"""

import os
import sys
import re
import json
import random
import traceback
import subprocess
import threading
import time
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

try:
    import numpy as np
    import torch
    import torchaudio
except ImportError as e:
    print("\n" + "=" * 65)
    print(f"❌ [ERROR CRÍTICO] Falta una librería esencial de audio: {e}")
    print(f"👉 Intérprete actual de Python: {sys.executable}")
    print("👉 Asegúrate de ejecutar este script con el entorno virtual que contiene PyTorch.")
    print("   Ejemplo: D:\\chatterbox-master\\.venv\\Scripts\\python.exe multilingual_app.py")
    print("=" * 65 + "\n")
    try:
        input("Presiona Enter para continuar...")
    except Exception:
        pass
    sys.exit(1)

# Intento de importar Chatterbox Multilingual TTS
try:
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS, SUPPORTED_LANGUAGES
except ImportError:
    ChatterboxMultilingualTTS = None
    SUPPORTED_LANGUAGES = {
        "ar": "Arabic", "da": "Danish", "de": "German", "el": "Greek",
        "en": "English", "es": "Spanish", "fi": "Finnish", "fr": "French",
        "he": "Hebrew", "hi": "Hindi", "it": "Italian", "ja": "Japanese",
        "ko": "Korean", "ms": "Malay", "nl": "Dutch", "no": "Norwegian",
        "pl": "Polish", "pt": "Portuguese", "ru": "Russian", "sv": "Swedish",
        "sw": "Swahili", "tr": "Turkish", "zh": "Chinese"
    }

# =============================================================================
# 1. CONFIGURACIÓN DEL SISTEMA Y HARDWARE
# =============================================================================

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEVICE_LABEL = f"🚀 CUDA ({torch.cuda.get_device_name(0)})" if torch.cuda.is_available() else "💻 CPU (AMD/Intel)"
T3_MODEL = os.getenv("CHATTERBOX_MULTILINGUAL_T3_MODEL", "v2")

# Rutas del proyecto usando pathlib
BASE_DIR = Path(__file__).resolve().parent
VOICES_DIR = BASE_DIR / "voices"
OUTPUTS_DIR = BASE_DIR / "outputs"
SEGMENTS_DIR = OUTPUTS_DIR / "segments"
PROJECT_FILE = OUTPUTS_DIR / "project.json"

# Asegurar existencia de directorios básicos
VOICES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Parámetros predeterminados para producción
DEFAULT_SEED = 737219296
DEFAULT_EXAGGERATION = 0.35
DEFAULT_TEMPERATURE = 0.55
DEFAULT_CFG_WEIGHT = 0.5
MAX_CHARS = 250
PREFERRED_VOICE = "Brian Warm Clonacion Voz"

# =============================================================================
# 2. GESTIÓN DE MODELO (CARGA LAZY / SINGLETON)
# =============================================================================

MODEL: Optional[Any] = None
MODEL_STATUS = f"⚪ Modelo no cargado ({DEVICE.upper()})"
GENERATION_LOCK = threading.Lock()

# Estado global de la cola de generación para el Frontend moderno
GENERATION_STATE: Dict[str, Any] = {
    "is_generating": False,
    "current_step": 0,
    "total_steps": 0,
    "current_label": "",
    "message": "Inactivo",
    "errors": [],
    "last_generated": None,
}


def get_model_status_text() -> str:
    """Devuelve el estado actual de la carga del modelo en memoria."""
    global MODEL
    if MODEL is not None:
        return f"🟢 Modelo cargado en memoria ({DEVICE.upper()})"
    return f"⚪ Modelo no cargado ({DEVICE.upper()})"


def get_or_load_model(progress_callback: Optional[Any] = None) -> Any:
    """
    Carga el modelo ChatterboxMultilingualTTS de forma lazy si aún no está en memoria.
    Reutiliza la instancia existente para evitar duplicar memoria RAM/VRAM.
    """
    global MODEL, MODEL_STATUS
    if MODEL is None:
        if ChatterboxMultilingualTTS is None:
            raise RuntimeError(
                "La librería 'chatterbox' no está instalada en el entorno de Python. "
                "Instálala con: pip install chatterbox-tts"
            )
        print(f"📦 [Chatterbox] Inicializando modelo en dispositivo: {DEVICE} (T3: {T3_MODEL})...")
        if progress_callback:
            try:
                progress_callback(0.05, desc="Cargando modelo Chatterbox en memoria...")
            except Exception:
                pass
        try:
            MODEL = ChatterboxMultilingualTTS.from_pretrained(DEVICE, t3_model=T3_MODEL)
            if hasattr(MODEL, "to") and str(getattr(MODEL, "device", "")) != DEVICE:
                MODEL.to(DEVICE)
            MODEL_STATUS = f"🟢 Modelo cargado en {DEVICE.upper()}"
            print(f"✅ [Chatterbox] Modelo cargado exitosamente. Dispositivo: {getattr(MODEL, 'device', DEVICE)}")
        except Exception as e:
            MODEL_STATUS = f"🔴 Error al cargar modelo: {str(e)}"
            print(f"❌ [Chatterbox] Error crítico al cargar modelo: {e}")
            traceback.print_exc()
            raise RuntimeError(f"No se pudo cargar el modelo Chatterbox: {e}")
    return MODEL


def set_seed(seed: int) -> None:
    """Establece la semilla para garantizar reproducibilidad exacta."""
    torch.manual_seed(seed)
    if DEVICE == "cuda":
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    np.random.seed(seed)


# =============================================================================
# 3. BIBLIOTECA DE VOCES Y MUESTRAS MULTILINGÜES
# =============================================================================

def get_voice_files() -> List[Path]:
    """Obtiene la lista ordenada de archivos WAV en la carpeta voices."""
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(list(VOICES_DIR.glob("*.wav")))


def get_voice_choices() -> Dict[str, str]:
    """Devuelve un diccionario {nombre_voz: ruta_absoluta_wav}."""
    files = get_voice_files()
    choices = {f.stem: str(f.resolve()) for f in files}
    if PREFERRED_VOICE not in choices:
        choices[PREFERRED_VOICE] = str((VOICES_DIR / f"{PREFERRED_VOICE}.wav").resolve())
    return choices


LANGUAGE_CONFIG: Dict[str, Dict[str, str]] = {
    "ar": {
        "name": "Árabe",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ar_f/ar_prompts2.flac",
        "text": "في الشهر الماضي، وصلنا إلى معلم جديد بمليارين من المشاهدات على قناتنا على يوتيوب."
    },
    "da": {
        "name": "Danés",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/da_m1.flac",
        "text": "Sidste måned nåede vi en ny milepæl med to milliarder visninger på vores YouTube-kanal."
    },
    "de": {
        "name": "Alemán",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/de_f1.flac",
        "text": "Letzten Monat haben wir einen neuen Meilenstein erreicht: zwei Milliarden Aufrufe auf unserem YouTube-Kanal."
    },
    "el": {
        "name": "Griego",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/el_m.flac",
        "text": "Τον περασμένο μήνα, φτάσαμε σε ένα νέο ορόσημο με δύο δισεκατομμύρια προβολές στο κανάλι μας στο YouTube."
    },
    "en": {
        "name": "Inglés",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/en_f1.flac",
        "text": "Last month, we reached a new milestone with two billion views on our YouTube channel."
    },
    "es": {
        "name": "Español",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/es_f1.flac",
        "text": "El mes pasado alcanzamos un nuevo hito: dos mil millones de visualizaciones en nuestro canal de YouTube."
    },
    "fi": {
        "name": "Finlandés",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/fi_m.flac",
        "text": "Viime kuussa saavutimme uuden virstanpylvään kahden miljardin katselukerran kanssa YouTube-kanavallamme."
    },
    "fr": {
        "name": "Francés",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/fr_f1.flac",
        "text": "Le mois dernier, nous avons atteint un nouveau jalon avec deux milliards de vues sur notre chaîne YouTube."
    },
    "he": {
        "name": "Hebreo",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/he_m1.flac",
        "text": "בחודש שעבר הגענו לאבן דרך חדשה עם שני מיליארד צפיות בערוץ היוטיוב שלנו."
    },
    "hi": {
        "name": "Hindi",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/hi_f1.flac",
        "text": "पिछले महीने हमने एक नया मील का पत्थर छुआ: हमारे YouTube चैनल पर दो अरब व्यूज़।"
    },
    "it": {
        "name": "Italiano",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/it_m1.flac",
        "text": "Il mese scorso abbiamo raggiunto un nuevo traguardo: due miliardi di visualizzazioni sul nostro canale YouTube."
    },
    "ja": {
        "name": "Japonés",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ja/ja_prompts1.flac",
        "text": "先月、私たちのYouTubeチャンネルで二十億回の再生回数という新たなマイルストーンに到達しました。"
    },
    "ko": {
        "name": "Coreano",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ko_f.flac",
        "text": "지난달 우리는 유튜브 채널에서 이십억 조회수라는 새로운 이정표에 도달했습니다."
    },
    "ms": {
        "name": "Malayo",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ms_f.flac",
        "text": "Bulan lepas, kami mencapai pencapaian baru dengan dua bilion tontonan di saluran YouTube kami."
    },
    "nl": {
        "name": "Holandés",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/nl_m.flac",
        "text": "Vorige maand bereikten we een nieuwe mijlpaal met twee miljard weergaven op ons YouTube-kanaal."
    },
    "no": {
        "name": "Noruego",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/no_f1.flac",
        "text": "Forrige måned nådde vi en ny milepæl med to milliarder visninger på YouTube-kanalen vår."
    },
    "pl": {
        "name": "Polaco",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/pl_m.flac",
        "text": "W zeszłym miesiącu osiągnęliśmy nowy kamień milowy z dwoma miliardami wyświetleń na naszym kanale YouTube."
    },
    "pt": {
        "name": "Portugués",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/pt_m1.flac",
        "text": "No mês passado, alcançámos um novo marco: dois mil milhões de visualizações no nosso canal do YouTube."
    },
    "ru": {
        "name": "Ruso",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ru_m.flac",
        "text": "В прошлом месяце мы достигли нового рубежа: два миллиарда просмотров на нашем YouTube-канале."
    },
    "sv": {
        "name": "Sueco",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/sv_f.flac",
        "text": "Förra månaden nådde vi en ny milstolpe med två miljarder visningar på vår YouTube-kanal."
    },
    "sw": {
        "name": "Suajili",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/sw_m.flac",
        "text": "Mwezi uliopita, tulifika hatua mpya ya maoni ya bilioni mbili kweny kituo chetu cha YouTube."
    },
    "tr": {
        "name": "Turco",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/tr_m.flac",
        "text": "Geçen ay YouTube kanalımızda iki milyar görüntüleme ile yeni bir dönüm noktasına ulaştık."
    },
    "zh": {
        "name": "Chino",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/zh_f2.flac",
        "text": "上个月，我们达到了一个新的里程碑。我们的YouTube频道观看次数达到了二十亿次，这绝对令人难以置信。"
    },
}

def get_language_dropdown_choices() -> List[Tuple[str, str]]:
    choices = []
    for code, conf in sorted(LANGUAGE_CONFIG.items()):
        name = conf.get("name", code)
        choices.append((f"{name} ({code})", code))
    return choices


def default_audio_for_ui(lang: str) -> Optional[str]:
    return LANGUAGE_CONFIG.get(lang, {}).get("audio")


def default_text_for_ui(lang: str) -> str:
    return LANGUAGE_CONFIG.get(lang, {}).get("text", "")


def resolve_audio_prompt(language_id: str, provided_path: Optional[str]) -> Optional[str]:
    if provided_path and str(provided_path).strip():
        path_obj = Path(provided_path)
        if path_obj.exists():
            return str(path_obj.resolve())
        return str(provided_path).strip()
    return LANGUAGE_CONFIG.get(language_id, {}).get("audio")


# =============================================================================
# 4. NORMALIZACIÓN FONÉTICA DE NÚMEROS EN ESPAÑOL
# =============================================================================

UNITS = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
TEENS = {
    10: "diez", 11: "once", 12: "doce", 13: "trece", 14: "catorce",
    15: "quince", 16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve"
}
TENS = {
    20: "veinte", 30: "treinta", 40: "cuarenta", 50: "cincuenta",
    60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"
}
HUNDREDS = {
    100: "cien", 200: "doscientos", 300: "trescientos", 400: "cuatrocientos",
    500: "quinientos", 600: "seiscientos", 700: "setecientos", 800: "ochocientos",
    900: "novecientos"
}


def number_to_spanish(n: int) -> str:
    if n < 0:
        return f"menos {number_to_spanish(abs(n))}"
    if n < 10:
        return UNITS[n]
    if n in TEENS:
        return TEENS[n]
    if n < 30:
        return f"veinti{UNITS[n - 20]}"
    if n < 100:
        tens = (n // 10) * 10
        units = n % 10
        if units == 0:
            return TENS[tens]
        return f"{TENS[tens]} y {UNITS[units]}"
    if n < 1000:
        hundreds = (n // 100) * 100
        remainder = n % 100
        prefix = "ciento" if (hundreds == 100 and remainder > 0) else HUNDREDS[hundreds]
        if remainder == 0:
            return prefix
        return f"{prefix} {number_to_spanish(remainder)}"
    if n < 2000:
        remainder = n % 1000
        if remainder == 0:
            return "mil"
        return f"mil {number_to_spanish(remainder)}"
    if n < 1000000:
        thousands = n // 1000
        remainder = n % 1000
        result = f"{number_to_spanish(thousands)} mil"
        if remainder:
            result += f" {number_to_spanish(remainder)}"
        return result
    return str(n)


def normalize_numbers_for_tts(text: str, language_id: str) -> str:
    if language_id != "es":
        return text

    def replace_number(match: re.Match) -> str:
        number_str = match.group(0)
        try:
            val = int(number_str)
            if val > 999999:
                return number_str
            return number_to_spanish(val)
        except Exception:
            return number_str

    return re.sub(r"\b\d{1,6}\b", replace_number, text)


# =============================================================================
# 5. SEGMENTACIÓN INTELIGENTE DE GUION (LÍMITE ~250 CARACTERES)
# =============================================================================

def split_text_for_tts(text: str, max_chars: int = MAX_CHARS) -> List[str]:
    text = text.strip()
    if not text:
        return []

    sentences = re.findall(r".+?(?:[.!?]+(?=\s|$)|$)", text, flags=re.DOTALL)
    chunks: List[str] = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            words = sentence.split()
            word_chunk = ""

            for word in words:
                candidate = f"{word_chunk} {word}".strip()
                if len(candidate) <= max_chars:
                    word_chunk = candidate
                else:
                    if word_chunk:
                        chunks.append(word_chunk.strip())
                    word_chunk = word

            if word_chunk:
                chunks.append(word_chunk.strip())
            continue

        candidate = f"{current_chunk} {sentence}".strip()
        if len(candidate) <= max_chars:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


# =============================================================================
# 6. PARSERS DE PÁRRAFOS Y ESCENAS
# =============================================================================

def parse_paragraphs_from_script(text_input: str) -> List[Dict[str, Any]]:
    text_input = text_input.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text_input:
        raise ValueError("El guion está vacío. Por favor introduce texto para continuar.")

    paragraphs = re.split(r"\n\s*\n", text_input)
    result = []
    number = 1

    for paragraph in paragraphs:
        p_text = paragraph.strip()
        if not p_text:
            continue
        result.append({
            "number": number,
            "title": "",
            "text": p_text
        })
        number += 1

    if not result:
        raise ValueError("No se encontraron párrafos válidos en el texto.")
    return result


def parse_scenes_from_script(text_input: str) -> List[Dict[str, Any]]:
    text_input = text_input.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text_input:
        raise ValueError("El guion está vacío. Por favor introduce texto para continuar.")

    lines = text_input.split("\n")
    scene_pattern = re.compile(r"^\s*ESCENA\s+(\d+)(?:\s*[—–:-]\s*(.*))?\s*$", re.IGNORECASE)

    scenes: List[Dict[str, Any]] = []
    current_scene: Optional[Dict[str, Any]] = None
    content_before_first_scene: List[str] = []

    for line in lines:
        match = scene_pattern.match(line)
        if match:
            if current_scene is not None:
                current_scene["text"] = "\n".join(current_scene["text_lines"]).strip()
                del current_scene["text_lines"]
                scenes.append(current_scene)

            scene_number = int(match.group(1))
            scene_title = (match.group(2) or "").strip()
            current_scene = {
                "number": scene_number,
                "title": scene_title,
                "text_lines": []
            }
        else:
            if current_scene is not None:
                current_scene["text_lines"].append(line)
            elif line.strip():
                content_before_first_scene.append(line.strip())

    if current_scene is not None:
        current_scene["text"] = "\n".join(current_scene["text_lines"]).strip()
        del current_scene["text_lines"]
        scenes.append(current_scene)

    if content_before_first_scene:
        raise ValueError(
            "Hay texto antes de la primera escena. El guion debe comenzar con 'ESCENA 1 — Título'."
        )

    if not scenes:
        raise ValueError("No se encontraron escenas. Usa el formato 'ESCENA 1 — Título'.")

    for s in scenes:
        if not s["text"]:
            raise ValueError(f"La ESCENA {s['number']} no contiene texto de narración.")

    return scenes


def build_project_structure(text_input: str, processing_mode: str, language_id: str) -> List[Dict[str, Any]]:
    if processing_mode == "scene":
        sections = parse_scenes_from_script(text_input)
    else:
        sections = parse_paragraphs_from_script(text_input)

    processed_sections = []
    for s in sections:
        norm_text = normalize_numbers_for_tts(s["text"], language_id)
        parts = split_text_for_tts(norm_text, max_chars=MAX_CHARS)

        processed_sections.append({
            "number": s["number"],
            "title": s.get("title", ""),
            "text": s["text"],
            "normalized_text": norm_text,
            "parts": [
                {"number": idx + 1, "text": part}
                for idx, part in enumerate(parts)
            ]
        })
    return processed_sections


# =============================================================================
# 7. PERSISTENCIA DEL PROYECTO (JSON)
# =============================================================================

def save_project(
    text_input: str,
    processing_mode: str,
    language_id: str,
    audio_prompt_path_input: Optional[str] = None,
    exaggeration_input: float = DEFAULT_EXAGGERATION,
    temperature_input: float = DEFAULT_TEMPERATURE,
    seed_num_input: int = DEFAULT_SEED,
    cfgw_input: float = DEFAULT_CFG_WEIGHT
) -> Dict[str, Any]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    sections = build_project_structure(text_input, processing_mode, language_id)

    project = {
        "last_script": text_input,
        "processing_mode": processing_mode,
        "settings": {
            "language": language_id,
            "audio_prompt_path": audio_prompt_path_input,
            "exaggeration": float(exaggeration_input),
            "temperature": float(temperature_input),
            "seed": int(seed_num_input),
            "cfg_weight": float(cfgw_input)
        },
        "sections": sections,
        "updated_at": int(time.time())
    }

    try:
        with open(PROJECT_FILE, "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=False, indent=2)
        print(f"💾 [Proyecto] Guardado en: {PROJECT_FILE}")
    except Exception as e:
        print(f"⚠️ [Proyecto] Error al guardar JSON: {e}")

    return project


def load_project() -> Optional[Dict[str, Any]]:
    if not PROJECT_FILE.exists():
        return None
    try:
        with open(PROJECT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ [Proyecto] Error al leer {PROJECT_FILE}: {e}")
        return None


# =============================================================================
# 8. RUTAS Y NOMBRES DE ARCHIVOS
# =============================================================================

def get_section_label(processing_mode: str) -> str:
    return "Escena" if processing_mode == "scene" else "Parrafo"


def get_section_filename(processing_mode: str, section_number: int, part_number: int) -> str:
    prefix = get_section_label(processing_mode)
    return f"{prefix}_{section_number:03d}_Parte_{part_number:02d}.wav"


def get_section_path(processing_mode: str, section_number: int, part_number: int) -> Path:
    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = get_section_filename(processing_mode, section_number, part_number)
    return SEGMENTS_DIR / filename


def get_final_joined_path(processing_mode: str, section_number: int) -> Path:
    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    prefix = get_section_label(processing_mode)
    return SEGMENTS_DIR / f"{prefix}_{section_number:03d}.wav"


# =============================================================================
# 9. GENERACIÓN Y SÍNTESIS DE AUDIO (SECUENCIAL Y THREAD-SAFE)
# =============================================================================

def generate_tts_audio(
    text_input: str,
    processing_mode: str,
    language_id: str,
    audio_prompt_path_input: Optional[str] = None,
    exaggeration_input: float = DEFAULT_EXAGGERATION,
    temperature_input: float = DEFAULT_TEMPERATURE,
    seed_num_input: int = DEFAULT_SEED,
    cfgw_input: float = DEFAULT_CFG_WEIGHT,
    progress: Optional[Any] = None
) -> Optional[str]:
    global GENERATION_STATE

    if not text_input or not text_input.strip():
        raise ValueError("El guion está vacío. Introduce texto antes de generar.")

    with GENERATION_LOCK:
        GENERATION_STATE["is_generating"] = True
        GENERATION_STATE["errors"] = []
        GENERATION_STATE["message"] = "Preparando proyecto..."

        try:
            project = save_project(
                text_input=text_input,
                processing_mode=processing_mode,
                language_id=language_id,
                audio_prompt_path_input=audio_prompt_path_input,
                exaggeration_input=exaggeration_input,
                temperature_input=temperature_input,
                seed_num_input=seed_num_input,
                cfgw_input=cfgw_input
            )

            current_model = get_or_load_model(progress_callback=progress)
            sections = project.get("sections", [])
            chosen_prompt = resolve_audio_prompt(language_id, audio_prompt_path_input)

            generate_kwargs: Dict[str, Any] = {
                "exaggeration": float(exaggeration_input),
                "temperature": float(temperature_input),
                "cfg_weight": float(cfgw_input)
            }
            if chosen_prompt:
                generate_kwargs["audio_prompt_path"] = chosen_prompt

            fixed_seed = int(seed_num_input)

            all_parts_to_process = []
            for s in sections:
                for p in s.get("parts", []):
                    p_path = get_section_path(processing_mode, int(s["number"]), int(p["number"]))
                    all_parts_to_process.append((s, p, p_path))

            total_count = len(all_parts_to_process)
            GENERATION_STATE["total_steps"] = total_count
            total_generated = 0
            total_skipped = 0
            last_generated_path: Optional[str] = None

            print("\n" + "=" * 60)
            print(f"🎬 INICIANDO GENERACIÓN: {'ESCENAS' if processing_mode == 'scene' else 'PÁRRAFOS'}")
            print(f"Total partes: {total_count} | Seed: {fixed_seed} | Dispositivo: {DEVICE}")
            print("=" * 60)

            for idx, (sec, part, segment_path) in enumerate(all_parts_to_process):
                sec_num = int(sec["number"])
                part_num = int(part["number"])
                chunk = part["text"]
                label = get_section_label(processing_mode)
                filename = segment_path.name

                GENERATION_STATE["current_step"] = idx + 1
                GENERATION_STATE["current_label"] = f"{label} {sec_num} Parte {part_num}"
                step_desc = f"Generando {label} {sec_num} Parte {part_num}/{len(sec['parts'])} ({idx+1}/{total_count})..."
                GENERATION_STATE["message"] = step_desc

                if progress:
                    try:
                        progress((idx + 1) / max(1, total_count), desc=step_desc)
                    except Exception:
                        pass

                # Comprobar si ya existe
                if segment_path.exists() and segment_path.stat().st_size > 44:
                    print(f"⏩ [YA EXISTE] {filename}")
                    total_skipped += 1
                    last_generated_path = str(segment_path.resolve())
                    GENERATION_STATE["last_generated"] = filename
                    continue

                set_seed(fixed_seed)
                print(f"🎙️ Generando {label} {sec_num} Parte {part_num} ({len(chunk)} caracteres)...")

                try:
                    wav = current_model.generate(
                        chunk,
                        language_id=language_id,
                        **generate_kwargs
                    )
                    audio = wav.squeeze(0).detach().cpu().numpy().astype(np.float32)
                    torchaudio.save(
                        str(segment_path.resolve()),
                        torch.from_numpy(audio).unsqueeze(0),
                        current_model.sr
                    )
                    print(f"✅ [GUARDADO] {filename}")
                    total_generated += 1
                    last_generated_path = str(segment_path.resolve())
                    GENERATION_STATE["last_generated"] = filename
                except Exception as part_err:
                    err_msg = f"Error en {label} {sec_num} Parte {part_num}: {part_err}"
                    print(f"❌ {err_msg}")
                    GENERATION_STATE["errors"].append(err_msg)

            GENERATION_STATE["message"] = f"Completado. {total_generated} generados, {total_skipped} omitidos."
            return last_generated_path
        finally:
            GENERATION_STATE["is_generating"] = False


def regenerate_tts_part(
    processing_mode: str,
    section_number: int,
    part_number: int,
    language_id: str,
    audio_prompt_path_input: Optional[str] = None,
    exaggeration_input: float = DEFAULT_EXAGGERATION,
    temperature_input: float = DEFAULT_TEMPERATURE,
    seed_num_input: int = DEFAULT_SEED,
    cfgw_input: float = DEFAULT_CFG_WEIGHT,
    progress: Optional[Any] = None
) -> str:
    global GENERATION_STATE

    with GENERATION_LOCK:
        GENERATION_STATE["is_generating"] = True
        label = get_section_label(processing_mode)
        GENERATION_STATE["current_label"] = f"{label} {section_number} Parte {part_number}"
        GENERATION_STATE["message"] = f"Regenerando {label} {section_number} Parte {part_number}..."

        try:
            current_model = get_or_load_model(progress_callback=progress)
            project = load_project()
            if not project:
                raise ValueError("No hay ningún proyecto guardado.")

            sec_num = int(section_number)
            p_num = int(part_number)
            selected_text: Optional[str] = None

            for section in project.get("sections", []):
                if int(section.get("number", 0)) == sec_num:
                    for part in section.get("parts", []):
                        if int(part.get("number", 0)) == p_num:
                            selected_text = part.get("text")
                            break
                    break

            if not selected_text:
                raise ValueError(f"No se encontró el texto de {label} {sec_num} Parte {p_num}.")

            segment_path = get_section_path(processing_mode, sec_num, p_num)
            chosen_prompt = resolve_audio_prompt(language_id, audio_prompt_path_input)

            generate_kwargs: Dict[str, Any] = {
                "exaggeration": float(exaggeration_input),
                "temperature": float(temperature_input),
                "cfg_weight": float(cfgw_input)
            }
            if chosen_prompt:
                generate_kwargs["audio_prompt_path"] = chosen_prompt

            set_seed(int(seed_num_input))

            wav = current_model.generate(
                selected_text,
                language_id=language_id,
                **generate_kwargs
            )
            audio = wav.squeeze(0).detach().cpu().numpy().astype(np.float32)
            torchaudio.save(
                str(segment_path.resolve()),
                torch.from_numpy(audio).unsqueeze(0),
                current_model.sr
            )

            print(f"🔄 [REGENERADO] {segment_path.name}")
            GENERATION_STATE["last_generated"] = segment_path.name
            GENERATION_STATE["message"] = f"{segment_path.name} regenerado correctamente."
            return str(segment_path.resolve())
        finally:
            GENERATION_STATE["is_generating"] = False


def batch_regenerate_tts_parts(
    selected_items: List[Tuple[int, int]],
    processing_mode: str,
    language_id: str,
    audio_prompt_path_input: Optional[str],
    exaggeration_input: float,
    temperature_input: float,
    seed_num_input: int,
    cfgw_input: float,
    progress: Optional[Any] = None
) -> str:
    global GENERATION_STATE

    if not selected_items:
        raise ValueError("No seleccionaste ninguna parte.")

    with GENERATION_LOCK:
        GENERATION_STATE["is_generating"] = True
        GENERATION_STATE["errors"] = []
        GENERATION_STATE["total_steps"] = len(selected_items)

        try:
            current_model = get_or_load_model(progress_callback=progress)
            project = load_project()
            if not project:
                raise ValueError("No hay ningún proyecto guardado.")

            chosen_prompt = resolve_audio_prompt(language_id, audio_prompt_path_input)
            generate_kwargs: Dict[str, Any] = {
                "exaggeration": float(exaggeration_input),
                "temperature": float(temperature_input),
                "cfg_weight": float(cfgw_input)
            }
            if chosen_prompt:
                generate_kwargs["audio_prompt_path"] = chosen_prompt

            fixed_seed = int(seed_num_input)
            total_selected = len(selected_items)
            generated = 0
            errors: List[str] = []

            for idx, (sec_num, part_num) in enumerate(selected_items):
                GENERATION_STATE["current_step"] = idx + 1
                GENERATION_STATE["current_label"] = f"Sección {sec_num} Parte {part_num}"
                desc = f"Regenerando seleccionadas: {idx+1}/{total_selected}..."
                GENERATION_STATE["message"] = desc

                if progress:
                    try:
                        progress((idx + 1) / total_selected, desc=desc)
                    except Exception:
                        pass

                try:
                    selected_text: Optional[str] = None
                    for section in project.get("sections", []):
                        if int(section.get("number", 0)) == sec_num:
                            for part in section.get("parts", []):
                                if int(part.get("number", 0)) == part_num:
                                    selected_text = part.get("text")
                                    break
                            break

                    if not selected_text:
                        raise ValueError(f"Texto no encontrado para {sec_num}-{part_num}")

                    segment_path = get_section_path(processing_mode, sec_num, part_num)
                    set_seed(fixed_seed)

                    wav = current_model.generate(
                        selected_text,
                        language_id=language_id,
                        **generate_kwargs
                    )
                    audio = wav.squeeze(0).detach().cpu().numpy().astype(np.float32)
                    torchaudio.save(
                        str(segment_path.resolve()),
                        torch.from_numpy(audio).unsqueeze(0),
                        current_model.sr
                    )
                    generated += 1
                    GENERATION_STATE["last_generated"] = segment_path.name
                    print(f"✅ [REGENERADO OK] {segment_path.name}")
                except Exception as e:
                    err_msg = f"{sec_num}-{part_num}: {str(e)}"
                    errors.append(err_msg)
                    GENERATION_STATE["errors"].append(err_msg)
                    print(f"❌ [ERROR REGENERANDO] {err_msg}")
                    continue

            msg = f"Regeneración terminada: {generated} parte(s) procesada(s)."
            if errors:
                msg += f" Hubo {len(errors)} error(es)."
            GENERATION_STATE["message"] = msg
            return msg
        finally:
            GENERATION_STATE["is_generating"] = False


def join_section_audio(processing_mode: str, section_number: int) -> str:
    project = load_project()
    if not project:
        raise ValueError("No hay ningún proyecto guardado.")

    sec_num = int(section_number)
    selected_section: Optional[Dict[str, Any]] = None

    for section in project.get("sections", []):
        if int(section.get("number", 0)) == sec_num:
            selected_section = section
            break

    if selected_section is None:
        raise ValueError(f"No se encontró {get_section_label(processing_mode)} {sec_num}.")

    parts = selected_section.get("parts", [])
    if not parts:
        raise ValueError("La sección no contiene partes.")

    missing_parts = []
    audio_paths = []
    for part in parts:
        p_num = int(part.get("number", 0))
        part_path = get_section_path(processing_mode, sec_num, p_num)
        if not part_path.exists() or part_path.stat().st_size <= 44:
            missing_parts.append(str(p_num))
        else:
            audio_paths.append(part_path)

    if missing_parts:
        parts_str = ", ".join(missing_parts)
        raise ValueError(f"Faltan las partes: {parts_str}. Debes generarlas antes de unir.")

    audio_parts: List[torch.Tensor] = []
    target_sr: Optional[int] = None

    for p_path in audio_paths:
        waveform, sr = torchaudio.load(str(p_path.resolve()))
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        if target_sr is None:
            target_sr = sr
        elif sr != target_sr:
            resampler = torchaudio.transforms.Resample(sr, target_sr)
            waveform = resampler(waveform)
        audio_parts.append(waveform)

    joined_audio = torch.cat(audio_parts, dim=1)
    final_path = get_final_joined_path(processing_mode, sec_num)
    torchaudio.save(str(final_path.resolve()), joined_audio, target_sr)
    print(f"🔗 [AUDIO UNIDO CON ÉXITO] {final_path.name}")
    return str(final_path.resolve())


def join_all_audio(processing_mode: str = "scene") -> str:
    """Concatena todos los segmentos generados del proyecto en un solo archivo WAV maestro."""
    project = load_project()
    if not project:
        raise ValueError("No hay ningún proyecto guardado.")

    sections = project.get("sections", [])
    if not sections:
        raise ValueError("El proyecto no contiene escenas ni secciones.")

    audio_paths = []
    missing_parts = []

    for section in sections:
        s_num = int(section.get("number", 0))
        parts = section.get("parts", [])
        for part in parts:
            p_num = int(part.get("number", 0))
            part_path = get_section_path(processing_mode, s_num, p_num)
            if not part_path.exists() or part_path.stat().st_size <= 44:
                missing_parts.append(f"Escena {s_num} Parte {p_num}")
            else:
                audio_paths.append(part_path)

    if not audio_paths:
        raise ValueError("No se encontraron archivos de audio generados para unir.")

    audio_parts: List[torch.Tensor] = []
    target_sr: Optional[int] = None

    for p_path in audio_paths:
        waveform, sr = torchaudio.load(str(p_path.resolve()))
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        if target_sr is None:
            target_sr = sr
        elif sr != target_sr:
            resampler = torchaudio.transforms.Resample(sr, target_sr)
            waveform = resampler(waveform)
        audio_parts.append(waveform)

    joined_audio = torch.cat(audio_parts, dim=1)
    final_dir = OUTPUTS_DIR / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    final_path = final_dir / "master_cronicas_mundiales.wav"
    torchaudio.save(str(final_path.resolve()), joined_audio, target_sr)
    print(f"🔗 [AUDIO MASTER COMPLETO CREADO CON ÉXITO] {final_path.name}")
    return str(final_path.resolve())


# =============================================================================
# 10. ESTADO Y VISTAS DE PROYECTO
# =============================================================================

def get_project_status(processing_mode: str) -> str:
    project = load_project()
    if not project:
        return "🟡 **Sin proyecto generado todavía.**"

    sections = project.get("sections", [])
    if not sections:
        return "🟡 **Proyecto vacío.**"

    label = get_section_label(processing_mode)
    total_parts = 0
    generated_parts = 0
    missing_parts = 0

    for section in sections:
        for part in section.get("parts", []):
            total_parts += 1
            p_num = int(part["number"])
            s_num = int(section["number"])
            p_path = get_section_path(processing_mode, s_num, p_num)
            if p_path.exists() and p_path.stat().st_size > 44:
                generated_parts += 1
            else:
                missing_parts += 1

    status_icon = "🟢" if missing_parts == 0 else "🟡"
    return (
        f"{status_icon} **{label}s:** {len(sections)}  |  "
        f"🎧 **Partes generadas:** {generated_parts} / {total_parts}  |  "
        f"⏳ **Partes faltantes:** {missing_parts}"
    )


def get_panel_data(processing_mode: str) -> List[Dict[str, Any]]:
    project = load_project()
    if not project:
        return []

    result = []
    for section in project.get("sections", []):
        sec_num = int(section.get("number", 0))
        title = section.get("title", "")
        parts_data = []

        for part in section.get("parts", []):
            part_num = int(part.get("number", 0))
            part_path = get_section_path(processing_mode, sec_num, part_num)
            exists = part_path.exists() and part_path.stat().st_size > 44
            filename = part_path.name

            parts_data.append({
                "number": part_num,
                "text": part.get("text", ""),
                "filename": filename,
                "path": str(part_path.resolve()) if exists else None,
                "audio_url": f"/api/audio/{filename}" if exists else None,
                "exists": exists
            })

        final_path = get_final_joined_path(processing_mode, sec_num)
        final_exists = final_path.exists() and final_path.stat().st_size > 44
        final_filename = final_path.name

        result.append({
            "number": sec_num,
            "title": title,
            "parts": parts_data,
            "final_path": str(final_path.resolve()) if final_exists else None,
            "final_filename": final_filename if final_exists else None,
            "final_audio_url": f"/api/audio/{final_filename}" if final_exists else None,
            "exists": final_exists
        })

    return result


def get_selection_choices(processing_mode: str) -> List[Tuple[str, str]]:
    data = get_panel_data(processing_mode)
    choices: List[Tuple[str, str]] = []

    for section in data:
        sec_num = section["number"]
        title = section.get("title", "")

        for part in section["parts"]:
            part_num = part["number"]
            value = f"{processing_mode}|{sec_num}|{part_num}"

            if processing_mode == "scene":
                display = f"Escena {sec_num}"
                if title:
                    display += f" — {title}"
                display += f" · Parte {part_num:02d}"
            else:
                display = f"Párrafo {sec_num:03d} · Parte {part_num:02d}"

            if not part["exists"]:
                display += "  ⏳ (Pendiente)"
            else:
                display += "  ✅"

            choices.append((display, value))

    return choices


def parse_selected_items(selected_items: Any) -> List[Tuple[int, int]]:
    parsed = []
    if not selected_items:
        return parsed

    for item in selected_items:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            try:
                parsed.append((int(item[0]), int(item[1])))
                continue
            except (ValueError, TypeError):
                pass

        if isinstance(item, str):
            parts = item.split("|")
            if len(parts) == 3:
                try:
                    parsed.append((int(parts[1]), int(parts[2])))
                    continue
                except ValueError:
                    pass
            elif len(parts) == 2:
                try:
                    parsed.append((int(parts[0]), int(parts[1])))
                    continue
                except ValueError:
                    pass
    return parsed


# =============================================================================
# 11. GRADIO BLOCKS (FALLBACK Y HERRAMIENTA DE PRUEBA)
# =============================================================================

CUSTOM_CSS = """
body, .gradio-container { background-color: #090c10 !important; color: #f0f4f8 !important; }
.cm-header { background: #131922; border-bottom: 1px solid #222936; padding: 20px; border-radius: 12px; text-align: center; }
.cm-title { font-size: 28px; font-weight: 800; color: #ffffff; }
.cm-card { background-color: #11151c !important; border: 1px solid #222936 !important; border-radius: 10px !important; }
"""

def create_studio_app() -> Any:
    """Crea la interfaz de Gradio como herramienta de prueba y fallback."""
    try:
        import gradio as gr
    except ImportError:
        print("⚠️ Gradio no disponible en este entorno.")
        return None

    saved_project = load_project()
    initial_mode = saved_project.get("processing_mode", "scene") if saved_project else "scene"
    initial_text = saved_project.get("last_script") if saved_project and saved_project.get("last_script") else (
        "ESCENA 1 — El Gran Despertar\n"
        "En el corazón de la antigua Europa, el año 1492 marcó el inicio de una era que transformaría el destino de 500 naciones.\n\n"
        "ESCENA 2 — La Tempestad en Altamar\n"
        "Durante 40 días y 40 noches, los vientos del Atlántico pusieron a prueba el temple de más de 90 tripulantes."
    )
    initial_settings = saved_project.get("settings", {}) if saved_project else {}
    initial_lang = initial_settings.get("language", "es")
    initial_exaggeration = initial_settings.get("exaggeration", DEFAULT_EXAGGERATION)
    initial_temp = initial_settings.get("temperature", DEFAULT_TEMPERATURE)
    initial_seed = initial_settings.get("seed", DEFAULT_SEED)
    initial_cfg = initial_settings.get("cfg_weight", DEFAULT_CFG_WEIGHT)

    voice_choices = get_voice_choices()
    initial_voice_name = PREFERRED_VOICE if PREFERRED_VOICE in voice_choices else next(iter(voice_choices), None)
    initial_voice_path = voice_choices.get(initial_voice_name) if initial_voice_name else default_audio_for_ui(initial_lang)

    with gr.Blocks(title="Crónicas Mundiales — Gradio Fallback", css=CUSTOM_CSS) as demo:
        panel_refresh = gr.State(0)

        gr.HTML(
            f"""
            <div class="cm-header">
                <div class="cm-title">CRÓNICAS MUNDIALES — GRADIO FALLBACK</div>
                <div style="color: #06b6d4; font-size: 13px; margin-top: 4px;">Modo de prueba local &bull; {DEVICE_LABEL}</div>
            </div>
            """
        )

        with gr.Row():
            with gr.Column(scale=5):
                processing_mode = gr.Radio(
                    choices=[("🎬 Por escenas", "scene"), ("📄 Por párrafos", "paragraph")],
                    value=initial_mode, label="Modo de procesamiento"
                )
                text_input = gr.Textbox(value=initial_text, label="Guion", lines=12)
                language_id = gr.Dropdown(choices=get_language_dropdown_choices(), value=initial_lang, label="Idioma")
                voice_dropdown = gr.Dropdown(choices=list(voice_choices.keys()), value=initial_voice_name, label="Voz")
                ref_wav = gr.Audio(sources=["upload", "microphone"], type="filepath", label="Referencia", value=initial_voice_path)

                with gr.Accordion("⚙️ Parámetros", open=False):
                    exaggeration = gr.Slider(0.25, 2.0, step=0.05, label="Exaggeration", value=initial_exaggeration)
                    cfg_weight = gr.Slider(0.2, 1.0, step=0.05, label="CFG Weight", value=initial_cfg)
                    temp = gr.Slider(0.05, 5.0, step=0.05, label="Temperature", value=initial_temp)
                    seed_num = gr.Number(value=initial_seed, precision=0, label="Seed")

            with gr.Column(scale=6):
                run_btn = gr.Button("🎙️ GENERAR NARRACIÓN", variant="primary")
                latest_audio = gr.Audio(label="Último audio", type="filepath")
                status_markdown = gr.Markdown(get_project_status(initial_mode))

                selected_parts = gr.CheckboxGroup(choices=get_selection_choices(initial_mode), value=[], label="Partes")
                with gr.Row():
                    select_all_btn = gr.Button("☑️ Todas")
                    clear_selection_btn = gr.Button("⬜ Limpiar")
                    batch_regen_btn = gr.Button("🔄 Regenerar seleccionadas")

                @gr.render(inputs=[processing_mode, panel_refresh])
                def render_panel(mode: str, _rf: int):
                    data = get_panel_data(mode)
                    if not data:
                        gr.Markdown("🟡 Sin audios.")
                        return
                    for sec in data:
                        gr.Markdown(f"### Sección {sec['number']}")
                        for part in sec["parts"]:
                            with gr.Row():
                                gr.Markdown(f"Parte {part['number']}: {part['text']}")
                                gr.Audio(value=part["path"], type="filepath", interactive=False)

        # Callbacks
        run_btn.click(
            fn=lambda t, m, l, r, ex, tp, sd, cf, rf: (
                generate_tts_audio(t, m, l, r, ex, tp, sd, cf),
                get_project_status(m),
                gr.update(choices=get_selection_choices(m), value=[]),
                int(rf) + 1
            ),
            inputs=[text_input, processing_mode, language_id, ref_wav, exaggeration, temp, seed_num, cfg_weight, panel_refresh],
            outputs=[latest_audio, status_markdown, selected_parts, panel_refresh]
        )

        select_all_btn.click(
            fn=lambda m: [val for _, val in get_selection_choices(m)],
            inputs=[processing_mode],
            outputs=[selected_parts]
        )

        clear_selection_btn.click(fn=lambda: [], inputs=[], outputs=[selected_parts])

    return demo


# =============================================================================
# 12. API REST LOCAL Y SERVIDOR DE FRONTEND ESTÁTICO (FASTAPI)
# =============================================================================

DIST_DIR = BASE_DIR / "dist"

def build_fastapi_app() -> Any:
    """Construye la aplicación FastAPI con endpoints REST, frontend compilado y Gradio."""
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel

    api_app = FastAPI(title="Crónicas Mundiales — Narration Studio", version="2.0")

    # Habilitar CORS para permitir peticiones desde cualquier origen local
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class ProjectPayload(BaseModel):
        text: str
        processing_mode: str = "scene"
        language: str = "es"
        voice_name: Optional[str] = PREFERRED_VOICE
        ref_audio_path: Optional[str] = None
        exaggeration: float = DEFAULT_EXAGGERATION
        temperature: float = DEFAULT_TEMPERATURE
        cfg_weight: float = DEFAULT_CFG_WEIGHT
        seed: int = DEFAULT_SEED

    class RegeneratePayload(BaseModel):
        processing_mode: str = "scene"
        section_number: int
        part_number: int
        language: str = "es"
        audio_prompt_path: Optional[str] = None
        exaggeration: float = DEFAULT_EXAGGERATION
        temperature: float = DEFAULT_TEMPERATURE
        cfg_weight: float = DEFAULT_CFG_WEIGHT
        seed: int = DEFAULT_SEED

    class BatchRegeneratePayload(BaseModel):
        selected_items: List[List[int]]
        processing_mode: str = "scene"
        language: str = "es"
        audio_prompt_path: Optional[str] = None
        exaggeration: float = DEFAULT_EXAGGERATION
        temperature: float = DEFAULT_TEMPERATURE
        cfg_weight: float = DEFAULT_CFG_WEIGHT
        seed: int = DEFAULT_SEED

    class JoinPayload(BaseModel):
        processing_mode: str = "scene"
        section_number: int

    # -------------------------------------------------------------------------
    # ENDPOINTS DE LA API REST (/api/...)
    # -------------------------------------------------------------------------

    @api_app.get("/api/status")
    def api_status():
        return {
            "status": "online",
            "device": DEVICE,
            "device_label": DEVICE_LABEL,
            "model_loaded": MODEL is not None,
            "model_status": get_model_status_text(),
            "t3_model": T3_MODEL,
            "is_generating": GENERATION_STATE["is_generating"],
            "frontend_served": DIST_DIR.exists() and (DIST_DIR / "index.html").exists()
        }

    @api_app.get("/api/progress")
    def api_progress():
        return GENERATION_STATE

    @api_app.get("/api/voices")
    def api_voices():
        choices = get_voice_choices()
        voice_list = [{"name": name, "path": path} for name, path in choices.items()]
        return {
            "voices": voice_list,
            "default_voice": PREFERRED_VOICE if PREFERRED_VOICE in choices else (voice_list[0]["name"] if voice_list else None)
        }

    @api_app.get("/api/languages")
    def api_languages():
        return {
            "languages": [
                {"code": code, "name": conf["name"], "default_text": conf["text"], "audio_prompt": conf["audio"]}
                for code, conf in LANGUAGE_CONFIG.items()
            ],
            "default_language": "es"
        }

    @api_app.get("/api/project")
    def api_get_project(mode: str = "scene"):
        proj = load_project()
        panel = get_panel_data(mode)
        status_text = get_project_status(mode)
        return {
            "project": proj,
            "panel": panel,
            "status_text": status_text,
            "processing_mode": mode
        }

    @api_app.post("/api/project")
    def api_save_project(payload: ProjectPayload):
        try:
            proj = save_project(
                text_input=payload.text,
                processing_mode=payload.processing_mode,
                language_id=payload.language,
                audio_prompt_path_input=payload.ref_audio_path,
                exaggeration_input=payload.exaggeration,
                temperature_input=payload.temperature,
                seed_num_input=payload.seed,
                cfgw_input=payload.cfg_weight
            )
            return {"status": "ok", "project": proj}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def run_bg_generation(payload: ProjectPayload):
        try:
            generate_tts_audio(
                text_input=payload.text,
                processing_mode=payload.processing_mode,
                language_id=payload.language,
                audio_prompt_path_input=payload.ref_audio_path,
                exaggeration_input=payload.exaggeration,
                temperature_input=payload.temperature,
                seed_num_input=payload.seed,
                cfgw_input=payload.cfg_weight
            )
        except Exception as e:
            print(f"❌ Error en generación en background: {e}")

    @api_app.post("/api/generate")
    def api_generate(payload: ProjectPayload, bg_tasks: BackgroundTasks):
        if GENERATION_STATE["is_generating"]:
            raise HTTPException(status_code=409, detail="Ya existe una tarea de generación en curso.")
        bg_tasks.add_task(run_bg_generation, payload)
        return {"status": "started", "message": "Generación iniciada en segundo plano"}

    @api_app.post("/api/regenerate")
    def api_regenerate(payload: RegeneratePayload):
        try:
            path = regenerate_tts_part(
                processing_mode=payload.processing_mode,
                section_number=payload.section_number,
                part_number=payload.part_number,
                language_id=payload.language,
                audio_prompt_path_input=payload.audio_prompt_path,
                exaggeration_input=payload.exaggeration,
                temperature_input=payload.temperature,
                seed_num_input=payload.seed,
                cfgw_input=payload.cfg_weight
            )
            filename = Path(path).name
            return {
                "status": "ok",
                "filename": filename,
                "audio_url": f"/api/audio/{filename}"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def run_bg_batch_regenerate(payload: BatchRegeneratePayload):
        try:
            items = [(item[0], item[1]) for item in payload.selected_items]
            batch_regenerate_tts_parts(
                selected_items=items,
                processing_mode=payload.processing_mode,
                language_id=payload.language,
                audio_prompt_path_input=payload.audio_prompt_path,
                exaggeration_input=payload.exaggeration,
                temperature_input=payload.temperature,
                seed_num_input=payload.seed,
                cfgw_input=payload.cfg_weight
            )
        except Exception as e:
            print(f"❌ Error en batch regenerate background: {e}")

    @api_app.post("/api/regenerate-batch")
    def api_regenerate_batch(payload: BatchRegeneratePayload, bg_tasks: BackgroundTasks):
        if GENERATION_STATE["is_generating"]:
            raise HTTPException(status_code=409, detail="Ya existe una tarea en curso.")
        bg_tasks.add_task(run_bg_batch_regenerate, payload)
        return {"status": "started", "message": "Regeneración por lote iniciada"}

    @api_app.post("/api/join")
    def api_join(payload: JoinPayload):
        try:
            path = join_section_audio(payload.processing_mode, payload.section_number)
            filename = Path(path).name
            return {
                "status": "ok",
                "filename": filename,
                "audio_url": f"/api/audio/{filename}"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @api_app.post("/api/join-all")
    def api_join_all(payload: JoinPayload):
        try:
            path = join_all_audio(payload.processing_mode)
            filename = Path(path).name
            return {
                "status": "ok",
                "filename": filename,
                "audio_url": f"/api/audio/{filename}"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @api_app.get("/api/audio/{filename}")
    def api_audio(filename: str):
        safe_name = Path(filename).name
        candidates = [
            OUTPUTS_DIR / "final" / safe_name,
            SEGMENTS_DIR / safe_name,
            OUTPUTS_DIR / safe_name,
        ]
        for p in candidates:
            if p.exists() and p.is_file():
                return FileResponse(path=str(p.resolve()), media_type="audio/wav", filename=safe_name)
        raise HTTPException(status_code=404, detail="Archivo de audio no encontrado")

    # -------------------------------------------------------------------------
    # ARCHIVOS ESTÁTICOS DE AUDIO Y ASSETS DEL FRONTEND (SIN DEPENDER DE AIOFILES)
    # -------------------------------------------------------------------------

    # 1. Servir los assets compilados de Vite si existen (/assets/...)
    @api_app.get("/assets/{asset_path:path}")
    def serve_asset(asset_path: str):
        safe_path = DIST_DIR / "assets" / asset_path
        if safe_path.exists() and safe_path.is_file():
            media_type = None
            if safe_path.suffix == ".js":
                media_type = "text/javascript"
            elif safe_path.suffix == ".css":
                media_type = "text/css"
            elif safe_path.suffix in [".woff", ".woff2"]:
                media_type = "font/woff2"
            return FileResponse(str(safe_path.resolve()), media_type=media_type)
        raise HTTPException(status_code=404, detail="Asset no encontrado")

    # 2. Servir archivos WAV generados en /outputs/segments/
    @api_app.get("/outputs/segments/{filename}")
    def serve_segment(filename: str):
        safe_name = Path(filename).name
        audio_path = SEGMENTS_DIR / safe_name
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Segmento no encontrado")
        return FileResponse(path=str(audio_path), media_type="audio/wav", filename=safe_name)

    # 3. Montar Gradio en /gradio si está instalado (como fallback de prueba)
    try:
        import gradio as gr
        demo = create_studio_app()
        if demo is not None:
            gr.mount_gradio_app(api_app, demo, path="/gradio")
            print("🚀 [Gradio] Interfaz fallback montada con éxito en: /gradio")
    except Exception as g_err:
        print(f"ℹ️ Gradio fallback no montado en FastAPI: {g_err}")

    # 4. Servir la ruta raíz (/) - Interfaz nativa de Python / HTML / CSS / JS sin npm
    @api_app.get("/", response_class=FileResponse)
    def serve_root():
        # A. Si existe la plantilla nativa del estudio (sin requerir Node/npm)
        template_file = BASE_DIR / "templates" / "index.html"
        if template_file.exists():
            return FileResponse(str(template_file.resolve()))

        # B. Si existe dist/index.html
        index_file = DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file.resolve()))

        # C. Redirigir a Gradio como fallback
        return HTMLResponse("<meta http-equiv='refresh' content='0; url=/gradio'>")

    # 5. Fallback para rutas SPA del frontend
    @api_app.get("/{full_path:path}")
    def serve_spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("gradio") or full_path.startswith("outputs/"):
            raise HTTPException(status_code=404, detail="Recurso no encontrado")

        candidate = DIST_DIR / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate.resolve()))

        template_file = BASE_DIR / "templates" / "index.html"
        if template_file.exists():
            return FileResponse(str(template_file.resolve()))

        index_file = DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file.resolve()))

        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return api_app


# =============================================================================
# 13. PUNTO DE ENTRADA Y SERVIDOR HTTP LOCAL
# =============================================================================

def start_server(port: int = 8000, host: str = "127.0.0.1", gradio_only: bool = False, open_browser: bool = True):
    """Inicia el servidor backend según dependencias disponibles."""
    if gradio_only:
        print("🖥️ Iniciando en modo Gradio-Only...")
        demo = create_studio_app()
        if demo:
            demo.queue().launch(server_name=host, server_port=port, share=False)
        return

    # 1. Intentar iniciar con FastAPI y Uvicorn
    try:
        import fastapi
        import uvicorn
        app = build_fastapi_app()

        target_url = f"http://localhost:{port}"

        print("\n" + "=" * 65)
        print("🎙️ CRÓNICAS MUNDIALES — NARRATION STUDIO INICIADO")
        print(f"🌐 Frontend Moderno: {target_url}")
        print(f"📡 API REST & Audio: {target_url}/api")
        print(f"🎛️ Gradio Fallback:  {target_url}/gradio")
        print(f"🚀 Dispositivo:      {DEVICE_LABEL}")
        print("=" * 65 + "\n")

        # Apertura automática del navegador tras breve pausa
        if open_browser:
            def _launch_browser():
                time.sleep(1.2)
                try:
                    import webbrowser
                    webbrowser.open(target_url)
                except Exception:
                    pass
            threading.Thread(target=_launch_browser, daemon=True).start()

        try:
            uvicorn.run(app, host=host, port=port, log_level="info")
        except OSError as port_err:
            if "address already in use" in str(port_err).lower() or "10048" in str(port_err):
                alt_port = port + 1
                print(f"⚠️ El puerto {port} está ocupado. Probando en http://localhost:{alt_port}...")
                uvicorn.run(app, host=host, port=alt_port, log_level="info")
            else:
                raise port_err
        return
    except ImportError as imp_err:
        print(f"⚠️ FastAPI o Uvicorn no están disponibles ({imp_err}).")
        print("ℹ️ Intentando iniciar Gradio standalone...")
    except Exception as general_err:
        print(f"⚠️ Error al iniciar FastAPI: {general_err}")
        traceback.print_exc()

    # 2. Si FastAPI no está instalado, intentar lanzar Gradio standalone
    try:
        import gradio as gr
        print(f"🖥️ Lanzando Gradio standalone en http://localhost:{port}...")
        demo = create_studio_app()
        if demo:
            demo.queue().launch(server_name=host, server_port=port, share=False)
            return
    except ImportError:
        pass
    except Exception as g_err:
        print(f"❌ Error al iniciar Gradio: {g_err}")
        traceback.print_exc()

    print("\n" + "=" * 65)
    print("❌ No se encontró FastAPI ni Gradio instalados en este entorno de Python.")
    print(f"👉 Intérprete actual: {sys.executable}")
    print("👉 Por favor ejecuta:")
    print(f"   \"{sys.executable}\" -m pip install -r requirements.txt")
    print("=" * 65 + "\n")
    try:
        input("Presiona Enter para cerrar...")
    except Exception:
        pass
    sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crónicas Mundiales — Narration Studio Backend")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del servidor (por defecto 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host a escuchar (por defecto 127.0.0.1)")
    parser.add_argument("--gradio-only", action="store_true", help="Lanzar únicamente la interfaz Gradio en lugar de la aplicación completa")
    parser.add_argument("--no-browser", action="store_true", help="No abrir automáticamente el navegador")
    args = parser.parse_args()

    start_server(
        port=args.port,
        host=args.host,
        gradio_only=args.gradio_only,
        open_browser=not args.no_browser
    )
