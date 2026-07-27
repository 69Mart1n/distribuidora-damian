"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Check, Eye, EyeOff, Pencil, Plus, Search, X } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/field";
import { money, normalize } from "@/lib/format";
import type { Product } from "@/lib/types";
import type { NewProduct } from "@/hooks/use-app-store";

export function ProductsView({
  products,
  onAdd,
  onUpdate,
}: {
  products: Product[];
  onAdd: (product: NewProduct) => Promise<Product>;
  onUpdate: (product: Product) => Promise<void>;
}) {
  const [search, setSearch] = useState("");
  const [supplier, setSupplier] = useState("Todos");
  const [reviewOnly, setReviewOnly] = useState(false);
  const [showHidden, setShowHidden] = useState(false);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const suppliers = useMemo(
    () => ["Todos", ...Array.from(new Set(products.map((product) => product.supplier))).sort()],
    [products],
  );
  const visible = useMemo(() => {
    const query = normalize(search);
    return products.filter(
      (product) =>
        (!query ||
          normalize(`${product.name} ${product.code} ${product.presentation}`).includes(query)) &&
        (supplier === "Todos" || product.supplier === supplier) &&
        (!reviewOnly || product.requiresReview) &&
        (showHidden || product.active),
    );
  }, [products, reviewOnly, search, showHidden, supplier]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Catálogo de productos</h2>
          <p className="text-sm text-stone-500">
            {visible.length} de {products.length} productos
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setAdding(true)}>
            <Plus className="size-4" />
            Añadir producto
          </Button>
          <label className="flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs font-semibold text-stone-700">
            <input
              type="checkbox"
              checked={showHidden}
              onChange={(event) => setShowHidden(event.target.checked)}
              className="accent-emerald-700"
            />
            Mostrar productos ocultos
          </label>
          <label className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
            <input
              type="checkbox"
              checked={reviewOnly}
              onChange={(event) => setReviewOnly(event.target.checked)}
              className="accent-amber-700"
            />
            Solo pendientes de revisión
          </label>
        </div>
      </div>

      <Card className="p-4">
        <div className="grid gap-3 md:grid-cols-[1fr_260px]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 size-4 text-stone-400" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar por producto, código o presentación…"
              className="pl-9"
            />
          </div>
          <Select value={supplier} onChange={(event) => setSupplier(event.target.value)}>
            {suppliers.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </Select>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="border-b border-stone-200 bg-stone-50/80 text-xs font-semibold uppercase tracking-wide text-stone-500">
              <tr>
                <th className="px-5 py-3">Producto</th>
                <th className="px-4 py-3">Proveedor</th>
                <th className="px-4 py-3">Categoría</th>
                <th className="px-4 py-3 text-right">Mayorista</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {visible.map((product) => (
                <tr
                  key={product.id}
                  className={product.active ? "transition hover:bg-stone-50/70" : "bg-stone-50/60 text-stone-400"}
                >
                  <td className="px-5 py-3.5">
                    <div className="font-semibold">{product.name}</div>
                    <div className="mt-0.5 text-xs text-stone-500">
                      <span className="font-mono">{product.code}</span> · {product.presentation}
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-stone-600">{product.supplier}</td>
                  <td className="px-4 py-3.5">
                    <span className="rounded-full bg-stone-100 px-2 py-1 text-xs font-medium text-stone-600">
                      {product.category}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono font-bold">
                    {product.wholesalePrice === null ? "—" : money.format(product.wholesalePrice)}
                  </td>
                  <td className="px-4 py-3.5">
                    {!product.active ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-stone-200 px-2 py-1 text-xs font-semibold text-stone-600">
                        <EyeOff className="size-3" /> Oculto
                      </span>
                    ) : product.requiresReview ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800">
                        <AlertTriangle className="size-3" /> Revisar
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
                        <Check className="size-3" /> Confirmado
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      className={product.active ? "text-stone-500" : "text-emerald-700"}
                      onClick={() => void onUpdate({ ...product, active: !product.active })}
                      aria-label={product.active ? `Ocultar ${product.name}` : `Mostrar ${product.name}`}
                      title={product.active ? "Ocultar producto" : "Volver a mostrar"}
                    >
                      {product.active ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setEditing(product)}>
                      <Pencil className="size-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {adding && (
        <AddProduct
          products={products}
          onClose={() => setAdding(false)}
          onSave={async (product) => {
            await onAdd(product);
            setAdding(false);
          }}
        />
      )}

      {editing && (
        <EditProduct
          product={editing}
          onClose={() => setEditing(null)}
          onSave={async (product) => {
            await onUpdate(product);
            setEditing(null);
          }}
        />
      )}
    </div>
  );
}

function nextProductCode(products: Product[]) {
  const nextNumber =
    Math.max(
      0,
      ...products.map((product) => {
        const match = product.code.match(/^P(\d+)$/i);
        return match ? Number(match[1]) : 0;
      }),
    ) + 1;
  return `P${String(nextNumber).padStart(4, "0")}`;
}

function AddProduct({
  products,
  onClose,
  onSave,
}: {
  products: Product[];
  onClose: () => void;
  onSave: (product: NewProduct) => Promise<void>;
}) {
  const suppliers = useMemo(
    () => Array.from(new Set(products.map((product) => product.supplier))).sort(),
    [products],
  );
  const categories = useMemo(
    () => Array.from(new Set(products.map((product) => product.category))).sort(),
    [products],
  );
  const [draft, setDraft] = useState<NewProduct>({
    code: nextProductCode(products),
    name: "",
    presentation: "",
    supplier: suppliers[0] || "Otros",
    category: categories[0] || "Otros",
    wholesalePrice: null,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const codeExists = products.some(
    (product) => normalize(product.code) === normalize(draft.code),
  );
  const isValid =
    draft.name.trim() &&
    draft.presentation.trim() &&
    draft.code.trim() &&
    draft.supplier &&
    draft.category &&
    draft.wholesalePrice !== null &&
    draft.wholesalePrice >= 0 &&
    !codeExists;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-stone-950/35 p-4 backdrop-blur-sm">
      <Card className="w-full max-w-2xl p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold">Añadir nuevo producto</h3>
            <p className="mt-0.5 text-sm text-stone-500">
              Se incorporará al catálogo y quedará disponible para las boletas.
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Cerrar">
            <X className="size-4" />
          </Button>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Label>Nombre del producto</Label>
            <Input
              autoFocus
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
              placeholder="Ejemplo: Vittamax Adulto"
            />
          </div>
          <div>
            <Label>Presentación / kilos</Label>
            <Input
              value={draft.presentation}
              onChange={(event) => setDraft({ ...draft, presentation: event.target.value })}
              placeholder="Ejemplo: 25 kg"
            />
          </div>
          <div>
            <Label>Precio mayorista</Label>
            <Input
              type="number"
              min="0"
              step="1"
              value={draft.wholesalePrice ?? ""}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  wholesalePrice: event.target.value ? Number(event.target.value) : null,
                })
              }
              placeholder="0"
            />
          </div>
          <div>
            <Label>Distribuidora</Label>
            <Select
              value={draft.supplier}
              onChange={(event) => setDraft({ ...draft, supplier: event.target.value })}
            >
              {suppliers.map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Categoría</Label>
            <Select
              value={draft.category}
              onChange={(event) => setDraft({ ...draft, category: event.target.value })}
            >
              {categories.map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </Select>
          </div>
          <div className="sm:col-span-2">
            <Label>Código de producto</Label>
            <Input
              value={draft.code}
              onChange={(event) => {
                setDraft({ ...draft, code: event.target.value.toUpperCase() });
                setError("");
              }}
              className="font-mono"
            />
            <p className={`mt-1.5 text-xs ${codeExists ? "text-red-600" : "text-stone-500"}`}>
              {codeExists
                ? "Ese código ya pertenece a otro producto."
                : "El sistema propone automáticamente el próximo código disponible."}
            </p>
          </div>
        </div>

        {error && (
          <p className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
            {error}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button
            disabled={saving || !isValid}
            onClick={async () => {
              setSaving(true);
              setError("");
              try {
                await onSave(draft);
              } catch (cause) {
                setError(cause instanceof Error ? cause.message : "No se pudo guardar el producto");
                setSaving(false);
              }
            }}
          >
            {saving ? "Guardando…" : "Guardar producto"}
          </Button>
        </div>
      </Card>
    </div>
  );
}

function EditProduct({
  product,
  onClose,
  onSave,
}: {
  product: Product;
  onClose: () => void;
  onSave: (product: Product) => Promise<void>;
}) {
  const [draft, setDraft] = useState(product);
  const [saving, setSaving] = useState(false);
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-stone-950/35 p-4 backdrop-blur-sm">
      <Card className="w-full max-w-lg p-5 shadow-2xl">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold">Editar producto</h3>
            <p className="font-mono text-xs text-stone-500">{product.code}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Label>Nombre</Label>
            <Input
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          </div>
          <div>
            <Label>Presentación</Label>
            <Input
              value={draft.presentation}
              onChange={(event) => setDraft({ ...draft, presentation: event.target.value })}
            />
          </div>
          <div>
            <Label>Precio mayorista</Label>
            <Input
              type="number"
              min="0"
              value={draft.wholesalePrice ?? ""}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  wholesalePrice: event.target.value ? Number(event.target.value) : null,
                  requiresReview: !event.target.value,
                })
              }
            />
          </div>
          <div>
            <Label>Proveedor</Label>
            <Input
              value={draft.supplier}
              onChange={(event) => setDraft({ ...draft, supplier: event.target.value })}
            />
          </div>
          <div>
            <Label>Categoría</Label>
            <Input
              value={draft.category}
              onChange={(event) => setDraft({ ...draft, category: event.target.value })}
            />
          </div>
        </div>
        <label className="mt-4 flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={!draft.requiresReview}
            onChange={(event) => setDraft({ ...draft, requiresReview: !event.target.checked })}
            className="accent-emerald-700"
          />
          Precio revisado y confirmado
        </label>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button
            disabled={saving || !draft.name.trim()}
            onClick={async () => {
              setSaving(true);
              await onSave(draft);
            }}
          >
            {saving ? "Guardando…" : "Guardar cambios"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
