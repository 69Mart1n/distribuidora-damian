import {
  AlertTriangle,
  ArrowRight,
  CircleDollarSign,
  FileText,
  PackageSearch,
  WalletCards,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { dateTime, money } from "@/lib/format";
import type { AppData } from "@/lib/types";
import type { ViewName } from "./dashboard-app";

export function Overview({
  data,
  stats,
  navigate,
}: {
  data: AppData;
  stats: { sales: number; pending: number; receipts: number; review: number };
  navigate: (view: ViewName) => void;
}) {
  const metrics = [
    { label: "Ventas registradas", value: money.format(stats.sales), icon: CircleDollarSign, tone: "emerald" },
    { label: "Saldo pendiente", value: money.format(stats.pending), icon: WalletCards, tone: "amber" },
    { label: "Boletas", value: String(stats.receipts), icon: FileText, tone: "blue" },
    { label: "Precios a revisar", value: String(stats.review), icon: AlertTriangle, tone: "red" },
  ];
  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-3xl bg-[#163d2a] px-6 py-7 text-white shadow-xl shadow-emerald-950/10 md:px-8">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[.2em] text-emerald-200">
            Resumen comercial
          </p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight md:text-3xl">
            Todo listo para trabajar desde cualquier dispositivo
          </h2>
          <p className="mt-2 text-sm leading-6 text-emerald-50/70">
            Catálogo mayorista actualizado, clientes, ventas y cuentas corrientes en un solo lugar.
          </p>
          <Button
            className="mt-5 bg-[#d9c891] text-emerald-950 hover:bg-[#e4d6a7]"
            onClick={() => navigate("Nueva boleta")}
          >
            Crear una boleta <ArrowRight className="size-4" />
          </Button>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label} className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-semibold text-stone-500">{metric.label}</p>
                <p className="mt-2 font-mono text-2xl font-bold tracking-tight">{metric.value}</p>
              </div>
              <div className="grid size-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
                <metric.icon className="size-5" />
              </div>
            </div>
          </Card>
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.4fr_.6fr]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
            <div>
              <h3 className="font-bold">Actividad reciente</h3>
              <p className="text-xs text-stone-500">Últimas boletas registradas</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate("Historial")}>
              Ver todas
            </Button>
          </div>
          {data.receipts.length ? (
            <div className="divide-y divide-stone-100">
              {data.receipts.slice(0, 6).map((receipt) => (
                <div key={receipt.id} className="flex items-center gap-3 px-5 py-3.5">
                  <div className="grid size-9 place-items-center rounded-xl bg-stone-100 text-stone-600">
                    <FileText className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{receipt.customerName}</p>
                    <p className="text-xs text-stone-500">
                      {receipt.code} · {dateTime.format(new Date(receipt.issuedAt))}
                    </p>
                  </div>
                  <p className="font-mono text-sm font-bold">{money.format(receipt.total)}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid min-h-56 place-items-center px-5 text-center">
              <div>
                <FileText className="mx-auto size-8 text-stone-300" />
                <p className="mt-3 text-sm font-semibold">Todavía no hay boletas</p>
                <p className="text-xs text-stone-500">La primera venta aparecerá aquí.</p>
              </div>
            </div>
          )}
        </Card>
        <Card className="p-5">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-amber-50 text-amber-700">
              <PackageSearch className="size-5" />
            </div>
            <div>
              <h3 className="font-bold">Calidad del catálogo</h3>
              <p className="text-xs text-stone-500">Lista mayorista de julio</p>
            </div>
          </div>
          <div className="mt-6 flex items-end justify-between">
            <div>
              <p className="font-mono text-4xl font-bold">{data.products.length - stats.review}</p>
              <p className="text-xs text-stone-500">productos con precio confirmado</p>
            </div>
            <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-800">
              {stats.review} a revisar
            </span>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-stone-100">
            <div
              className="h-full rounded-full bg-emerald-600"
              style={{
                width: `${((data.products.length - stats.review) / data.products.length) * 100}%`,
              }}
            />
          </div>
          <Button
            variant="outline"
            className="mt-6 w-full"
            onClick={() => navigate("Productos")}
          >
            Revisar catálogo
          </Button>
        </Card>
      </section>
    </div>
  );
}
