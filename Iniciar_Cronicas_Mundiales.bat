@echo off
rem =====================================================================
rem           CRONICAS MUNDIALES - NARRATION STUDIO
rem            (100%% Python Nativo - Sin requerir Node ni npm)
rem =====================================================================

cd /d "%~dp0"

echo =====================================================================
echo           CRONICAS MUNDIALES - NARRATION STUDIO
echo      Estudio Profesional de Produccion de Voz para YouTube
echo =====================================================================
echo.

echo [1/2] Detectando entorno virtual de Python con PyTorch...

set PYTHON_EXE=

rem 1. Probar en subcarpeta local .venv
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

rem 2. Probar en carpeta superior ..\.venv
if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

rem 3. Probar en D:\chatterbox-master\.venv
if exist "D:\chatterbox-master\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=D:\chatterbox-master\.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

rem 4. Probar en C:\chatterbox-master\.venv
if exist "C:\chatterbox-master\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=C:\chatterbox-master\.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

rem 5. Probar python en PATH
python --version >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

rem 6. Probar py launcher
py -3 --version >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_EXE=py -3"
    goto :PYTHON_FOUND
)

echo.
echo =====================================================================
echo [AVISO] No se detecto automaticamente la ruta a tu entorno de Python.
echo.
echo Por favor escribe o arrastra aqui el archivo python.exe de tu entorno
echo (por ejemplo: D:\chatterbox-master\.venv\Scripts\python.exe)
echo =====================================================================
set /p CUSTOM_PY="Ruta a python.exe: "
if defined CUSTOM_PY (
    set "PYTHON_EXE=%CUSTOM_PY%"
    goto :PYTHON_FOUND
)

pause
exit /b 1

:PYTHON_FOUND
echo [OK] Python detectado: %PYTHON_EXE%
echo.

echo [2/2] Iniciando Servidor de Cronicas Mundiales en http://localhost:8000 ...
echo =====================================================================
echo 🌐 Abre tu navegador en: http://localhost:8000
echo 🎛️ Vista alternativa Gradio en: http://localhost:8000/gradio
echo Presiona Ctrl+C en esta ventana para detener el servidor.
echo =====================================================================
echo.

"%PYTHON_EXE%" "%~dp0multilingual_app.py" --port 8000

echo.
echo =====================================================================
echo El servidor se ha detenido.
echo Presiona cualquier tecla para cerrar esta ventana...
echo =====================================================================
pause
