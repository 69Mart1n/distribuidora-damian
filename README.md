# Distribuidora Damián

Sistema comercial de escritorio para Windows. Funciona de forma local con SQLite y conserva los datos en `data/distribuidora.db`.

## Funciones

- Boletas numeradas con cliente registrado u ocasional, cantidades y precios enteros.
- Pagos en efectivo, transferencia, cuenta o mixtos; estados pagado, parcial y pendiente.
- Vista previa dentro del sistema, impresión, copia PDF y preparación para WhatsApp.
- Edición auditable de boletas, revisiones, cancelación, duplicado y pagos posteriores.
- Clientes con compras acumuladas y saldo pendiente.
- Catálogo con 314 productos, filtros, edición de precio, duplicado, desactivación e historial.
- Cambios masivos de precios con vista previa, respaldo y deshacer lote.
- Importación revisable de PDF, XLSX y CSV.
- Exportación de precios a PDF, Excel y CSV.
- Respaldos automáticos y manuales, verificación, exportación y restauración.
- Configuración de datos comerciales, logo, numeración, moneda y rutas.

## Tecnología

- Python 3.12 y PySide6.
- SQLite y SQLAlchemy 2.
- ReportLab para PDF.
- openpyxl, pdfplumber y pypdf para intercambio de archivos.
- pytest y ruff para validación.

## Ejecutar

Desde esta carpeta:

```powershell
python main.py
```

Con el entorno incluido en Codex:

```powershell
& 'C:\Users\56944438\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' main.py
```

La aplicación crea un respaldo diario al iniciar. Las importaciones, cambios masivos y restauraciones también generan una copia previa.

## Instalar en Windows

Descarga `Instalador_Distribuidora_Damian.msi` desde la sección Releases del repositorio y ábrelo. El instalador incluye Python, Qt y todas las dependencias, crea accesos directos en el Escritorio y el menú Inicio, y no necesita permisos de administrador.

En la versión instalada, la base y los archivos del negocio se guardan en:

```text
%LOCALAPPDATA%\Distribuidora Damian
```

Los datos no están dentro de la carpeta del programa, por lo que se conservan al actualizar o reinstalar.

## Construir instaladores

```powershell
.\packaging\build_installer.ps1
python .\packaging\build_msi.py
```

El primer comando prepara el runtime oficial de Python embebido y genera el instalador EXE. El segundo genera el MSI compatible con Windows Installer.

## Validación

```powershell
python -m ruff check app tests
python -m pytest -q
```
