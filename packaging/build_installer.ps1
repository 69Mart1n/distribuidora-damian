$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $PSScriptRoot
$buildPython = "C:\Users\56944438\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$innoCompiler = "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
$releaseDir = Join-Path $projectDir "release"
$payloadDir = Join-Path $releaseDir "payload"
$runtimeDir = Join-Path $payloadDir "runtime"
$installedAppDir = Join-Path $payloadDir "app"
$downloadDir = Join-Path $projectDir "tmp\python_runtime"
$runtimeZip = Join-Path $downloadDir "python-3.12.10-embed-amd64.zip"
$runtimeUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"

Set-Location $projectDir

if (-not (Test-Path -LiteralPath $buildPython)) {
    throw "No se encontro el Python de compilacion: $buildPython"
}
if (-not (Test-Path -LiteralPath $innoCompiler)) {
    throw "No se encontro Inno Setup: $innoCompiler"
}

$resolvedProject = [IO.Path]::GetFullPath($projectDir)
$resolvedPayload = [IO.Path]::GetFullPath($payloadDir)
if (-not $resolvedPayload.StartsWith($resolvedProject, [StringComparison]::OrdinalIgnoreCase)) {
    throw "La carpeta temporal de empaquetado quedo fuera del proyecto."
}

if (Test-Path -LiteralPath $payloadDir) {
    Remove-Item -LiteralPath $payloadDir -Recurse -Force
}
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
New-Item -ItemType Directory -Path $installedAppDir -Force | Out-Null
New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $runtimeZip)) {
    Invoke-WebRequest -Uri $runtimeUrl -OutFile $runtimeZip
}
Expand-Archive -LiteralPath $runtimeZip -DestinationPath $runtimeDir -Force

$pythonSignature = Get-AuthenticodeSignature (Join-Path $runtimeDir "pythonw.exe")
if ($pythonSignature.Status -ne "Valid") {
    throw "El runtime oficial de Python no tiene una firma valida."
}

New-Item -ItemType Directory -Path (Join-Path $runtimeDir "Lib\site-packages") -Force | Out-Null
& $buildPython -m pip install `
    --disable-pip-version-check `
    --only-binary=:all: `
    --target (Join-Path $runtimeDir "Lib\site-packages") `
    -r (Join-Path $PSScriptRoot "runtime-requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "No se pudieron preparar las dependencias internas."
}

Copy-Item -LiteralPath (Join-Path $projectDir "app") -Destination $installedAppDir -Recurse
Copy-Item -LiteralPath (Join-Path $projectDir "assets") -Destination $installedAppDir -Recurse
Copy-Item -LiteralPath (Join-Path $projectDir "data") -Destination $installedAppDir -Recurse
Copy-Item -LiteralPath (Join-Path $projectDir "main.py") -Destination $installedAppDir

New-Item -ItemType File -Path (Join-Path $runtimeDir "distribuidora-runtime.marker") -Force | Out-Null
$pthFile = Join-Path $runtimeDir "python312._pth"
@(
    "python312.zip"
    "."
    "Lib\site-packages"
    "..\app"
    "import site"
) | Set-Content -LiteralPath $pthFile -Encoding ascii

& (Join-Path $PSScriptRoot "prune_payload.ps1") -PayloadDir $payloadDir

& (Join-Path $runtimeDir "python.exe") -c "import PySide6, sqlalchemy, reportlab, openpyxl, pdfplumber, pypdf; print('runtime-ok')"
if ($LASTEXITCODE -ne 0) {
    throw "El runtime interno no pudo cargar las dependencias."
}

& $innoCompiler "packaging\installer.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup no pudo generar el instalador."
}

Write-Host "Instalador generado en release\Instalador_Distribuidora_Damian.exe"
