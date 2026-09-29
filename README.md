# Crónicas Mundiales — Narration Studio

Estudio profesional de producción de narraciones para YouTube.  
Arquitectura unificada con **un solo servidor (FastAPI)** que sirve directamente el **Frontend Moderno**, expone la **API REST**, procesa la inferencia con **Chatterbox Multilingual TTS** y mantiene **Gradio como fallback**.

---

## 🏛️ Arquitectura de Servidor Único

```text
       DOBLE CLIC (Iniciar_Cronicas_Mundiales.bat)
                           ↓
             SERVIDOR FASTAPI (Puerto 8000)
    ┌──────────────────────┬──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
FRONTEND MODERNO        API REST           GRADIO FALLBACK
    http://localhost:8000     /api/...            /gradio
    (servido desde dist/)
                           ↓
                CHATTERBOX MULTILINGUAL
                  (Inferencia PyTorch)
                           ↓
                ARCHIVOS WAV EN DISCO
                (outputs/segments/*.wav)
```

---

## 🖱️ Uso Normal (Un Solo Clic en Windows)

Para utilizar la aplicación de forma habitual **NO necesitas abrir dos terminales ni ejecutar npm**:

1. Haz **doble clic** en:
   ```text
   Iniciar_Cronicas_Mundiales.bat
   ```
   *(o `Iniciar_Cronicas_Mundiales.ps1` en PowerShell).*

2. El script detectará automáticamente tu entorno de Python (ej: `.venv`), iniciará el servidor FastAPI y **abrirá tu navegador automáticamente** en:
   👉 **`http://localhost:8000`**

3. Aparecerá inmediatamente la **interfaz moderna de Crónicas Mundiales** conectada y lista para producir.

4. Para cerrar la aplicación cuando termines, simplemente cierra la ventana de la terminal.

---

## 🎛️ Gradio Fallback

Si en algún momento necesitas acceder a la interfaz de Gradio clásica como herramienta de prueba o emergencia:
- Con el servidor iniciado, entra en: **`http://localhost:8000/gradio`**
- O ejecútalo en modo exclusivo con: `python multilingual_app.py --gradio-only`

---

## 💻 Modo Desarrollo (Solo si vas a modificar la interfaz React)

Si deseas hacer cambios en el código de la interfaz gráfica (`src/`):

1. Inicia el servidor de desarrollo de Vite:
   ```bash
   npm run dev
   ```
   *(Escuchará en `http://localhost:3000` con Hot Module Reload y conectará vía proxy al backend en el puerto 8000).*

2. Para compilar los cambios hacia la versión de producción que usa FastAPI:
   ```bash
   npm run build
   ```
   *Esto actualizará automáticamente la carpeta `dist/` que sirve FastAPI al hacer doble clic.*

---

## 📋 Requisitos e Instalación Inicial (Solo la primera vez)

En tu carpeta de proyecto en Windows (ej. `D:\chatterbox-master\chatterbox-es`):

```bash
# 1. Instalar librerías de Python
pip install -r requirements.txt

# 2. Instalar dependencias de Frontend (si vas a compilar)
npm install
npm run build
```

> 🎙️ **Voz de Brian:** Coloca el archivo `Brian Warm Clonacion Voz.wav` en la carpeta `voices/`. El sistema lo detectará automáticamente como voz predeterminada para tus crónicas.

---

## 📡 Endpoints de la API REST

- `GET /api/status` &bull; Estado del motor, dispositivo (`CPU`/`CUDA`) y modelo.
- `GET /api/progress` &bull; Progreso en tiempo real paso a paso (`is_generating`, `current_step`, `total_steps`).
- `GET /api/voices` &bull; Lista de voces en disco (`voices/`).
- `GET /api/languages` &bull; Idiomas soportados por Chatterbox.
- `GET /api/project` &bull; Estado actual del proyecto y segmentos generados.
- `POST /api/project` &bull; Guardar estructura y parámetros en `outputs/project.json`.
- `POST /api/generate` &bull; Síntesis secuencial en segundo plano (no satura la CPU).
- `POST /api/regenerate` &bull; Regenerar parte individual.
- `POST /api/regenerate-batch` &bull; Regenerar cola de partes seleccionadas con checkbox.
- `POST /api/join` &bull; Ensamblado/unión de audio en master WAV continuo.
- `GET /api/audio/{filename}` &bull; Transmisión directa de audio WAV.
