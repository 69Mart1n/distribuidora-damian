# Distribuidora Damián Web

Migración web del sistema de gestión de boletas de Distribuidora Damián.

## Tecnología

- Next.js 16 (App Router) y React 19.
- Supabase: Postgres, autenticación y Row Level Security.
- Vercel para despliegues.
- Modo local con `localStorage` cuando Supabase todavía no está configurado.

## Funciones implementadas

- Panel con ventas, saldos, boletas y alertas de precios.
- Creación de boletas con clientes registrados u ocasionales.
- Pagos en efectivo, transferencia, cuenta corriente y mixtos.
- Estados pagado, parcial y pendiente.
- Historial, vista imprimible, WhatsApp y anulación.
- Clientes con compras y saldo acumulado.
- Catálogo con búsqueda, filtros, edición y revisión.
- Actualizaciones masivas de precios con vista previa.
- Promociones por volumen de M-Line y Vittamax.
- Lista mayorista de julio de 2026: 310 productos únicos, 295 precios confirmados y 15 filas marcadas para revisión.

## Ejecutar

```powershell
pnpm install
pnpm dev
```

Sin variables de entorno se abre el modo local. Para Supabase:

```powershell
Copy-Item .env.example .env.local
```

Completa `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, aplica
`supabase/migrations/202607270001_initial_schema.sql` y después `supabase/seed.sql`.

## Desplegar

Configura en Vercel:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

Luego despliega el directorio `web`.
