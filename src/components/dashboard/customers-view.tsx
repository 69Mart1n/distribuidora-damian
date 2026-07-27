"use client";

import { FormEvent, useMemo, useState } from "react";
import { FilePlus2, Search, UserPlus, Users } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/field";
import { money, normalize } from "@/lib/format";
import type { Customer, Receipt } from "@/lib/types";

const emptyForm = { name: "", phone: "", address: "", document: "", notes: "" };

export function CustomersView({
  customers,
  receipts,
  onAdd,
  onNewReceipt,
}: {
  customers: Customer[];
  receipts: Receipt[];
  onAdd: (input: Omit<Customer, "id" | "active">) => Promise<Customer>;
  onNewReceipt: () => void;
}) {
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const visible = customers.filter((customer) =>
    normalize(`${customer.name} ${customer.phone} ${customer.document}`).includes(normalize(search)),
  );
  const balances = useMemo(() => {
    return new Map(
      customers.map((customer) => {
        const customerReceipts = receipts.filter(
          (receipt) => receipt.customerId === customer.id && receipt.status === "active",
        );
        return [
          customer.id,
          {
            count: customerReceipts.length,
            total: customerReceipts.reduce((sum, receipt) => sum + receipt.total, 0),
            pending: customerReceipts.reduce((sum, receipt) => sum + receipt.pendingAmount, 0),
          },
        ];
      }),
    );
  }, [customers, receipts]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    await onAdd(form);
    setForm(emptyForm);
    setShowForm(false);
    setSaving(false);
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Clientes</h2>
          <p className="text-sm text-stone-500">Compras acumuladas y saldos pendientes</p>
        </div>
        <Button onClick={() => setShowForm((value) => !value)}>
          <UserPlus className="size-4" /> Agregar cliente
        </Button>
      </div>

      {showForm && (
        <Card className="p-5">
          <form onSubmit={submit}>
            <h3 className="font-bold">Nuevo cliente</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div>
                <Label>Nombre *</Label>
                <Input
                  required
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                />
              </div>
              <div>
                <Label>Teléfono</Label>
                <Input
                  value={form.phone}
                  onChange={(event) => setForm({ ...form, phone: event.target.value })}
                />
              </div>
              <div>
                <Label>Documento / RUT</Label>
                <Input
                  value={form.document}
                  onChange={(event) => setForm({ ...form, document: event.target.value })}
                />
              </div>
              <div>
                <Label>Dirección</Label>
                <Input
                  value={form.address}
                  onChange={(event) => setForm({ ...form, address: event.target.value })}
                />
              </div>
              <div className="md:col-span-2 xl:col-span-4">
                <Label>Notas</Label>
                <Textarea
                  value={form.notes}
                  onChange={(event) => setForm({ ...form, notes: event.target.value })}
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
                Cancelar
              </Button>
              <Button disabled={saving}>{saving ? "Guardando…" : "Guardar cliente"}</Button>
            </div>
          </form>
        </Card>
      )}

      <Card className="p-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 size-4 text-stone-400" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por nombre, teléfono o documento…"
            className="pl-9"
          />
        </div>
      </Card>

      {visible.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visible.map((customer) => {
            const balance = balances.get(customer.id)!;
            return (
              <Card key={customer.id} className="p-5">
                <div className="flex items-start gap-3">
                  <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
                    <Users className="size-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-bold">{customer.name}</h3>
                    <p className="text-xs text-stone-500">{customer.phone || "Sin teléfono"}</p>
                  </div>
                  <Button variant="ghost" size="icon" onClick={onNewReceipt}>
                    <FilePlus2 className="size-4" />
                  </Button>
                </div>
                <div className="mt-5 grid grid-cols-3 gap-2 border-t border-stone-100 pt-4 text-center">
                  <div>
                    <p className="font-mono text-sm font-bold">{balance.count}</p>
                    <p className="text-[10px] uppercase tracking-wide text-stone-500">Boletas</p>
                  </div>
                  <div>
                    <p className="font-mono text-sm font-bold">{money.format(balance.total)}</p>
                    <p className="text-[10px] uppercase tracking-wide text-stone-500">Compras</p>
                  </div>
                  <div>
                    <p className="font-mono text-sm font-bold text-amber-700">
                      {money.format(balance.pending)}
                    </p>
                    <p className="text-[10px] uppercase tracking-wide text-stone-500">Saldo</p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      ) : (
        <Card className="grid min-h-64 place-items-center text-center">
          <div>
            <Users className="mx-auto size-9 text-stone-300" />
            <p className="mt-3 font-semibold">No hay clientes para mostrar</p>
            <p className="text-sm text-stone-500">Agrega el primero para llevar su cuenta.</p>
          </div>
        </Card>
      )}
    </div>
  );
}
