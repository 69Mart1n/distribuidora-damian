@echo off
setlocal

set "APP_DIR=%~dp0"
set "APP_EXE=%APP_DIR%Distribuidora Damian.exe"
set "SHORTCUT=%USERPROFILE%\Desktop\Distribuidora Damian.lnk"

if not exist "%APP_EXE%" (
  echo No se encontro "%APP_EXE%".
  echo Ejecuta este archivo desde la carpeta donde esta Distribuidora Damian.exe.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%SHORTCUT%'); $s.TargetPath='%APP_EXE%'; $s.WorkingDirectory='%APP_DIR%'; $s.Description='Distribuidora Damian'; $s.IconLocation='%APP_EXE%,0'; $s.Save()"

echo Acceso directo creado en el Escritorio.
pause
