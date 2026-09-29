#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
CHATTERBOX PRIME — AI NARRATION STUDIO
Backend Python & API Local para Estudio Profesional de Narración
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
import shutil
import inspect
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
    if sys.platform == 'win32' and hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
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
# 1. CONFIGURACIÓN DEL SISTEMA Y HARDWARE (CPU / CUDA AUTOMÁTICO)
# =============================================================================

# Detección automática interna de hardware: CPU actual y preparado para CUDA/GPU futura
CUDA_AVAILABLE = torch.cuda.is_available()
DEVICE = "cuda" if CUDA_AVAILABLE else "cpu"
DEVICE_LABEL = f"CUDA ({torch.cuda.get_device_name(0)})" if CUDA_AVAILABLE else "CPU"
T3_MODEL = os.getenv("CHATTERBOX_MULTILINGUAL_T3_MODEL", "v2")

# Rutas del proyecto usando pathlib
BASE_DIR = Path(__file__).resolve().parent
VOICES_DIR = BASE_DIR / "voices"
OUTPUTS_DIR = BASE_DIR / "outputs"
SEGMENTS_DIR = OUTPUTS_DIR / "segments"
FINAL_DIR = OUTPUTS_DIR / "final"
PROJECT_FILE = OUTPUTS_DIR / "project.json"

# Asegurar existencia de directorios básicos
VOICES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR.mkdir(parents=True, exist_ok=True)

# Parámetros predeterminados para producción según especificación Chatterbox Prime
DEFAULT_SEED = 737219296
DEFAULT_EXAGGERATION = 0.35
DEFAULT_TEMPERATURE = 0.55
DEFAULT_CFG_WEIGHT = 0.5
MAX_CHARS = 250
PREFERRED_VOICE = "Brian Warm Clonacion Voz"

# =============================================================================
# 2. GESTIÓN DE MODELO (CARGA LAZY / SINGLETON Y VERIFICACIÓN V2/V3)
# =============================================================================

MODEL: Optional[Any] = None
MODEL_STATUS = "⚪ Modelo no cargado"
GENERATION_LOCK = threading.Lock()
CANCEL_REQUESTED = False

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


