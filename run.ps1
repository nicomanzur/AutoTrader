# run.ps1 - Ejecuta la aplicacion (configura el venv si hace falta y lanza main.py)
# Uso: .\run.ps1   o   .\run.ps1 --cli

$ErrorActionPreference = "Stop"
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$venvDir = Join-Path $ScriptDir ".venv-v2"
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"

# Asegurar que el venv existe y es valido (ejecuta setup si hace falta)
$needSetup = $false
if (-not (Test-Path $venvDir)) {
    $needSetup = $true
} elseif (Test-Path (Join-Path $venvDir "pyvenv.cfg")) {
    $cfg = Get-Content (Join-Path $venvDir "pyvenv.cfg") -Raw
    if ($cfg -match "executable\s*=\s*(.+)") {
        $venvPython = $Matches[1].Trim()
        if (-not (Test-Path $venvPython)) { $needSetup = $true }
    }
}

if ($needSetup) {
    Write-Host "Primera ejecucion o venv invalido. Ejecutando setup..." -ForegroundColor Yellow
    & (Join-Path $ScriptDir "setup.ps1")
    if (-not $?) { exit 1 }
}

# Ejecutar con el Python exacto del entorno virtual
$venvPythonExe = Join-Path $venvDir "Scripts\python.exe"
& $venvPythonExe main.py @args
