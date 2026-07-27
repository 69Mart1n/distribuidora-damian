"use client";

import { useMemo, useState } from "react";
import { Minus, PackagePlus, Plus, Search, ShoppingBasket, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Label, Select, Textarea } from "@/components/ui/field";
import { money, normalize } from "@/lib/format";
import type { Customer, Product, Promotion, ReceiptItem } from "@/lib/types";
import type { NewReceipt } from "@/hooks/use-app-store";

export function ReceiptBuilder({
  products,
  customers,
  promotions,
  onSave,
  onSaved,
}: {
  products: Product[];
  customers: Customer[];
  promotions: Promotion[];
  onSave: (input: NewReceipt) => Promise<unknown>;
  onSaved: () => void;
}) {
  const [search, setSearch] = useState("");
  const [cart, setCart] = useState<ReceiptItem[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [occasionalName, setOccasionalName] = useState("");
  const [occasionalPhone, setOccasionalPhone] = useState("");
  const [occasionalAddress, setOccasionalAddress] = useState("");
  const [discount, setDiscount] = useState(0);
  const [paymentMethod, setPaymentMethod] = useState<NewReceipt["paymentMethod"]>("cash");
  const [paymentStatus, setPaymentStatus] = useState<"paid" | "partial" | "pending">("paid");
  const [partialPaid, setPartialPaid] = useState(0);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const customer = customers.find((item) => item.id === customerId);
  const visibleProducts = useMemo(() => {
    const query = normalize(search);
    return products
      .filter(
        (product) =>
          product.active &&
          product.wholesalePrice !== null &&
          (!query ||
            normalize(
              `${product.name} ${product.presentation} ${product.supplier} ${product.code}`,
            ).includes(query)),
      )
      .sort((a, b) => {
        const byName = a.name.localeCompare(b.name, "es", { sensitivity: "base" });
        return byName || a.presentation.localeCompare(b.presentation, "es", { numeric: true });
      });
  }, [products, search]);

  const subtotal = cart.reduce((sum, item) => sum + item.quantity * item.unitPrice, 0);
  const total = Math.round(subtotal * (1 - discount / 100));
  const amountPaid =
    paymentStatus === "paid" ? total : paymentStatus === "pending" ? 0 : partialPaid;

  const promoHints = useMemo(() => {
    const totals = new Map<string, number>();
    for (const item of cart) {
      const match = item.presentation.match(/(\d+(?:[.,]\d+)?)\s*kg/i);
      const kilos = match ? Number(match[1].replace(",", ".")) * item.quantity : 0;
      if (!kilos) continue;
      const brand = /m-line/i.test(item.name)
        ? "M-Line"
        : /vittamax/i.test(item.name)
          ? "Vittamax"
          : "";
      if (brand) totals.set(brand, (totals.get(brand) || 0) + kilos);
    }
    return promotions
      .map((promo) => {
        const brand = promo.name.replace(/^Promo\s+/i, "");
        const current = totals.get(brand) || 0;
        return { ...promo, current, reached: current >= promo.minimumKg };
      })
      .filter((promo) => promo.current > 0);
  }, [cart, promotions]);

  function addProduct(product: Product) {
    setCart((current) => {
      const existing = current.find((item) => item.productId === product.id);
      if (existing) {
        return current.map((item) =>
          item.productId === product.id ? { ...item, quantity: item.quantity + 1 } : item,
        );
      }
      return [
        ...current,
        {
          productId: product.id,
          code: product.code,
          name: product.name,
          presentation: product.presentation,
          quantity: 1,
          unitPrice: product.wholesalePrice!,
        },
      ];
    });
  }

  function updateQuantity(productId: string, quantity: number) {
    if (quantity <= 0) {
      setCart((current) => current.filter((item) => item.productId !== productId));
      return;
    }
    setCart((current) =>
      current.map((item) => (item.productId === productId ? { ...item, quantity } : item)),
    );
  }

  function updateReceiptItem(
    productId: string,
    changes: Partial<Pick<ReceiptItem, "presentation" | "unitPrice">>,
  ) {
    setCart((current) =>
      current.map((item) => (item.productId === productId ? { ...item, ...changes } : item)),
    );
  }

  async function save() {
    if (!cart.length) return;
    setSaving(true);
    try {
      await onSave({
        customerId: customer?.id,
        customerName: customer?.name || occasionalName.trim() || "Cliente ocasional",
        customerPhone: customer?.phone || occasionalPhone.trim(),
        customerAddress: customer?.address || occasionalAddress.trim(),
        items: cart,
        discountPercentage: discount,
        paymentMethod,
        amountPaid,
        notes,
      });
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Nueva boleta</h2>
        <p className="text-sm text-stone-500">
          Completa los datos y selecciona los productos en la misma pantalla
        </p>
      </div>

      <Card className="mx-auto grid w-full max-w-5xl overflow-hidden lg:grid-cols-[.9fr_1.1fr]">
        <section className="space-y-3 bg-stone-50/55 p-4 lg:border-r lg:border-stone-100">
          <div className="flex items-center gap-3 border-b border-stone-200 pb-3">
            <div className="grid size-9 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
              <ShoppingBasket className="size-4" />
            </div>
            <div>
              <h3 className="font-bold">Datos de la boleta</h3>
              <p className="text-xs text-stone-500">Cliente, pago y totales</p>
            </div>
          </div>

          <div>
            <Label>Cliente registrado</Label>
            <Select value={customerId} onChange={(event) => setCustomerId(event.target.value)}>
              <option value="">Cliente ocasional</option>
              {customers.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </Select>
          </div>

          {!customerId && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Nombre</Label>
                <Input
                  value={occasionalName}
                  onChange={(event) => setOccasionalName(event.target.value)}
                  placeholder="Cliente ocasional"
                />
              </div>
              <div>
                <Label>Teléfono</Label>
                <Input
                  value={occasionalPhone}
                  onChange={(event) => setOccasionalPhone(event.target.value)}
                />
              </div>
              <div className="col-span-2">
                <Label>Dirección</Label>
                <Input
                  value={occasionalAddress}
                  onChange={(event) => setOccasionalAddress(event.target.value)}
                  placeholder="Dirección de entrega"
                />
              </div>
            </div>
          )}
          {customerId && (
            <div>
              <Label>Dirección</Label>
              <Input
                value={customer?.address || ""}
                readOnly
                placeholder="El cliente no tiene una dirección cargada"
                className="bg-white text-stone-600"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Descuento total (%)</Label>
              <Input
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={discount}
                onChange={(event) => setDiscount(Number(event.target.value))}
              />
            </div>
            <div>
              <Label>Forma de pago</Label>
              <Select
                value={paymentMethod}
                onChange={(event) =>
                  setPaymentMethod(event.target.value as NewReceipt["paymentMethod"])
                }
              >
                <option value="cash">Efectivo</option>
                <option value="transfer">Transferencia</option>
                <option value="account">Cuenta corriente</option>
                <option value="mixed">Mixto</option>
              </Select>
            </div>
            <div>
              <Label>Estado del pago</Label>
              <Select
                value={paymentStatus}
                onChange={(event) =>
                  setPaymentStatus(event.target.value as typeof paymentStatus)
                }
              >
                <option value="paid">Pagado</option>
                <option value="partial">Pago parcial</option>
                <option value="pending">Pendiente</option>
              </Select>
            </div>
            {paymentStatus === "partial" && (
              <div>
                <Label>Importe entregado</Label>
                <Input
                  type="number"
                  min="0"
                  max={total}
                  value={partialPaid}
                  onChange={(event) => setPartialPaid(Number(event.target.value))}
                />
              </div>
            )}
          </div>

          <div>
            <Label>Notas</Label>
            <Textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Observaciones de entrega o pago…"
              className="min-h-16"
            />
          </div>

          {promoHints.length > 0 && (
            <div className="space-y-1 rounded-xl border border-amber-200 bg-amber-50 p-2.5 text-[11px] text-amber-900">
              {promoHints.map((promo) => (
                <div key={`${promo.name}-${promo.minimumKg}`} className="flex justify-between gap-2">
                  <span>
                    {promo.name}: {promo.current.toFixed(1)} / {promo.minimumKg} kg
                  </span>
                  <strong>
                    {promo.reached ? `${promo.discountPercentage}% disponible` : "en progreso"}
                  </strong>
                </div>
              ))}
            </div>
          )}

          <div className="space-y-1.5 border-t border-stone-200 pt-3 text-sm">
            <div className="flex justify-between text-stone-500">
              <span>Subtotal</span>
              <span className="font-mono">{money.format(subtotal)}</span>
            </div>
            {discount > 0 && (
              <div className="flex justify-between text-emerald-700">
                <span>Descuento ({discount}%)</span>
                <span className="font-mono">-{money.format(subtotal - total)}</span>
              </div>
            )}
            <div className="flex items-end justify-between">
              <span className="font-bold">Total</span>
              <span className="font-mono text-xl font-bold">{money.format(total)}</span>
            </div>
            {amountPaid < total && (
              <div className="flex justify-between font-semibold text-amber-700">
                <span>Saldo pendiente</span>
                <span className="font-mono">{money.format(total - amountPaid)}</span>
              </div>
            )}
          </div>

          <Button className="w-full" disabled={!cart.length || saving} onClick={save}>
            {saving ? "Guardando boleta…" : "Guardar boleta"}
          </Button>
        </section>

        <section className="flex min-h-0 flex-col p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="font-bold">Seleccionar productos</h3>
              <p className="text-xs text-stone-500">Busca y toca para agregar</p>
            </div>
            <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
              {cart.length} elegidos
            </span>
          </div>

          <div className="relative mt-3">
            <Search className="pointer-events-none absolute left-3 top-3 size-4 text-stone-400" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar producto, proveedor o código…"
              className="pl-9"
              autoFocus
            />
          </div>

          <div className="mt-3 grid max-h-80 grid-cols-1 gap-1.5 overflow-y-auto pr-1">
            {visibleProducts.map((product) => (
              <button
                key={product.id}
                type="button"
                className="group grid min-h-16 grid-cols-[minmax(0,1fr)_72px_82px_18px] items-center gap-3 rounded-xl border border-stone-200 bg-white px-4 py-2.5 text-left transition hover:border-emerald-400 hover:bg-emerald-50/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
                onClick={() => addProduct(product)}
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-stone-950">{product.name}</p>
                  <p className="truncate text-[10px] font-medium text-stone-400">
                    {product.supplier} · {product.category} · {product.code}
                  </p>
                </div>
                <p className="text-center text-sm font-bold text-stone-950">
                  {product.presentation}
                </p>
                <p className="text-right font-mono text-sm font-bold text-emerald-800">
                  {money.format(product.wholesalePrice!)}
                </p>
                <PackagePlus className="size-4 text-stone-300 group-hover:text-emerald-700" />
              </button>
            ))}
          </div>

          <div className="mt-4 flex items-center justify-between border-b border-stone-200 pb-2">
            <div>
              <h4 className="text-sm font-bold">Productos en la boleta</h4>
              <p className="text-[11px] text-stone-500">{cart.length} productos distintos</p>
            </div>
          </div>

          <div className="max-h-52 min-h-24 divide-y divide-stone-100 overflow-y-auto">
            {cart.length ? (
              cart.map((item) => (
                <div
                  key={item.productId}
                  className="space-y-2 py-2.5"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-xs font-bold text-stone-950">{item.name}</p>
                      <p className="text-[10px] text-stone-400">{item.code}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <p className="min-w-16 text-right font-mono text-xs font-bold">
                        {money.format(item.quantity * item.unitPrice)}
                      </p>
                      <button
                        onClick={() => updateQuantity(item.productId, 0)}
                        className="text-stone-300 hover:text-red-600"
                        aria-label={`Quitar ${item.name}`}
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-[minmax(90px,1fr)_92px_auto] items-end gap-2">
                    <div>
                      <Label className="mb-1 text-[10px]">Kilos / presentación</Label>
                      <Input
                        value={item.presentation}
                        onChange={(event) =>
                          updateReceiptItem(item.productId, {
                            presentation: event.target.value,
                          })
                        }
                        aria-label={`Kilos o presentación de ${item.name}`}
                        className="h-8 px-2.5 text-xs font-semibold"
                      />
                    </div>
                    <div>
                      <Label className="mb-1 text-[10px]">Precio unitario</Label>
                      <Input
                        type="number"
                        min="0"
                        step="1"
                        value={item.unitPrice}
                        onChange={(event) =>
                          updateReceiptItem(item.productId, {
                            unitPrice: Math.max(0, Number(event.target.value)),
                          })
                        }
                        aria-label={`Precio unitario de ${item.name}`}
                        className="h-8 px-2 text-right font-mono text-xs font-bold"
                      />
                    </div>
                    <div>
                      <Label className="mb-1 text-[10px]">Cantidad</Label>
                      <div className="flex items-center rounded-lg border border-stone-200 bg-white">
                        <button
                          className="grid size-8 place-items-center"
                          onClick={() => updateQuantity(item.productId, item.quantity - 1)}
                          aria-label={`Restar ${item.name}`}
                        >
                          <Minus className="size-3" />
                        </button>
                        <input
                          className="h-8 w-9 border-x border-stone-200 text-center text-xs font-semibold outline-none"
                          type="number"
                          min="0.001"
                          step="1"
                          value={item.quantity}
                          aria-label={`Cantidad de ${item.name}`}
                          onChange={(event) =>
                            updateQuantity(item.productId, Number(event.target.value))
                          }
                        />
                        <button
                          className="grid size-8 place-items-center"
                          onClick={() => updateQuantity(item.productId, item.quantity + 1)}
                          aria-label={`Sumar ${item.name}`}
                        >
                          <Plus className="size-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                  <p className="text-[10px] text-stone-400">
                    Los cambios de kilos y precio se aplican solamente a esta boleta.
                  </p>
                </div>
              ))
            ) : (
              <div className="grid min-h-28 place-items-center text-center">
                <div>
                  <ShoppingBasket className="mx-auto size-6 text-stone-300" />
                  <p className="mt-1 text-xs font-semibold">La boleta está vacía</p>
                  <p className="text-[10px] text-stone-500">Selecciona un producto arriba.</p>
                </div>
              </div>
            )}
          </div>
        </section>
      </Card>
    </div>
  );
}
