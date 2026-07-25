@echo off
setlocal

set "APP_DIR=%~dp0"
set "APP_CMD=%APP_DIR%Abrir Distribuidora Damian.cmd"
set "SHORTCUT=%USERPROFILE%\Desktop\Distribuidora Damian.lnk"

if not exist "%APP_CMD%" (
  echo No se encontro "%APP_CMD%".
  echo Ejecuta este archivo desde la carpeta de la aplicacion.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%'); $s.TargetPath='%APP_CMD%'; $s.WorkingDirectory='%APP_DIR%'; $s.Description='Distribuidora Damian'; $s.Save()"

echo Acceso directo creado en el Escritorio.
pause
