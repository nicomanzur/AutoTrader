@echo off
REM run.bat - Ejecuta la aplicacion (configura el venv si hace falta y lanza main.py)
REM Uso: run.bat   o   run.bat --cli

cd /d "%~dp0"

set "VENV_DIR=.venv-v2"
set "PY_EXE=%VENV_DIR%\Scripts\python.exe"

REM Si no hay venv o python del venv falla, ejecutar setup
set NEED_SETUP=0
if not exist "%PY_EXE%" set NEED_SETUP=1
if exist "%PY_EXE%" (
    "%PY_EXE%" -c "import sys; sys.exit(0)" >nul 2>&1
    if errorlevel 1 set NEED_SETUP=1
)

if %NEED_SETUP%==1 (
    echo Primera ejecucion o venv invalido. Ejecutando setup...
    call setup.bat --no-pause
    if errorlevel 1 exit /b 1
)

"%PY_EXE%" main.py %*
