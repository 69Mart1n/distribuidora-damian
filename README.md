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

## Validación

```powershell
python -m ruff check app tests
python -m pytest -q
```

El instalador y el archivo `.exe` no forman parte de esta entrega.
