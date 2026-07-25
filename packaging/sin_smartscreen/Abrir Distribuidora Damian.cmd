@echo off
setlocal

set "APP_DIR=%~dp0"
set "VENV_PYW=%APP_DIR%.venv\Scripts\pythonw.exe"
set "VENV_PY=%APP_DIR%.venv\Scripts\python.exe"

cd /d "%APP_DIR%"

if not exist "%VENV_PYW%" (
  call "%APP_DIR%Instalar dependencias.cmd"
  if errorlevel 1 exit /b 1
)

start "" "%VENV_PYW%" "%APP_DIR%main.py"
exit /b 0
