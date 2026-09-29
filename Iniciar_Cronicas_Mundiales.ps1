<#
.SYNOPSIS
    Iniciador de un solo clic para Crónicas Mundiales — Narration Studio (PowerShell)
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "          CRÓNICAS MUNDIALES — NARRATION STUDIO" -ForegroundColor White
Write-Host "     Estudio Profesional de Producción de Voz para YouTube" -ForegroundColor DarkCyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Detectar entorno de Python con PyTorch
Write-Host "[1/3] Buscando entorno virtual de Python con PyTorch/Chatterbox..." -ForegroundColor Yellow

$Candidates = @(
    "$ScriptDir\.venv\Scripts\python.exe",
    "$ScriptDir\..\.venv\Scripts\python.exe",
    "D:\chatterbox-master\.venv\Scripts\python.exe",
    "C:\chatterbox-master\.venv\Scripts\python.exe",
    "$ScriptDir\venv\Scripts\python.exe",
    "$ScriptDir\..\venv\Scripts\python.exe"
)

$PythonExe = $null

foreach ($Cand in $Candidates) {
    if (Test-Path $Cand) {
        $hasTorch = & $Cand -c "import torch" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $PythonExe = $Cand
            Write-Host "[OK] Entorno con PyTorch detectado: $PythonExe" -ForegroundColor Green
            break
        } elseif (-not $PythonExe) {
            $PythonExe = $Cand
        }
    }
}

if (-not $PythonExe) {
    $SysPython = Get-Command python -ErrorAction SilentlyContinue
    if ($SysPython) {
        $PythonExe = "python"
        Write-Host "[OK] Usando Python del sistema." -ForegroundColor Green
    }
}

if (-not $PythonExe) {
    Write-Host "[ERROR] No se encontró Python en el equipo." -ForegroundColor Red
    Read-Host "Presiona Enter para salir..."
    exit 1
}

# 2. Verificar dependencias
Write-Host "[2/3] Verificando dependencias en $PythonExe..." -ForegroundColor Yellow
& $PythonExe -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Instalando FastAPI y Uvicorn en tu entorno..." -ForegroundColor Cyan
    & $PythonExe -m pip install fastapi "uvicorn[standard]"
}

# 3. Iniciar servidor
Write-Host ""
Write-Host "[3/3] Iniciando Servidor Unificado en http://localhost:8000..." -ForegroundColor Green
Write-Host "Para detener el servidor presiona Ctrl+C." -ForegroundColor DarkGray
Write-Host ""

& $PythonExe "$ScriptDir\multilingual_app.py" --port 8000

Write-Host ""
Write-Host "El servidor se ha detenido." -ForegroundColor Yellow
Read-Host "Presiona Enter para salir..."