def inspect_chatterbox_installation() -> Dict[str, Any]:
    """
    Inspecciona rigurosamente la versión instalada de Chatterbox y comprueba
    su compatibilidad real con V3 antes de intentar cargar cualquier variante.
    """
    info: Dict[str, Any] = {
        "installed": ChatterboxMultilingualTTS is not None,
        "version": "No instalada",
        "has_t3_param": False,
        "v3_compatible": False,
        "active_model_version": "v2",
        "device": DEVICE,
        "cuda_available": CUDA_AVAILABLE,
        "gpu_name": torch.cuda.get_device_name(0) if CUDA_AVAILABLE else None,
    }

    try:
        import chatterbox
        info["version"] = getattr(chatterbox, "__version__", "instalada (local/git)")
    except Exception:
        pass

    if ChatterboxMultilingualTTS is not None:
        try:
            sig = inspect.signature(ChatterboxMultilingualTTS.from_pretrained)
            info["has_t3_param"] = "t3_model" in sig.parameters

            # Verificar si v3 está soportado en la clase o en los modelos de chatterbox
            class_repr = repr(ChatterboxMultilingualTTS)
            source_snippet = ""
            try:
                source_snippet = inspect.getsource(ChatterboxMultilingualTTS.from_pretrained)
            except Exception:
                pass

            # Si el código o las constantes mencionan explícitamente v3
            supports_v3 = "v3" in source_snippet.lower() or "t3_v3" in source_snippet.lower()
            info["v3_compatible"] = supports_v3

            # Usar v3 solo si está verdaderamente soportado o si se configuró explícitamente y es seguro
            env_target = os.getenv("CHATTERBOX_MULTILINGUAL_T3_MODEL", "v2").lower()
            if env_target == "v3" and supports_v3:
                info["active_model_version"] = "v3"
            else:
                info["active_model_version"] = "v2"
        except Exception as e:
            info["inspect_error"] = str(e)
            info["active_model_version"] = "v2"

    return info


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
    Verifica compatibilidad de parámetros antes de llamar a from_pretrained.
    """
    global MODEL, MODEL_STATUS
    if MODEL is None:
        if ChatterboxMultilingualTTS is None:
            raise RuntimeError(
                "La librería 'chatterbox' no está instalada en el entorno de Python. "
                "Instálala con: pip install chatterbox-tts"
            )

        env_info = inspect_chatterbox_installation()
        print(f"\n📦 [Chatterbox Prime] Verificando instalación: {env_info['version']} en {DEVICE.upper()}...")

        if progress_callback:
            try:
                progress_callback(0.05, desc="Cargando modelo Chatterbox en memoria...")
            except Exception:
                pass

        try:
            # Inspeccionar parámetros de from_pretrained
            sig = inspect.signature(ChatterboxMultilingualTTS.from_pretrained)
            kwargs: Dict[str, Any] = {}

            if "t3_model" in sig.parameters:
                # Solo usar V3 si está comprobado en la API real
                chosen_v = env_info.get("active_model_version", "v2")
                kwargs["t3_model"] = chosen_v
                print(f"📦 [Chatterbox Prime] t3_model verificado: {chosen_v}")

            try:
                MODEL = ChatterboxMultilingualTTS.from_pretrained(DEVICE, **kwargs)
            except TypeError as te:
                print(f"⚠️ [Chatterbox Prime] Incompatibilidad de argumentos ({te}). Cargando solo con DEVICE={DEVICE}...")
                MODEL = ChatterboxMultilingualTTS.from_pretrained(DEVICE)

            if hasattr(MODEL, "to") and str(getattr(MODEL, "device", "")) != DEVICE:
                MODEL.to(DEVICE)

            MODEL_STATUS = f"🟢 Modelo cargado en {DEVICE.upper()}"
            print(f"✅ [Chatterbox Prime] Modelo listo en {getattr(MODEL, 'device', DEVICE)}")
        except Exception as e:
            MODEL_STATUS = f"🔴 Error al cargar modelo: {str(e)}"
            print(f"❌ [Chatterbox Prime] Error crítico al cargar modelo: {e}")
            traceback.print_exc()
            raise RuntimeError(f"No se pudo cargar el modelo Chatterbox: {e}")

    return MODEL


def set_seed(seed: int) -> None:
    """
    Establece la semilla para garantizar reproducibilidad exacta.
    Elimina cualquier creación de logs TXT innecesarios.
    """
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    np.random.seed(seed % (2**32 - 1))
    random.seed(seed)


# =============================================================================
# 3. BIBLIOTECA DE VOCES Y MUESTRAS MULTILINGÜES
# =============================================================================

def get_voice_files() -> List[Path]:
    """Obtiene la lista ordenada de archivos WAV en la carpeta voices."""
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(list(VOICES_DIR.glob("*.wav")), key=lambda p: p.stem.lower())


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
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/ar_f.flac",
        "text": "في الشهر الماضي وصلنا إلى معلم جديد: ملياري مشاهدة على قناتنا على يوتيوب."
    },
    "da": {
        "name": "Danés",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/da_m1.flac",
        "text": "Sidste måned nåede vi en ny milepæl med to milliarder visninger på vores YouTube-kanal."
    },
    "de": {
        "name": "Alemán",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/de_m.flac",
        "text": "Letzten Monat haben wir einen neuen Meilenstein erreicht: zwei Milliarden Aufrufe auf unserem YouTube-Kanal."
    },
    "el": {
        "name": "Griego",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/el_m.flac",
        "text": "Τον περασμένο μήνα φτάσαμε σε ένα νέο ορόσημο: δύο δισεκατομμύρια προβολές στο κανάλι μας στο YouTube."
    },
    "en": {
        "name": "Inglés",
        "audio": "https://storage.googleapis.com/chatterbox-demo-samples/mtl_prompts/en_f1.flac",
        "text": "Last month we reached a new milestone: two billion views on our YouTube channel."
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


def normalize_numbers_for_tts(text: str, language_id: str = "es") -> str:
    """
    Convierte internamente números a español para la síntesis de voz,
    conservando intacto el texto original visible en el editor.
    """
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
# 5. SEGMENTACIÓN INTELIGENTE JERÁRQUICA (PÁRRAFO -> ORACIÓN -> PALABRA)
# =============================================================================

def split_text_for_tts(text: str, max_chars: int = MAX_CHARS) -> List[str]:
    """
    Divide el texto en partes de aproximadamente max_chars (~250 caracteres) siguiendo la jerarquía:
    1. Párrafo
    2. Oración (delimitada por signos de puntuación: . ! ? ; o saltos de línea)
    3. Palabra (si una sola oración supera max_chars)

    Evita cortar oraciones y nunca corta palabras innecesariamente.
    """
    text = text.strip()
    if not text:
        return []

    # 1. Separar por párrafos
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    chunks: List[str] = []

    for paragraph in paragraphs:
        # Si el párrafo cabe en el límite, se conserva entero
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue

        # 2. Dividir en oraciones respetando puntuación
        raw_sentences = re.findall(r'[^.!?;\n]+(?:[.!?;\n]+["\']?|$)', paragraph)
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        current_chunk = ""

        for sentence in sentences:
            # Caso 2A: Si la oración en sí sola supera max_chars, dividir por palabras sin cortar palabras
            if len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                words = sentence.split()
                word_chunk = ""
                for word in words:
                    candidate = f"{word_chunk} {word}".strip() if word_chunk else word
                    if len(candidate) <= max_chars:
                        word_chunk = candidate
                    else:
                        if word_chunk:
                            chunks.append(word_chunk.strip())
                        word_chunk = word
                if word_chunk:
                    current_chunk = word_chunk
                continue

            # Caso 2B: Acumular oraciones completas mientras no superen max_chars
            candidate = f"{current_chunk} {sentence}".strip() if current_chunk else sentence
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
# 6. PARSERS ROBUSTOS DE PÁRRAFOS Y ESCENAS
# =============================================================================

def parse_paragraphs_from_script(text_input: str) -> List[Dict[str, Any]]:
    """
    Parsea el guion separándolo por párrafos (líneas en blanco).
    """
    text_input = text_input.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text_input:
        raise ValueError("El guion está vacío. Introduce texto para continuar.")

    paragraphs = re.split(r"\n\s*\n", text_input)
    result = []
    number = 1

    for p in paragraphs:
        p_text = p.strip()
        if not p_text:
            continue
        result.append({
            "number": number,
            "title": f"Párrafo {number}",
            "text": p_text
        })
        number += 1

    if not result:
        result.append({
            "number": 1,
            "title": "Párrafo 1",
            "text": text_input
        })
    return result


def parse_scenes_from_script(text_input: str) -> List[Dict[str, Any]]:
    """
    Parsea el guion detectando 'ESCENA 1', 'ESCENA 2', etc.
    Permite texto introductorio antes de la primera escena sin error (lo asigna a la Escena 1).
    Soporta múltiples variantes: ESCENA 1, Escena 01, ESCENA 1: Título, ESCENA 1 — Título, CAPÍTULO 1, etc.
    Corrige definitivamente cualquier fallo de generación de la Escena 1.
    """
    text_input = text_input.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text_input:
        raise ValueError("El guion está vacío. Introduce texto para continuar.")

    lines = text_input.split("\n")
    scene_pattern = re.compile(
        r"^\s*(?:ESCENA|Escena|SCENE|Scene|CAPÍTULO|Capítulo|PARTE|Parte)\s+(\d+)(?:\s*[—–:\-\.]\s*(.*))?\s*$",
        re.IGNORECASE
    )

    scenes: List[Dict[str, Any]] = []
    current_scene: Optional[Dict[str, Any]] = None
    pre_scene_lines: List[str] = []

    for line in lines:
        match = scene_pattern.match(line)
        if match:
            if current_scene is not None:
                current_scene["text"] = "\n".join(current_scene["text_lines"]).strip()
                del current_scene["text_lines"]
                if current_scene["text"]:
                    scenes.append(current_scene)

            scene_num = int(match.group(1))
            scene_title = (match.group(2) or "").strip()
            current_scene = {
                "number": scene_num,
                "title": scene_title,
                "text_lines": []
            }
        else:
            if current_scene is not None:
                current_scene["text_lines"].append(line)
            else:
                if line.strip():
                    pre_scene_lines.append(line)

    if current_scene is not None:
        current_scene["text"] = "\n".join(current_scene["text_lines"]).strip()
        del current_scene["text_lines"]
        if current_scene["text"]:
            scenes.append(current_scene)

    # Si había texto introductorio antes de la primera escena, unirlo sin arrojar error destructivo
    if pre_scene_lines:
        intro_text = "\n".join(pre_scene_lines).strip()
        if not scenes:
            scenes.append({
                "number": 1,
                "title": "Escena 1",
                "text": intro_text
            })
        else:
            if scenes[0]["number"] == 1:
                scenes[0]["text"] = f"{intro_text}\n\n{scenes[0]['text']}".strip()
            else:
                scenes.insert(0, {
                    "number": 1,
                    "title": "Introducción",
                    "text": intro_text
                })

    if not scenes:
        scenes.append({
            "number": 1,
            "title": "Escena 1",
            "text": text_input
        })

    # Renumerar secuencialmente de forma segura
    for idx, s in enumerate(scenes):
        s["number"] = idx + 1
        if not s.get("title"):
            s["title"] = f"Escena {s['number']}"

    return scenes


def build_project_structure(text_input: str, processing_mode: str, language_id: str) -> List[Dict[str, Any]]:
    """
    Construye la estructura completa del proyecto en base al texto y al modo (scene / paragraph).
    Ambos modos comparten exactamente la misma lógica de división y generación.
    """
    if processing_mode == "scene":
        sections = parse_scenes_from_script(text_input)
    else:
        sections = parse_paragraphs_from_script(text_input)

    processed_sections = []
    for s in sections:
        # Texto normalizado fonéticamente con números en español para TTS
        norm_text = normalize_numbers_for_tts(s["text"], language_id)

        # División inteligente en bloques de ~250 caracteres
        norm_parts = split_text_for_tts(norm_text, max_chars=MAX_CHARS)
        raw_parts = split_text_for_tts(s["text"], max_chars=MAX_CHARS)

        parts_list = []
        for idx, n_part in enumerate(norm_parts):
            raw_display = raw_parts[idx] if idx < len(raw_parts) else n_part
            p_num = idx + 1
            filename = get_section_filename(processing_mode, s["number"], p_num)
            part_path = get_section_path(processing_mode, s["number"], p_num)
            has_audio = part_path.exists() and part_path.stat().st_size > 44

            parts_list.append({
                "number": p_num,
                "text": raw_display,              # Visible para el usuario
                "normalized_text": n_part,        # Usado para síntesis TTS
                "audio_filename": filename,
                "audio_url": f"/outputs/segments/{filename}" if has_audio else None,
                "has_audio": has_audio,
                "status": "Listo" if has_audio else "Pendiente"
            })

        processed_sections.append({
            "number": s["number"],
            "title": s.get("title", f"{get_section_label(processing_mode)} {s['number']}"),
            "text": s["text"],
            "normalized_text": norm_text,
            "parts": parts_list
        })

    return processed_sections


# =============================================================================
# 7. PERSISTENCIA DEL PROYECTO (JSON) Y AUTOSAVE
# =============================================================================

def save_project(
    text_input: str,
    processing_mode: str,
    language_id: str,
    audio_prompt_path_input: Optional[str] = None,
    exaggeration_input: float = DEFAULT_EXAGGERATION,
    temperature_input: float = DEFAULT_TEMPERATURE,
    seed_num_input: int = DEFAULT_SEED,
    cfgw_input: float = DEFAULT_CFG_WEIGHT,
    voice_name_input: Optional[str] = PREFERRED_VOICE
) -> Dict[str, Any]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    sections = build_project_structure(text_input, processing_mode, language_id)

    project = {
        "last_script": text_input,
        "processing_mode": processing_mode,
        "voice_name": voice_name_input or PREFERRED_VOICE,
        "settings": {
            "language": language_id,
            "voice_name": voice_name_input or PREFERRED_VOICE,
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
# 8. RUTAS Y NOMBRES DE ARCHIVOS EXACTOS
# =============================================================================

def get_section_label(processing_mode: str) -> str:
    return "Escena" if processing_mode == "scene" else "Parrafo"


def get_section_filename(processing_mode: str, section_number: int, part_number: int) -> str:
    """Nombres exactos: Parrafo_001_Parte_01.wav o Escena_001_Parte_01.wav"""
    prefix = get_section_label(processing_mode)
    return f"{prefix}_{section_number:03d}_Parte_{part_number:02d}.wav"


def get_section_path(processing_mode: str, section_number: int, part_number: int) -> Path:
    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = get_section_filename(processing_mode, section_number, part_number)
    return SEGMENTS_DIR / filename


def get_final_joined_path(processing_mode: str, section_number: int) -> Path:
    """Nombres exactos: Parrafo_001.wav o Escena_001.wav"""
    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
    prefix = get_section_label(processing_mode)
    return SEGMENTS_DIR / f"{prefix}_{section_number:03d}.wav"


# =============================================================================
# 9. GENERACIÓN Y SÍNTESIS DE AUDIO (CONTINUACIÓN, CANCELACIÓN Y RESISTENCIA A ERRORES)
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
    voice_name_input: Optional[str] = PREFERRED_VOICE,
    progress: Optional[Any] = None
) -> Optional[str]:
    """
    Analiza el guion, muestra párrafos/escenas y sus partes.
    Genera únicamente los archivos faltantes, conservando los existentes.
    Permite continuar una producción incompleta.
    Protección contra doble generación y soporte para cancelación en vivo.
    """
    global GENERATION_STATE, CANCEL_REQUESTED
    CANCEL_REQUESTED = False

    if not text_input or not text_input.strip():
        raise ValueError("El guion está vacío. Introduce texto antes de generar.")

    with GENERATION_LOCK:
        GENERATION_STATE["is_generating"] = True
        GENERATION_STATE["errors"] = []
        GENERATION_STATE["message"] = "Analizando guion y preparando estructura..."

        try:
            project = save_project(
                text_input=text_input,
                processing_mode=processing_mode,
                language_id=language_id,
                audio_prompt_path_input=audio_prompt_path_input,
                exaggeration_input=exaggeration_input,
                temperature_input=temperature_input,
                seed_num_input=seed_num_input,
                cfgw_input=cfgw_input,
                voice_name_input=voice_name_input
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

            print("\n" + "=" * 65)
            print("🎬 [CHATTERBOX PRIME] INICIANDO PRODUCCIÓN DE AUDIO")
            print(f"Modo: {'ESCENAS' if processing_mode == 'scene' else 'PÁRRAFOS'} | Total partes: {total_count}")
            print(f"Seed: {fixed_seed} (fijo) | Dispositivo: {DEVICE.upper()} (CUDA: {CUDA_AVAILABLE})")
            print("=" * 65)

            for idx, (sec, part, segment_path) in enumerate(all_parts_to_process):
                if CANCEL_REQUESTED:
                    print("🛑 [Chatterbox Prime] Generación cancelada por el usuario.")
                    GENERATION_STATE["message"] = "Generación cancelada por el usuario."
                    break

                sec_num = int(sec["number"])
                part_num = int(part["number"])
                # Se utiliza el texto normalizado fonéticamente para la síntesis
                chunk = part.get("normalized_text") or part.get("text", "")
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

                # Conservar existentes y continuar producción incompleta
                if segment_path.exists() and segment_path.stat().st_size > 44:
                    print(f"⏩ [CONSERVANDO EXISTENTE] {filename}")
                    total_skipped += 1
                    last_generated_path = str(segment_path.resolve())
                    GENERATION_STATE["last_generated"] = filename
                    continue

                set_seed(fixed_seed)
                print(f"🎙️ [Sintetizando] {label} {sec_num} Parte {part_num} ({len(chunk)} chars)...")

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
                    # Si una parte falla, las demás deben poder continuar
                    continue

            if CUDA_AVAILABLE:
                torch.cuda.empty_cache()

            if not CANCEL_REQUESTED:
                GENERATION_STATE["message"] = f"Producción finalizada. {total_generated} generados, {total_skipped} reutilizados."
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
    """Regenera una parte individual sin alterar las demás."""
    global GENERATION_STATE, CANCEL_REQUESTED
    CANCEL_REQUESTED = False

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
                            selected_text = part.get("normalized_text") or part.get("text")
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

            if CUDA_AVAILABLE:
                torch.cuda.empty_cache()

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
    """Regenera en lote las partes seleccionadas por el usuario."""
    global GENERATION_STATE, CANCEL_REQUESTED
    CANCEL_REQUESTED = False

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
                if CANCEL_REQUESTED:
                    print("🛑 [Regeneración Lote] Cancelación solicitada.")
                    break

                label = get_section_label(processing_mode)
                GENERATION_STATE["current_step"] = idx + 1
                GENERATION_STATE["current_label"] = f"{label} {sec_num} Parte {part_num}"
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
                                    selected_text = part.get("normalized_text") or part.get("text")
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

            if CUDA_AVAILABLE:
                torch.cuda.empty_cache()

            msg = f"Regeneración terminada: {generated} parte(s) procesada(s)."
            if errors:
                msg += f" Hubo {len(errors)} error(es)."
            GENERATION_STATE["message"] = msg
            return msg
        finally:
            GENERATION_STATE["is_generating"] = False


# =============================================================================
# 10. UNIÓN DE AUDIO (SECCIONES Y MASTER COMPLETO)
# =============================================================================

def join_section_audio(processing_mode: str, section_number: int) -> str:
    """
    🔗 Unir párrafo / 🔗 Unir escena:
    Concatena los WAVs existentes de la sección sin volver a sintetizarlos
    y conservando todas las partes originales intactas.
    Guarda como: Parrafo_001.wav o Escena_001.wav
    """
    project = load_project()
    if not project:
        raise ValueError("No hay ningún proyecto guardado.")

    sec_num = int(section_number)
    selected_section: Optional[Dict[str, Any]] = None

    for section in project.get("sections", []):
        if int(section.get("number", 0)) == sec_num:
            selected_section = section
            break

    label = get_section_label(processing_mode)
    if selected_section is None:
        raise ValueError(f"No se encontró {label} {sec_num}.")

    parts = selected_section.get("parts", [])
    if not parts:
        raise ValueError(f"{label} {sec_num} no contiene partes.")

    audio_paths = []
    missing_parts = []
    for part in parts:
        p_num = int(part.get("number", 0))
        part_path = get_section_path(processing_mode, sec_num, p_num)
        if not part_path.exists() or part_path.stat().st_size <= 44:
            missing_parts.append(f"Parte {p_num}")
        else:
            audio_paths.append(part_path)

    if missing_parts:
        raise ValueError(
            f"Faltan audios en {label} {sec_num}: {', '.join(missing_parts)}. "
            "Genera las partes faltantes antes de unir."
        )

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
    print(f"🔗 [AUDIO SECCIÓN UNIDO] {final_path.name}")
    return str(final_path.resolve())


def join_all_audio(processing_mode: str = "scene") -> str:
    """
    Concatena todos los segmentos del proyecto en un solo archivo WAV maestro.
    """
    project = load_project()
    if not project:
        raise ValueError("No hay ningún proyecto guardado.")

    sections = project.get("sections", [])
    if not sections:
        raise ValueError("El proyecto no contiene escenas ni párrafos.")

    audio_paths = []
    missing_parts = []

    for section in sections:
        s_num = int(section.get("number", 0))
        parts = section.get("parts", [])
        for part in parts:
            p_num = int(part.get("number", 0))
            part_path = get_section_path(processing_mode, s_num, p_num)
            if not part_path.exists() or part_path.stat().st_size <= 44:
                missing_parts.append(f"{get_section_label(processing_mode)} {s_num} Parte {p_num}")
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
    final_path = final_dir / "Master_Chatterbox_Prime.wav"
    torchaudio.save(str(final_path.resolve()), joined_audio, target_sr)
    print(f"🏆 [MASTER COMPLETO GENERADO] {final_path.name}")
    return str(final_path.resolve())


# =============================================================================
# 11. RESUMEN Y VISTAS DE PRODUCCIÓN
# =============================================================================

def get_panel_data(mode: str = "scene") -> List[Dict[str, Any]]:
    """Obtiene los datos estructurados para el panel de producción del frontend."""
    project = load_project()
    if not project:
        return []

    sections = project.get("sections", [])
    data = []
    for sec in sections:
        s_num = int(sec.get("number", 0))
        sec_title = sec.get("title") or f"{get_section_label(mode)} {s_num}"
        joined_path = get_final_joined_path(mode, s_num)
        has_joined = joined_path.exists() and joined_path.stat().st_size > 44

        parts_data = []
        for p in sec.get("parts", []):
            p_num = int(p.get("number", 0))
            p_path = get_section_path(mode, s_num, p_num)
            has_audio = p_path.exists() and p_path.stat().st_size > 44
            filename = p_path.name
            parts_data.append({
                "number": p_num,
                "text": p.get("text", ""),
                "normalized_text": p.get("normalized_text", ""),
                "path": str(p_path.resolve()) if has_audio else None,
                "filename": filename,
                "audio_url": f"/outputs/segments/{filename}" if has_audio else None,
                "has_audio": has_audio,
                "status": "Listo" if has_audio else "Pendiente"
            })

        data.append({
            "number": s_num,
            "title": sec_title,
            "text": sec.get("text", ""),
            "has_joined": has_joined,
            "joined_filename": joined_path.name if has_joined else None,
            "joined_audio_url": f"/outputs/segments/{joined_path.name}" if has_joined else None,
            "parts": parts_data
        })
    return data


def get_project_summary(mode: str = "scene") -> Dict[str, Any]:
    """Genera las métricas consolidadas de producción."""
    panel = get_panel_data(mode)
    total_sections = len(panel)
    total_parts = sum(len(s.get("parts", [])) for s in panel)
    ready_parts = sum(sum(1 for p in s.get("parts", []) if p.get("has_audio")) for s in panel)
    pending_parts = total_parts - ready_parts
    percent = round((ready_parts / max(1, total_parts)) * 100) if total_parts > 0 else 0
    errors_count = len(GENERATION_STATE.get("errors", []))

    return {
        "mode": mode,
        "mode_label": "Escenas" if mode == "scene" else "Párrafos",
        "total_sections": total_sections,
        "total_parts": total_parts,
        "ready_parts": ready_parts,
        "pending_parts": pending_parts,
        "errors_count": errors_count,
        "percent": percent,
        "is_generating": GENERATION_STATE["is_generating"],
        "current_label": GENERATION_STATE["current_label"],
        "message": GENERATION_STATE["message"]
    }


def get_project_status(mode: str = "scene") -> str:
    summ = get_project_summary(mode)
    return (
        f"📊 **{summ['mode_label']}**: {summ['total_sections']} | "
        f"**Partes**: {summ['ready_parts']}/{summ['total_parts']} ({summ['percent']}%) | "
        f"**Pendientes**: {summ['pending_parts']} | **Errores**: {summ['errors_count']}"
    )


# =============================================================================
# 12. API REST LOCAL Y SERVIDOR (FASTAPI)
# =============================================================================

DIST_DIR = BASE_DIR / "dist"

def build_fastapi_app() -> Any:
    """Construye la aplicación FastAPI profesional para Chatterbox Prime."""
    from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, UploadFile, File, Form
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
    from pydantic import BaseModel

    api_app = FastAPI(title="Chatterbox Prime — AI Narration Studio", version="3.0")

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

    class RegenerateFromHerePayload(BaseModel):
        processing_mode: str = "scene"
        section_number: int
        part_number: int
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
    # ENDPOINTS DE ESTADO Y HARDWARE
    # -------------------------------------------------------------------------

    @api_app.get("/api/status")
    def api_status():
        info = inspect_chatterbox_installation()
        return {
            "status": "online",
            "device": DEVICE,
            "device_label": DEVICE_LABEL,
            "cuda_available": CUDA_AVAILABLE,
            "model_loaded": MODEL is not None,
            "model_status": get_model_status_text(),
            "chatterbox_version": info.get("version"),
            "v3_compatible": info.get("v3_compatible"),
            "active_model": info.get("active_model_version"),
            "is_generating": GENERATION_STATE["is_generating"],
            "frontend_served": (BASE_DIR / "templates" / "index.html").exists() or (DIST_DIR / "index.html").exists()
        }

    @api_app.get("/api/progress")
    def api_progress():
        return GENERATION_STATE

    @api_app.post("/api/cancel")
    def api_cancel():
        global CANCEL_REQUESTED, GENERATION_STATE
        if GENERATION_STATE["is_generating"]:
            CANCEL_REQUESTED = True
            GENERATION_STATE["message"] = "Cancelando proceso..."
            return {"status": "cancelling", "message": "Petición de cancelación enviada."}
        return {"status": "idle", "message": "No hay procesos activos."}

    # -------------------------------------------------------------------------
    # ADMINISTRAR VOCES (SUBIR, ELIMINAR, REPRODUCIR, REFRESCAR)
    # -------------------------------------------------------------------------

    @api_app.get("/api/voices")
    def api_voices():
        VOICES_DIR.mkdir(parents=True, exist_ok=True)
        files = get_voice_files()
        voice_list = []
        for f in files:
            size_kb = round(f.stat().st_size / 1024, 1)
            voice_list.append({
                "name": f.stem,
                "filename": f.name,
                "path": str(f.resolve()),
                "url": f"/api/voices/{f.name}/preview",
                "size_kb": size_kb,
                "is_default": f.stem == PREFERRED_VOICE
            })

        if not any(v["name"] == PREFERRED_VOICE for v in voice_list):
            voice_list.insert(0, {
                "name": PREFERRED_VOICE,
                "filename": f"{PREFERRED_VOICE}.wav",
                "path": str((VOICES_DIR / f"{PREFERRED_VOICE}.wav").resolve()),
                "url": f"/api/voices/{PREFERRED_VOICE}.wav/preview",
                "size_kb": 0,
                "is_default": True
            })

        default_v = PREFERRED_VOICE if any(v["name"] == PREFERRED_VOICE for v in voice_list) else (voice_list[0]["name"] if voice_list else None)
        return {"voices": voice_list, "default_voice": default_v}

    @api_app.post("/api/voices/upload")
    async def api_upload_voice(file: UploadFile = File(...), name: Optional[str] = Form(None)):
        VOICES_DIR.mkdir(parents=True, exist_ok=True)
        raw_name = (name or Path(file.filename or "Nueva_Voz").stem).strip()
        safe_name = re.sub(r'[\\/*?:"<>|]', '', raw_name).strip() or "Nueva_Voz"
        dest_path = VOICES_DIR / f"{safe_name}.wav"

        content = await file.read()
        with open(dest_path, "wb") as f_out:
            f_out.write(content)

        print(f"🎙️ [Voces] Archivo guardado automáticamente en: {dest_path.name}")
        return api_voices()

    @api_app.delete("/api/voices/{voice_name}")
    def api_delete_voice(voice_name: str):
        clean_name = re.sub(r'[\\/*?:"<>|]', '', voice_name).strip()
        target = VOICES_DIR / f"{clean_name}.wav"
        if target.exists():
            try:
                target.unlink()
                print(f"🗑️ [Voces] Voz eliminada: {target.name}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"No se pudo eliminar: {e}")
        else:
            alt_target = VOICES_DIR / clean_name
            if alt_target.exists():
                alt_target.unlink()
        return api_voices()

    @api_app.get("/api/voices/{filename}/preview")
    def api_voice_preview(filename: str):
        safe_name = Path(filename).name
        p = VOICES_DIR / safe_name
        if not p.exists():
            p_wav = VOICES_DIR / f"{safe_name}.wav"
            if p_wav.exists():
                p = p_wav
            else:
                raise HTTPException(status_code=404, detail="Archivo de voz no encontrado")
        return FileResponse(str(p.resolve()), media_type="audio/wav", filename=p.name)

    @api_app.get("/api/languages")
    def api_languages():
        return {
            "languages": [
                {"code": code, "name": conf["name"], "default_text": conf["text"], "audio_prompt": conf["audio"]}
                for code, conf in LANGUAGE_CONFIG.items()
            ],
            "default_language": "es"
        }

    # -------------------------------------------------------------------------
    # PROYECTO Y PRODUCCIÓN
    # -------------------------------------------------------------------------

    @api_app.get("/api/project")
    def api_get_project(mode: str = "scene"):
        proj = load_project()
        actual_mode = mode or (proj.get("processing_mode") if proj else "scene")
        panel = get_panel_data(actual_mode)
        summary = get_project_summary(actual_mode)
        status_text = get_project_status(actual_mode)
        return {
            "project": proj,
            "panel": panel,
            "summary": summary,
            "status_text": status_text,
            "processing_mode": actual_mode
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
                cfgw_input=payload.cfg_weight,
                voice_name_input=payload.voice_name
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
                cfgw_input=payload.cfg_weight,
                voice_name_input=payload.voice_name
            )
        except Exception as e:
            print(f"❌ Error en generación background: {e}")

    @api_app.post("/api/generate")
    def api_generate(payload: ProjectPayload, bg_tasks: BackgroundTasks):
        if GENERATION_STATE["is_generating"]:
            raise HTTPException(status_code=409, detail="Ya existe una tarea de generación en curso.")
        bg_tasks.add_task(run_bg_generation, payload)
        return {"status": "started", "message": "Producción iniciada en segundo plano"}

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
                "audio_url": f"/outputs/segments/{filename}"
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def run_bg_batch_regenerate(payload: BatchRegeneratePayload):
        try:
            items = [(int(item[0]), int(item[1])) for item in payload.selected_items]
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
            print(f"❌ Error en regeneración por lotes: {e}")

    @api_app.post("/api/regenerate-batch")
    def api_regenerate_batch(payload: BatchRegeneratePayload, bg_tasks: BackgroundTasks):
        if GENERATION_STATE["is_generating"]:
            raise HTTPException(status_code=409, detail="Ya existe una tarea en curso.")
        bg_tasks.add_task(run_bg_batch_regenerate, payload)
        return {"status": "started", "message": f"Regenerando {len(payload.selected_items)} partes"}

    @api_app.post("/api/regenerate-from-here")
    def api_regenerate_from_here(payload: RegenerateFromHerePayload, bg_tasks: BackgroundTasks):
        if GENERATION_STATE["is_generating"]:
            raise HTTPException(status_code=409, detail="Ya existe una tarea en curso.")

        project = load_project()
        if not project:
            raise HTTPException(status_code=400, detail="No hay proyecto guardado.")

        items_to_regen: List[List[int]] = []
        started = False
        target_sec = int(payload.section_number)
        target_part = int(payload.part_number)

        for sec in project.get("sections", []):
            s_num = int(sec.get("number", 0))
            for p in sec.get("parts", []):
                p_num = int(p.get("number", 0))
                if not started:
                    if s_num == target_sec and p_num == target_part:
                        started = True
                if started:
                    items_to_regen.append([s_num, p_num])

        if not items_to_regen:
            raise HTTPException(status_code=400, detail="No se encontraron partes desde el punto indicado.")

        batch_payload = BatchRegeneratePayload(
            selected_items=items_to_regen,
            processing_mode=payload.processing_mode,
            language=payload.language,
            audio_prompt_path=payload.audio_prompt_path,
            exaggeration=payload.exaggeration,
            temperature=payload.temperature,
            cfg_weight=payload.cfg_weight,
            seed=payload.seed
        )
        bg_tasks.add_task(run_bg_batch_regenerate, batch_payload)
        return {"status": "started", "message": f"Regenerando {len(items_to_regen)} partes desde {target_sec}-{target_part}"}

    # -------------------------------------------------------------------------
    # UNIÓN DE AUDIO
    # -------------------------------------------------------------------------

    @api_app.post("/api/join")
    @api_app.post("/api/join-section")
    def api_join_section(payload: JoinPayload):
        try:
            path = join_section_audio(payload.processing_mode, payload.section_number)
            filename = Path(path).name
            return {
                "status": "ok",
                "filename": filename,
                "audio_url": f"/outputs/segments/{filename}"
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
    # SERVIR ARCHIVOS ESTÁTICOS Y FRONTEND
    # -------------------------------------------------------------------------

    @api_app.get("/outputs/segments/{filename}")
    def serve_segment(filename: str):
        safe_name = Path(filename).name
        audio_path = SEGMENTS_DIR / safe_name
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Segmento no encontrado")
        return FileResponse(path=str(audio_path), media_type="audio/wav", filename=safe_name)

    @api_app.get("/assets/{asset_path:path}")
    def serve_asset(asset_path: str):
        safe_path = DIST_DIR / "assets" / asset_path
        if safe_path.exists() and safe_path.is_file():
            media_type = "application/octet-stream"
            if safe_path.suffix == ".js":
                media_type = "application/javascript"
            elif safe_path.suffix == ".css":
                media_type = "text/css"
            return FileResponse(str(safe_path.resolve()), media_type=media_type)
        raise HTTPException(status_code=404, detail="Asset no encontrado")

    # Montar Gradio en /gradio si está instalado
    try:
        import gradio as gr
        demo = create_studio_app()
        if demo is not None:
            gr.mount_gradio_app(api_app, demo, path="/gradio")
            print("🚀 [Gradio] Interfaz fallback montada con éxito en: /gradio")
    except Exception as g_err:
        print(f"ℹ️ Gradio fallback no montado en FastAPI: {g_err}")

    # Servir la ruta raíz (/) - Prioridad a template nativo de Python / HTML
    @api_app.get("/", response_class=FileResponse)
    def serve_root():
        template_file = BASE_DIR / "templates" / "index.html"
        if template_file.exists():
            return FileResponse(str(template_file.resolve()))

        index_file = DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file.resolve()))

        return HTMLResponse("<meta http-equiv='refresh' content='0; url=/gradio'>")

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
# 13. INTERFAZ GRADIO (HERRAMIENTA SECUNDARIA / FALLBACK)
# =============================================================================

CUSTOM_CSS = """
.cm-header { background: #0f141d; border-bottom: 1px solid #1f2737; padding: 20px; border-radius: 12px; text-align: center; }
.cm-title { font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: -0.02em; }
.cm-sub { color: #06b6d4; font-size: 13px; font-weight: 600; margin-top: 4px; text-transform: uppercase; }
"""

def create_studio_app() -> Any:
    """Crea la interfaz de Gradio como herramienta secundaria y de prueba."""
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

    with gr.Blocks(title="Chatterbox Prime — Gradio Fallback", css=CUSTOM_CSS) as demo:
        gr.HTML(
            f"""
            <div class="cm-header">
                <div class="cm-title">CHATTERBOX PRIME</div>
                <div class="cm-sub">AI Narration Studio &bull; {DEVICE.upper()}</div>
            </div>
            """
        )

        with gr.Row():
            with gr.Column(scale=5):
                processing_mode = gr.Radio(
                    choices=[("🎬 Por escenas", "scene"), ("📄 Por párrafos", "paragraph")],
                    value=initial_mode, label="Modo de trabajo"
                )
                text_input = gr.Textbox(value=initial_text, label="Guion", lines=12)
                language_id = gr.Dropdown(choices=get_language_dropdown_choices(), value=initial_lang, label="Idioma")
                voice_dropdown = gr.Dropdown(choices=list(voice_choices.keys()), value=initial_voice_name, label="Voz")
                ref_wav = gr.Audio(sources=["upload", "microphone"], type="filepath", label="Referencia", value=initial_voice_path)

                with gr.Accordion("⚙️ Parámetros de Audio", open=False):
                    exaggeration = gr.Slider(0.0, 1.0, step=0.01, label="Exaggeration", value=initial_exaggeration)
                    cfg_weight = gr.Slider(0.1, 1.0, step=0.05, label="CFG Weight", value=initial_cfg)
                    temp = gr.Slider(0.1, 1.0, step=0.01, label="Temperature", value=initial_temp)
                    seed_num = gr.Number(value=initial_seed, precision=0, label="Seed")

            with gr.Column(scale=6):
                run_btn = gr.Button("🎙️ GENERAR NARRACIÓN", variant="primary")
                latest_audio = gr.Audio(label="Último audio generado", type="filepath")
                status_markdown = gr.Markdown(get_project_status(initial_mode))

        run_btn.click(
            fn=lambda t, m, l, r, ex, tp, sd, cf, v: (
                generate_tts_audio(t, m, l, r, ex, tp, sd, cf, v),
                get_project_status(m)
            ),
            inputs=[text_input, processing_mode, language_id, ref_wav, exaggeration, temp, seed_num, cfg_weight, voice_dropdown],
            outputs=[latest_audio, status_markdown]
        )

    return demo


# =============================================================================
# 14. PUNTO DE ENTRADA Y SERVIDOR HTTP LOCAL
# =============================================================================

def start_server(port: int = 8000, host: str = "127.0.0.1", gradio_only: bool = False, open_browser: bool = True):
    """Inicia el servidor unificado para Chatterbox Prime."""
    if gradio_only:
        print("🖥️ Iniciando en modo Gradio-Only...")
        demo = create_studio_app()
        if demo:
            demo.queue().launch(server_name=host, server_port=port, share=False)
        return

    print("🚀 [Chatterbox Prime] Verificando servidor web FastAPI...")
    try:
        import uvicorn
        fastapi_app = build_fastapi_app()

        def _open():
            time.sleep(1.8)
            try:
                import webbrowser
                target_url = f"http://localhost:{port}"
                print(f"🌐 [Navegador] Abriendo {target_url}...")
                webbrowser.open(target_url)
            except Exception as e:
                print(f"ℹ️ [Navegador] No se pudo abrir automáticamente: {e}")

        if open_browser:
            threading.Thread(target=_open, daemon=True).start()

        print(f"\n=====================================================================")
        print(f"🌟 CHATTERBOX PRIME — AI NARRATION STUDIO")
        print(f"🌐 Servidor disponible en: http://localhost:{port}")
        print(f"🎛️ Vista alternativa Gradio en: http://localhost:{port}/gradio")
        print(f"⚡ Dispositivo activo: {DEVICE.upper()} (CUDA: {CUDA_AVAILABLE})")
        print(f"=====================================================================\n")

        uvicorn.run(fastapi_app, host=host, port=port, log_level="info")

    except ImportError:
        print("⚠️ FastAPI o Uvicorn no están instalados. Iniciando con Gradio...")
        demo = create_studio_app()
        if demo:
            demo.queue().launch(server_name=host, server_port=port, inbrowser=open_browser)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chatterbox Prime — AI Narration Studio")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del servidor HTTP")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host del servidor HTTP")
    parser.add_argument("--gradio-only", action="store_true", help="Iniciar solo Gradio")
    parser.add_argument("--no-browser", action="store_true", help="No abrir automáticamente el navegador")
    args = parser.parse_args()

    start_server(
        port=args.port,
        host=args.host,
        gradio_only=args.gradio_only,
        open_browser=not args.no_browser
    )
