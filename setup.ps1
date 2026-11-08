# setup.ps1 - Configuración portable del proyecto (cualquier PC / clon desde GitHub)
# Uso: .\setup.ps1   (ejecutar desde la raíz del proyecto)

# Permitir ejecución de scripts solo en este proceso (evita error de ExecutionPolicy)
$ErrorActionPreference = "Stop"
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Ir a la carpeta del script (raíz del proyecto)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "TraderDesk V2 - Configuracion portable" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar Python
try {
    $pythonVersion = python --version 2>&1
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    Write-Host "  Python: $pythonVersion" -ForegroundColor Green
    Write-Host "  Ruta:  $pythonPath" -ForegroundColor Gray
} catch {
    Write-Host "  Error: Python no encontrado. Instala Python 3.10+ desde https://www.python.org y anade al PATH." -ForegroundColor Red
    exit 1
}

# 2. Comprobar si el venv existe y es válido (apunta a un Python que existe)
$venvDir = Join-Path $ScriptDir ".venv-v2"
$pyvenvCfg = Join-Path $venvDir "pyvenv.cfg"
$venvNeedsRecreate = $false

if (Test-Path $venvDir) {
    if (Test-Path $pyvenvCfg) {
        $cfg = Get-Content $pyvenvCfg -Raw
        if ($cfg -match "executable\s*=\s*(.+)") {
            $venvPython = $Matches[1].Trim()
            if (-not (Test-Path $venvPython)) {
                Write-Host "  El venv actual apunta a otro equipo/usuario. Se recreara con Python local." -ForegroundColor Yellow
                $venvNeedsRecreate = $true
            }
        }
    } else {
        $venvNeedsRecreate = $true
    }
}

if ($venvNeedsRecreate -and (Test-Path $venvDir)) {
    Write-Host "  Eliminando venv anterior..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $venvDir
}

# 3. Crear venv si no existe
if (-not (Test-Path $venvDir)) {
    Write-Host "  Creando entorno virtual .venv-v2 con Python local..." -ForegroundColor Cyan
    python -m venv $venvDir
    if (-not $?) { exit 1 }
    Write-Host "  Entorno virtual creado." -ForegroundColor Green
} else {
    Write-Host "  Entorno virtual .venv-v2 ya existe y es valido." -ForegroundColor Green
}

# 4. Instalar dependencias con el Python del entorno virtual
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
$venvPythonExe = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $activateScript)) {
    Write-Host "  Error: No se encontro Activate.ps1 en .venv-v2" -ForegroundColor Red
    exit 1
}

# Crear .env y accounts.json desde plantillas si no existen (máxima automatización)
if (-not (Test-Path (Join-Path $ScriptDir ".env"))) {
    $envExample = Join-Path $ScriptDir ".env.example"
    if (Test-Path $envExample) {
        Copy-Item $envExample (Join-Path $ScriptDir ".env") -Force
        Write-Host "  .env creado desde .env.example" -ForegroundColor Green
    }
}
if (-not (Test-Path (Join-Path $ScriptDir "accounts.json"))) {
    $accountsExample = Join-Path $ScriptDir "accounts.json.example"
    if (Test-Path $accountsExample) {
        Copy-Item $accountsExample (Join-Path $ScriptDir "accounts.json") -Force
        Write-Host "  accounts.json creado desde plantilla" -ForegroundColor Green
    }
}

Write-Host "  Instalando dependencias (requirements-gui.txt)..." -ForegroundColor Cyan
& $venvPythonExe -m pip install --quiet -r requirements-gui.txt
if (-not $?) { exit 1 }

Write-Host ""
Write-Host "  Listo. Para ejecutar la aplicacion:" -ForegroundColor Green
Write-Host "    .\.venv-v2\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "    python main.py" -ForegroundColor White
Write-Host "  O usa:  .\run.ps1" -ForegroundColor White
Write-Host ""
