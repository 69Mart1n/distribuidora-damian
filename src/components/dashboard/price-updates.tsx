"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, ArrowRight, BadgePercent, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/field";
import { money } from "@/lib/format";
import type { Product, Promotion } from "@/lib/types";

export function PriceUpdates({
  products,
  promotions,
  onApply,
}: {
  products: Product[];
  promotions: Promotion[];
  onApply: (products: Product[]) => Promise<void>;
}) {
  const [supplier, setSupplier] = useState("");
  const [category, setCategory] = useState("");
  const [operation, setOperation] = useState<"increase" | "decrease">("increase");
  const [adjustmentType, setAdjustmentType] = useState<"percentage" | "fixed">("percentage");
  const [value, setValue] = useState(0);
  const [excludedIds, setExcludedIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const suppliers = useMemo(
    () => Array.from(new Set(products.map((product) => product.supplier))).sort(),
    [products],
  );
  const categories = useMemo(
    () =>
      Array.from(
        new Set(
          products
            .filter((product) => !supplier || product.supplier === supplier)
            .map((product) => product.category),
        ),
      ).sort(),
    [products, supplier],
  );
  const candidates = useMemo(() => {
    if (!supplier && !category) return [];
    const sign = operation === "increase" ? 1 : -1;
    return products
      .filter(
        (product) =>
          product.active &&
          product.wholesalePrice !== null &&
          (!supplier || product.supplier === supplier) &&
          (!category || product.category === category),
      )
      .sort((a, b) => {
        const byName = a.name.localeCompare(b.name, "es", { sensitivity: "base" });
        return byName || a.presentation.localeCompare(b.presentation, "es", { numeric: true });
      })
      .map((product) => {
        const change =
          value <= 0
            ? 0
            : adjustmentType === "percentage"
              ? product.wholesalePrice! * (value / 100)
              : value;
        return {
          ...product,
          wholesalePrice: Math.max(1, Math.round(product.wholesalePrice! + sign * change)),
          requiresReview: false,
        };
      });
  }, [adjustmentType, category, operation, products, supplier, value]);
  const affected = useMemo(
    () => candidates.filter((product) => !excludedIds.has(product.id)),
    [candidates, excludedIds],
  );
  const allSelected = candidates.length > 0 && affected.length === candidates.length;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Actualización de precios</h2>
        <p className="text-sm text-stone-500">Vista previa antes de aplicar cambios masivos</p>
      </div>

      <div className="grid gap-5 xl:grid-cols-[.65fr_1.35fr]">
        <div className="space-y-5">
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <div className="grid size-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
                <BadgePercent className="size-5" />
              </div>
              <div>
                <h3 className="font-bold">Nuevo ajuste</h3>
                <p className="text-xs text-stone-500">Filtra por distribuidora y categoría</p>
              </div>
            </div>
            <div className="mt-5 space-y-4">
              <div>
                <Label>Distribuidora / proveedor</Label>
                <Select
                  value={supplier}
                  onChange={(event) => {
                    setSupplier(event.target.value);
                    setCategory("");
                    setExcludedIds(new Set());
                  }}
                >
                  <option value="">Todas las distribuidoras</option>
                  {suppliers.map((item) => <option key={item}>{item}</option>)}
                </Select>
              </div>
              <div>
                <Label>Categoría</Label>
                <Select
                  value={category}
                  onChange={(event) => {
                    setCategory(event.target.value);
                    setExcludedIds(new Set());
                  }}
                >
                  <option value="">Todas las categorías</option>
                  {categories.map((item) => <option key={item}>{item}</option>)}
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Operación</Label>
                  <Select
                    value={operation}
                    onChange={(event) => setOperation(event.target.value as typeof operation)}
                  >
                    <option value="increase">Aumentar</option>
                    <option value="decrease">Disminuir</option>
                  </Select>
                </div>
                <div>
                  <Label>Tipo de ajuste</Label>
                  <Select
                    value={adjustmentType}
                    onChange={(event) =>
                      setAdjustmentType(event.target.value as typeof adjustmentType)
                    }
                  >
                    <option value="percentage">Porcentaje (%)</option>
                    <option value="fixed">Importe fijo ($)</option>
                  </Select>
                </div>
              </div>
              <div>
                  <Label>
                    {adjustmentType === "percentage"
                      ? "Porcentaje a aplicar"
                      : "Pesos por cada producto"}
                  </Label>
                  <Input
                    type="number"
                    min="0"
                    max={adjustmentType === "percentage" ? 99 : undefined}
                    step={adjustmentType === "percentage" ? 0.5 : 1}
                    value={value}
                    onChange={(event) => setValue(Number(event.target.value))}
                  />
              </div>
              <div className="rounded-xl border border-blue-200 bg-blue-50 p-3 text-xs leading-5 text-blue-900">
                Selecciona al menos una distribuidora o categoría. Verás el precio actual y el
                nuevo antes de confirmar; los importes se redondean al peso entero.
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <h3 className="font-bold">Promociones por volumen</h3>
            <p className="mt-1 text-xs text-stone-500">Detectadas en la nueva lista mayorista</p>
            <div className="mt-4 space-y-2">
              {promotions.map((promotion) => (
                <div
                  key={`${promotion.name}-${promotion.minimumKg}`}
                  className="flex items-center justify-between rounded-xl bg-stone-50 px-3 py-2.5 text-sm"
                >
                  <div>
                    <p className="font-semibold">{promotion.name}</p>
                    <p className="text-xs text-stone-500">Desde {promotion.minimumKg} kg</p>
                  </div>
                  <span className="rounded-full bg-emerald-100 px-2 py-1 font-mono text-xs font-bold text-emerald-800">
                    -{promotion.discountPercentage}%
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
            <div>
              <h3 className="font-bold">Vista previa</h3>
              <p className="text-xs text-stone-500">
                {affected.length} de {candidates.length} productos seleccionados
              </p>
            </div>
            <Button
              disabled={value <= 0 || !affected.length || saving}
              onClick={async () => {
                setSaving(true);
                await onApply(affected);
                setSaving(false);
                setValue(0);
              }}
            >
              <CheckCircle2 className="size-4" />
              {saving ? "Aplicando…" : "Aplicar cambios"}
            </Button>
          </div>
          {candidates.length ? (
            <div className="max-h-[700px] overflow-auto">
              <table className="w-full min-w-[600px] text-left text-sm">
                <thead className="sticky top-0 border-b border-stone-200 bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
                  <tr>
                    <th className="w-12 px-5 py-3">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={(event) =>
                          setExcludedIds(
                            event.target.checked
                              ? new Set()
                              : new Set(candidates.map((product) => product.id)),
                          )
                        }
                        aria-label={allSelected ? "Deseleccionar todos" : "Seleccionar todos"}
                        className="size-4 accent-emerald-700"
                      />
                    </th>
                    <th className="px-5 py-3">Producto</th>
                    <th className="px-4 py-3 text-right">Anterior</th>
                    <th className="px-4 py-3" />
                    <th className="px-5 py-3 text-right">Nuevo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {candidates.map((product) => {
                    const old = products.find((item) => item.id === product.id)!;
                    const selected = !excludedIds.has(product.id);
                    return (
                      <tr key={product.id} className={selected ? "" : "bg-stone-50/80 opacity-50"}>
                        <td className="px-5 py-3">
                          <input
                            type="checkbox"
                            checked={selected}
                            onChange={(event) =>
                              setExcludedIds((current) => {
                                const next = new Set(current);
                                if (event.target.checked) next.delete(product.id);
                                else next.add(product.id);
                                return next;
                              })
                            }
                            aria-label={`Aplicar ajuste a ${product.name} ${product.presentation}`}
                            className="size-4 accent-emerald-700"
                          />
                        </td>
                        <td className="px-5 py-3">
                          <p className="font-semibold">{product.name}</p>
                          <p className="text-xs text-stone-500">{product.presentation}</p>
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-stone-500">
                          {money.format(old.wholesalePrice!)}
                        </td>
                        <td className="px-4 py-3 text-stone-300"><ArrowRight className="size-4" /></td>
                        <td className="px-5 py-3 text-right font-mono font-bold text-emerald-800">
                          {value > 0 ? (
                            money.format(product.wholesalePrice!)
                          ) : (
                            <span className="font-sans text-xs font-medium text-stone-400">
                              Sin definir
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="grid min-h-[420px] place-items-center px-6 text-center">
              <div>
                <AlertTriangle className="mx-auto size-9 text-stone-300" />
                <p className="mt-3 font-semibold">Selecciona un grupo</p>
                <p className="max-w-sm text-sm text-stone-500">
                  Elige una distribuidora o categoría para ver inmediatamente sus productos.
                </p>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
