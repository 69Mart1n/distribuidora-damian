param(
    [Parameter(Mandatory = $true)]
    [string]$PayloadDir
)

$ErrorActionPreference = "Stop"

$payloadPath = [IO.Path]::GetFullPath($PayloadDir)
$expectedSuffix = [IO.Path]::Combine("release", "payload")
if (-not $payloadPath.EndsWith($expectedSuffix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "La carpeta a depurar no es release\payload."
}

$pySideDir = Join-Path $payloadPath "runtime\Lib\site-packages\PySide6"
$marker = Join-Path $payloadPath "runtime\distribuidora-runtime.marker"
if (-not (Test-Path -LiteralPath $pySideDir) -or -not (Test-Path -LiteralPath $marker)) {
    throw "El payload no contiene el runtime esperado."
}

function Remove-PayloadDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        [IO.Directory]::Delete("\\?\$([IO.Path]::GetFullPath($Path))", $true)
    }
}

$unusedDirectories = @(
    "doc",
    "glue",
    "include",
    "lib",
    "metatypes",
    "qml",
    "resources",
    "scripts",
    "translations",
    "typesystems",
    "QtAsyncio"
)
foreach ($directory in $unusedDirectories) {
    $path = Join-Path $pySideDir $directory
    Remove-PayloadDirectory -Path $path
}

$keptPluginDirectories = @("iconengines", "imageformats", "platforms", "styles")
$pluginsDir = Join-Path $pySideDir "plugins"
Get-ChildItem -LiteralPath $pluginsDir -Directory | Where-Object {
    $_.Name -notin $keptPluginDirectories
} | ForEach-Object {
    Remove-PayloadDirectory -Path $_.FullName
}

$keptPythonModules = @(
    "QtCore.pyd",
    "QtGui.pyd",
    "QtPdf.pyd",
    "QtPdfWidgets.pyd",
    "QtPrintSupport.pyd",
    "QtWidgets.pyd"
)
Get-ChildItem -LiteralPath $pySideDir -File -Filter "*.pyd" | Where-Object {
    $_.Name -notin $keptPythonModules
} | Remove-Item -Force

$keptQtLibraries = @(
    "Qt6Core.dll",
    "Qt6Gui.dll",
    "Qt6Network.dll",
    "Qt6Pdf.dll",
    "Qt6PdfWidgets.dll",
    "Qt6PrintSupport.dll",
    "Qt6Svg.dll",
    "Qt6Widgets.dll"
)
Get-ChildItem -LiteralPath $pySideDir -File -Filter "Qt6*.dll" | Where-Object {
    $_.Name -notin $keptQtLibraries
} | Remove-Item -Force
