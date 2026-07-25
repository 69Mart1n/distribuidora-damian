@echo off
setlocal

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY_CMD=py -3"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY_CMD=python"
  ) else (
    where winget >nul 2>nul
    if %errorlevel%==0 (
      echo No se encontro Python. Instalando Python 3.12...
      winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
      if errorlevel 1 (
        echo No se pudo instalar Python automaticamente.
        echo Instala Python 3.12 o superior desde:
        echo https://www.python.org/downloads/windows/
        pause
        exit /b 1
      )
      set "PY_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
    ) else (
      echo No se encontro Python instalado.
      echo Instala Python 3.12 o superior desde:
      echo https://www.python.org/downloads/windows/
      echo.
      echo Marca la opcion "Add python.exe to PATH" durante la instalacion.
      pause
      exit /b 1
    )
  )
)

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if not %errorlevel%==0 (
  echo Se requiere Python 3.12 o superior.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo No se pudo crear el entorno local.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo No se pudo actualizar pip.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo No se pudieron instalar las dependencias.
  pause
  exit /b 1
)

echo Dependencias instaladas correctamente.
exit /b 0
