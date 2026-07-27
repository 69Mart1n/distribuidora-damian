"use client";

import { useState } from "react";
import { createPortal } from "react-dom";
import Image from "next/image";
import {
  Eye,
  FileText,
  MessageCircle,
  Printer,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/field";
import { dateTime, money, normalize } from "@/lib/format";
import type { Receipt } from "@/lib/types";

const statusLabels = {
  paid: "Pagado",
  partial: "Parcial",
  pending: "Pendiente",
};

export function ReceiptHistory({
  receipts,
  onCancel,
  allowCancel,
}: {
  receipts: Receipt[];
  onCancel: (id: string) => Promise<void>;
  allowCancel: boolean;
}) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [showDeleted, setShowDeleted] = useState(false);
  const [selected, setSelected] = useState<Receipt | null>(null);
  const visible = receipts.filter(
    (receipt) =>
      (showDeleted || receipt.status === "active") &&
      normalize(`${receipt.code} ${receipt.customerName} ${receipt.customerPhone}`).includes(
        normalize(search),
      ) &&
      (status === "all" || receipt.paymentStatus === status),
  );

  const remove = async (receipt: Receipt) => {
    if (
      !window.confirm(
        `¿Eliminar ${receipt.code} del historial activo?\n\nEl registro quedará conservado para auditoría.`,
      )
    )
      return;
    await onCancel(receipt.id);
    setSelected((current) =>
      current?.id === receipt.id ? { ...current, status: "cancelled" } : current,
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Historial de boletas</h2>
          <p className="text-sm text-stone-500">Consulta, imprime y administra ventas anteriores</p>
        </div>
        <label className="flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs font-semibold text-stone-700">
          <input
            type="checkbox"
            checked={showDeleted}
            onChange={(event) => setShowDeleted(event.target.checked)}
            className="accent-emerald-700"
          />
          Mostrar boletas eliminadas
        </label>
      </div>

      <Card className="p-4">
        <div className="grid gap-3 md:grid-cols-[1fr_220px]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 size-4 text-stone-400" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por número, cliente o teléfono…"
              className="pl-9"
            />
          </div>
          <Select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="all">Todos los estados</option>
            <option value="paid">Pagadas</option>
            <option value="partial">Parciales</option>
            <option value="pending">Pendientes</option>
          </Select>
        </div>
      </Card>

      <Card className="overflow-hidden">
        {visible.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[780px] text-left text-sm">
              <thead className="border-b border-stone-200 bg-stone-50/80 text-xs uppercase tracking-wide text-stone-500">
                <tr>
                  <th className="px-5 py-3">Boleta</th>
                  <th className="px-4 py-3">Cliente</th>
                  <th className="px-4 py-3">Fecha</th>
                  <th className="px-4 py-3">Pago</th>
                  <th className="px-4 py-3 text-right">Total</th>
                  <th className="px-5 py-3 text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {visible.map((receipt) => (
                  <tr
                    key={receipt.id}
                    className={
                      receipt.status === "cancelled"
                        ? "bg-stone-50/70 text-stone-400"
                        : "hover:bg-stone-50/70"
                    }
                  >
                    <td className="px-5 py-3.5">
                      <span className="font-mono text-sm font-bold">{receipt.code}</span>
                      {receipt.status === "cancelled" && (
                        <span className="ml-2 rounded-full bg-red-50 px-2 py-1 text-[10px] font-semibold text-red-700">
                          Eliminada · registro conservado
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      <p className="font-semibold">{receipt.customerName}</p>
                      <p className="text-xs text-stone-500">{receipt.items.length} productos</p>
                    </td>
                    <td className="px-4 py-3.5 text-stone-600">
                      {dateTime.format(new Date(receipt.issuedAt))}
                    </td>
                    <td className="px-4 py-3.5">
                      <span
                        className={
                          receipt.paymentStatus === "paid"
                            ? "rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700"
                            : "rounded-full bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800"
                        }
                      >
                        {statusLabels[receipt.paymentStatus]}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono font-bold">
                      {money.format(receipt.total)}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setSelected(receipt)}
                        aria-label={`Ver ${receipt.code}`}
                      >
                        <Eye className="size-4" />
                      </Button>
                      {receipt.status === "active" && allowCancel && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-red-600 hover:bg-red-50 hover:text-red-700"
                          onClick={() => void remove(receipt)}
                          aria-label={`Eliminar ${receipt.code}`}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid min-h-64 place-items-center text-center">
            <div>
              <FileText className="mx-auto size-9 text-stone-300" />
              <p className="mt-3 font-semibold">No hay boletas para mostrar</p>
            </div>
          </div>
        )}
      </Card>

      {selected && (
        <ReceiptDetail
          receipt={selected}
          onClose={() => setSelected(null)}
          onRemove={() => remove(selected)}
          allowRemove={allowCancel}
        />
      )}
    </div>
  );
}

function ReceiptDetail({
  receipt,
  onClose,
  onRemove,
  allowRemove,
}: {
  receipt: Receipt;
  onClose: () => void;
  onRemove: () => Promise<void>;
  allowRemove: boolean;
}) {
  const share = () => {
    const lines = [
      `*Distribuidora Damián · ${receipt.code}*`,
      `Cliente: ${receipt.customerName}`,
      ...receipt.items.map(
        (item) => `${item.quantity} × ${item.name} — ${money.format(item.quantity * item.unitPrice)}`,
      ),
      `*Total: ${money.format(receipt.total)}*`,
      receipt.pendingAmount > 0 ? `Saldo: ${money.format(receipt.pendingAmount)}` : "Pago al día",
    ];
    window.open(`https://wa.me/?text=${encodeURIComponent(lines.join("\n"))}`, "_blank");
  };

  return (
    <>
      <div className="fixed inset-0 z-50 overflow-y-auto bg-stone-950/40 p-4 backdrop-blur-sm">
        <div className="mx-auto my-6 max-w-3xl overflow-hidden rounded-2xl bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b border-stone-100 p-4">
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => window.print()}>
                <Printer className="size-4" /> Imprimir
              </Button>
              <Button variant="outline" size="sm" onClick={share}>
                <MessageCircle className="size-4" /> WhatsApp
              </Button>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} aria-label="Cerrar">
              <X className="size-4" />
            </Button>
          </div>
          <ReceiptDocument receipt={receipt} />
          {receipt.status === "active" && allowRemove && (
            <div className="border-t border-stone-100 p-4 text-right">
              <Button
                variant="ghost"
                className="text-red-600 hover:bg-red-50 hover:text-red-700"
                onClick={() => void onRemove()}
              >
                <Trash2 className="size-4" /> Eliminar boleta (conservar registro)
              </Button>
            </div>
          )}
        </div>
      </div>
      {typeof document !== "undefined" &&
        createPortal(
          <div className="print-receipt-root">
            <ReceiptDocument receipt={receipt} />
          </div>,
          document.body,
        )}
    </>
  );
}

