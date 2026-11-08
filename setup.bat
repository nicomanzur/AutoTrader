@echo off
REM setup.bat - Configuracion portable del proyecto (cualquier PC / clon desde GitHub)
REM Uso: setup.bat   (ejecutar desde la raiz del proyecto)

cd /d "%~dp0"

echo TraderDesk V2 - Configuracion portable
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo   Error: Python no encontrado. Instala Python 3.10+ desde https://www.python.org y anade al PATH.
    pause
    exit /b 1
)
echo   Python detectado.
echo.

REM Si existe .venv-v2, comprobar si el Python del venv existe (pyvenv.cfg)
set "VENV_DIR=.venv-v2"
set "CFG=%VENV_DIR%\pyvenv.cfg"
set RECREATE=0

if exist "%VENV_DIR%\Scripts\python.exe" (
    REM Venv existe; en Windows el python.exe del venv suele ser un launcher que lee pyvenv.cfg
    REM Si el venv fue copiado de otra PC, pip/python pueden fallar. Comprobamos ejecutando.
    "%VENV_DIR%\Scripts\python.exe" -c "import sys; sys.exit(0)" >nul 2>&1
    if errorlevel 1 set RECREATE=1
)

if not exist "%VENV_DIR%" set RECREATE=1

if %RECREATE%==1 (
    if exist "%VENV_DIR%" (
        echo   El venv actual no es valido o es de otra PC. Se recreara.
        rmdir /s /q "%VENV_DIR%"
    )
    echo   Creando entorno virtual .venv-v2 con Python local...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo   Error al crear el entorno virtual.
        pause
        exit /b 1
    )
    echo   Entorno virtual creado.
) else (
    echo   Entorno virtual .venv-v2 ya existe.
)

REM Crear .env y accounts.json desde plantillas si no existen (máxima automatización)
if not exist ".env" (
    if exist ".env.example" (
        copy /Y .env.example .env >nul
        echo   .env creado desde .env.example
    )
)
if not exist "accounts.json" (
    if exist "accounts.json.example" (
        copy /Y accounts.json.example accounts.json >nul
        echo   accounts.json creado desde plantilla
    )
)

echo   Instalando dependencias (requirements-gui.txt)...
"%VENV_DIR%\Scripts\python.exe" -m pip install -q -r requirements-gui.txt
if errorlevel 1 (
    echo   Error al instalar dependencias.
    pause
    exit /b 1
)

echo.
echo   Listo. Para ejecutar la aplicacion:
echo     %VENV_DIR%\Scripts\python.exe main.py
echo   O usa:  run.bat
echo.
if not "%1"=="--no-pause" pause