function ReceiptDocument({ receipt }: { receipt: Receipt }) {
  return (
    <article className="receipt-document bg-white p-7 text-stone-900 md:p-10">
      <header className="rounded-2xl bg-[#f6f1e4] p-5">
        <div className="flex items-center justify-between gap-5">
          <Image
            src="/logo.png"
            alt="Distribuidora Damián"
            width={210}
            height={140}
            className="h-auto max-h-20 w-auto object-contain"
          />
          <div className="text-right">
            <p className="text-[10px] font-bold uppercase tracking-[.16em] text-emerald-800">
              Boleta
            </p>
            <p className="font-mono text-sm font-bold text-emerald-950">{receipt.code}</p>
            <p className="mt-1 text-xs font-medium text-stone-900">
              {dateTime.format(new Date(receipt.issuedAt))}
            </p>
          </div>
        </div>
        <div className="mt-4 h-1 rounded-full bg-gradient-to-r from-emerald-800 via-emerald-600 to-amber-500" />
      </header>

      <div className="my-4 grid overflow-hidden rounded-lg border border-stone-400 sm:grid-cols-2">
        <div className="min-h-20 border-b border-stone-400 p-3 sm:border-b-0 sm:border-r">
          <p className="text-[10px] font-bold uppercase tracking-wide text-stone-400">Cliente</p>
          <p className="mt-1 font-bold">{receipt.customerName}</p>
          <p className="text-sm text-stone-500">{receipt.customerPhone}</p>
          {receipt.customerAddress && (
            <p className="mt-0.5 text-sm text-stone-600">{receipt.customerAddress}</p>
          )}
        </div>
        <div className="min-h-20 p-3 sm:text-right">
          <p className="text-[10px] font-bold uppercase tracking-wide text-stone-400">Estado</p>
          <p className="mt-1 font-bold">{statusLabels[receipt.paymentStatus]}</p>
          {receipt.pendingAmount > 0 && (
            <p className="text-sm font-medium text-stone-900">
              Saldo {money.format(receipt.pendingAmount)}
            </p>
          )}
        </div>
      </div>

      <table className="my-4 w-full border-collapse border border-stone-400 text-[13px]">
        <thead className="bg-stone-100 text-left text-[10px] uppercase tracking-wide text-stone-600">
          <tr>
            <th className="border border-stone-400 px-2.5 py-1.5">Producto</th>
            <th className="w-16 border border-stone-400 px-2.5 py-1.5 text-center">Cant.</th>
            <th className="w-24 border border-stone-400 px-2.5 py-1.5 text-right">Precio</th>
            <th className="w-24 border border-stone-400 px-2.5 py-1.5 text-right">Importe</th>
          </tr>
        </thead>
        <tbody>
          {receipt.items.map((item) => (
            <tr key={`${receipt.id}-${item.productId}`}>
              <td className="border border-stone-400 px-2.5 py-2">
                <p className="font-semibold">{item.name}</p>
                <p className="text-xs text-stone-500">{item.presentation}</p>
              </td>
              <td className="border border-stone-400 px-2.5 py-2 text-center font-mono">
                {item.quantity}
              </td>
              <td className="border border-stone-400 px-2.5 py-2 text-right font-mono">
                {money.format(item.unitPrice)}
              </td>
              <td className="border border-stone-400 px-2.5 py-2 text-right font-mono font-bold">
                {money.format(item.quantity * item.unitPrice)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {receipt.notes && (
        <div className="mb-4 overflow-hidden rounded-lg border border-stone-400">
          <p className="border-b border-stone-400 bg-stone-100 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-stone-600">
            Observaciones
          </p>
          <p className="min-h-10 whitespace-pre-wrap px-2.5 py-2 text-[13px] text-stone-700">
            {receipt.notes}
          </p>
        </div>
      )}

      <table className="ml-auto w-full max-w-xs border-collapse border border-stone-400 text-[13px]">
        <tbody>
          <tr>
            <th className="border border-stone-400 bg-stone-50 px-2.5 py-1.5 text-left font-medium text-stone-600">
              Subtotal
            </th>
            <td className="border border-stone-400 px-2.5 py-1.5 text-right font-mono">
              {money.format(receipt.subtotal)}
            </td>
          </tr>
        {receipt.discountPercentage > 0 && (
          <tr className="text-emerald-800">
            <th className="border border-stone-400 bg-stone-50 px-2.5 py-1.5 text-left font-medium">
              Descuento ({receipt.discountPercentage}%)
            </th>
            <td className="border border-stone-400 px-2.5 py-1.5 text-right font-mono">
              -{money.format(receipt.subtotal - receipt.total)}
            </td>
          </tr>
        )}
          <tr className="text-base font-bold">
            <th className="border border-stone-500 bg-stone-100 px-2.5 py-2 text-left">Total</th>
            <td className="border border-stone-500 px-2.5 py-2 text-right font-mono">
              {money.format(receipt.total)}
            </td>
          </tr>
        </tbody>
      </table>

      {receipt.status === "cancelled" && (
        <div className="mt-6 rounded-xl border-2 border-red-600 p-3 text-center font-bold uppercase text-red-600">
          Boleta eliminada · registro conservado
        </div>
      )}
      <footer className="mt-8 border-t border-stone-200 pt-3 text-center text-[10px] text-stone-400">
        Distribuidora Damián · Gracias por su compra
      </footer>
    </article>
  );
}
