"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import { uid } from "@/lib/format";
import { newCustomerSchema, newProductSchema, newReceiptSchema } from "@/lib/validation";
import type { AppData, Customer, Product, Receipt, ReceiptItem } from "@/lib/types";

const STORAGE_KEY = "distribuidora-damian-web-v1";

export type NewReceipt = {
  customerId?: string;
  customerName: string;
  customerPhone: string;
  customerAddress: string;
  items: ReceiptItem[];
  discountPercentage: number;
  paymentMethod: Receipt["paymentMethod"];
  amountPaid: number;
  notes: string;
};

export type NewProduct = Omit<Product, "id" | "active" | "requiresReview" | "sourcePage">;

function productFromDb(row: Record<string, unknown>): Product {
  return {
    id: String(row.id),
    code: String(row.code),
    name: String(row.name),
    presentation: String(row.presentation),
    supplier: String(row.supplier),
    category: String(row.category),
    wholesalePrice: row.wholesale_price === null ? null : Number(row.wholesale_price),
    active: Boolean(row.active),
    requiresReview: Boolean(row.requires_review),
    sourcePage: row.source_page ? Number(row.source_page) : undefined,
  };
}

function customerFromDb(row: Record<string, unknown>): Customer {
  return {
    id: String(row.id),
    name: String(row.name),
    phone: String(row.phone || ""),
    address: String(row.address || ""),
    document: String(row.document || ""),
    notes: String(row.notes || ""),
    active: Boolean(row.active),
  };
}

function receiptFromDb(row: Record<string, unknown>): Receipt {
  const items = ((row.receipt_items as Record<string, unknown>[]) || []).map((item) => ({
    productId: String(item.product_id || ""),
    code: String(item.product_code_snapshot || ""),
    name: String(item.product_name_snapshot),
    presentation: String(item.presentation_snapshot || ""),
    quantity: Number(item.quantity),
    unitPrice: Number(item.unit_price),
  }));
  return {
    id: String(row.id),
    code: String(row.receipt_code),
    customerId: row.customer_id ? String(row.customer_id) : undefined,
    customerName: String(row.customer_name_snapshot),
    customerPhone: String(row.customer_phone_snapshot || ""),
    customerAddress: String(row.customer_address_snapshot || ""),
    issuedAt: String(row.issued_at),
    items,
    subtotal: Number(row.subtotal),
    discountPercentage: Number(row.discount_value || 0),
    total: Number(row.total),
    paymentMethod: row.payment_method as Receipt["paymentMethod"],
    paymentStatus: row.payment_status as Receipt["paymentStatus"],
    amountPaid: Number(row.amount_paid),
    pendingAmount: Number(row.pending_amount),
    status: row.status as Receipt["status"],
    notes: String(row.notes || ""),
  };
}

export function useAppStore(initialProducts: Product[], demoMode: boolean) {
  const [data, setData] = useState<AppData>({
    products: initialProducts,
    customers: [],
    receipts: [],
  });
  const [loading, setLoading] = useState(!demoMode);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => setNotice(null), 3500);
    return () => window.clearTimeout(timeout);
  }, [notice]);

  const persist = useCallback(
    (next: AppData) => {
      setData(next);
      if (demoMode) localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    },
    [demoMode],
  );

  const loadCloud = useCallback(async () => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) return;
    setLoading(true);
    const [productsResult, customersResult, receiptsResult] = await Promise.all([
      supabase.from("products").select("*").order("name"),
      supabase.from("customers").select("*").order("name"),
      supabase
        .from("receipts")
        .select("*, receipt_items(*)")
        .order("issued_at", { ascending: false }),
    ]);
    const error = productsResult.error || customersResult.error || receiptsResult.error;
    if (error) {
      setNotice(`No se pudo sincronizar: ${error.message}`);
    } else {
      setData({
        products: (productsResult.data || []).map(productFromDb),
        customers: (customersResult.data || []).map(customerFromDb),
        receipts: (receiptsResult.data || []).map(receiptFromDb),
      });
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (demoMode) {
      const timeout = window.setTimeout(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          try {
            const parsed = JSON.parse(saved) as AppData;
            setData({
              products: parsed.products?.length ? parsed.products : initialProducts,
              customers: parsed.customers || [],
              receipts: parsed.receipts || [],
            });
          } catch {
            localStorage.removeItem(STORAGE_KEY);
          }
        }
        setLoading(false);
      }, 0);
      return () => window.clearTimeout(timeout);
    }
    const timeout = window.setTimeout(() => void loadCloud(), 0);
    return () => window.clearTimeout(timeout);
  }, [demoMode, initialProducts, loadCloud]);

  const updateProduct = useCallback(
    async (product: Product) => {
      const next = {
        ...data,
        products: data.products.map((current) => (current.id === product.id ? product : current)),
      };
      persist(next);
      if (!demoMode) {
        const supabase = getSupabaseBrowserClient();
        const old = data.products.find((current) => current.id === product.id);
        const { error } = await supabase!
          .from("products")
          .update({
            name: product.name,
            presentation: product.presentation,
            supplier: product.supplier,
            category: product.category,
            wholesale_price: product.wholesalePrice,
            active: product.active,
            requires_review: product.requiresReview,
          })
          .eq("id", product.id);
        if (!error && old?.wholesalePrice !== product.wholesalePrice) {
          await supabase!.from("price_history").insert({
            product_id: product.id,
            old_price: old?.wholesalePrice,
            new_price: product.wholesalePrice,
            reason: "Actualización desde la web",
          });
        }
        if (error) setNotice(error.message);
      }
      setNotice("Producto actualizado");
    },
    [data, demoMode, persist],
  );

  const addProduct = useCallback(
    async (input: NewProduct) => {
      const productInput = newProductSchema.parse({
        ...input,
        code: input.code.trim().toUpperCase(),
      });

      if (demoMode) {
        const product: Product = {
          ...productInput,
          id: uid("product"),
          active: true,
          requiresReview: productInput.wholesalePrice === null,
        };
        persist({
          ...data,
          products: [...data.products, product].sort((first, second) =>
            first.name.localeCompare(second.name, "es", { sensitivity: "base" }),
          ),
        });
        setNotice(`${product.name} agregado al catálogo`);
        return product;
      }

      const supabase = getSupabaseBrowserClient()!;
      const { data: saved, error } = await supabase
        .from("products")
        .insert({
          code: productInput.code,
          name: productInput.name,
          presentation: productInput.presentation,
          supplier: productInput.supplier,
          category: productInput.category,
          wholesale_price: productInput.wholesalePrice,
          active: true,
          requires_review: productInput.wholesalePrice === null,
        })
        .select()
        .single();

      if (error) {
        const message =
          error.code === "23505"
            ? "Ya existe un producto con ese código, nombre y presentación"
            : error.message;
        setNotice(message);
        throw new Error(message);
      }

      const product = productFromDb(saved);
      setData((current) => ({
        ...current,
        products: [...current.products, product].sort((first, second) =>
          first.name.localeCompare(second.name, "es", { sensitivity: "base" }),
        ),
      }));
      setNotice(`${product.name} guardado en Supabase`);
      return product;
    },
    [data, demoMode, persist],
  );

  const addCustomer = useCallback(
    async (input: Omit<Customer, "id" | "active">) => {
      const validatedInput = newCustomerSchema.parse(input);
      if (demoMode) {
        const customer: Customer = { ...validatedInput, id: uid("customer"), active: true };
        persist({ ...data, customers: [...data.customers, customer] });
        setNotice("Cliente agregado");
        return customer;
      }
      const supabase = getSupabaseBrowserClient()!;
      const { data: saved, error } = await supabase
        .from("customers")
        .insert({
          name: validatedInput.name,
          phone: validatedInput.phone || null,
          address: validatedInput.address || null,
          document: validatedInput.document || null,
          notes: validatedInput.notes || null,
        })
        .select()
        .single();
      if (error) {
        setNotice(error.message);
        throw error;
      }
      const customer = customerFromDb(saved);
      setData((current) => ({ ...current, customers: [...current.customers, customer] }));
      setNotice("Cliente agregado");
      return customer;
    },
    [data, demoMode, persist],
  );

  const saveReceipt = useCallback(
    async (input: NewReceipt) => {
      const validatedInput = newReceiptSchema.parse(input);
      const subtotal = validatedInput.items.reduce(
        (sum, item) => sum + item.quantity * item.unitPrice,
        0,
      );
      const total = Math.max(0, subtotal * (1 - validatedInput.discountPercentage / 100));
      const amountPaid = Math.min(Math.max(validatedInput.amountPaid, 0), total);
      if (demoMode) {
        const nextNumber = Math.max(
          500,
          ...data.receipts.map((receipt) => Number(receipt.code.replace(/\D/g, "")) || 0),
        ) + 1;
        const receipt: Receipt = {
          ...validatedInput,
          id: uid("receipt"),
          code: `BD-${String(nextNumber).padStart(6, "0")}`,
          issuedAt: new Date().toISOString(),
          subtotal,
          total,
          amountPaid,
          pendingAmount: total - amountPaid,
          paymentStatus: amountPaid >= total ? "paid" : amountPaid > 0 ? "partial" : "pending",
          status: "active",
        };
        persist({ ...data, receipts: [receipt, ...data.receipts] });
        setNotice(`Boleta ${receipt.code} guardada`);
        return receipt;
      }
      const supabase = getSupabaseBrowserClient()!;
      const { data: result, error } = await supabase.rpc("create_receipt", {
        p_payload: validatedInput,
      });
      if (error) {
        setNotice(error.message);
        throw error;
      }
      await loadCloud();
      setNotice(`Boleta ${String((result as { code?: string })?.code || "")} guardada`);
      return null;
    },
    [data, demoMode, loadCloud, persist],
  );

  const cancelReceipt = useCallback(
    async (id: string) => {
      const next = {
        ...data,
        receipts: data.receipts.map((receipt) =>
          receipt.id === id ? { ...receipt, status: "cancelled" as const } : receipt,
        ),
      };
      persist(next);
      if (!demoMode) {
        const { error } = await getSupabaseBrowserClient()!
          .from("receipts")
          .update({
            status: "cancelled",
            cancelled_at: new Date().toISOString(),
            cancellation_reason: "Eliminada desde el historial web",
          })
          .eq("id", id);
        if (error) setNotice(error.message);
      }
      setNotice("Boleta eliminada del historial activo; el registro fue conservado");
    },
    [data, demoMode, persist],
  );

  const applyPriceChanges = useCallback(
    async (changes: Product[]) => {
      const changedIds = new Set(changes.map((product) => product.id));
      persist({
        ...data,
        products: data.products.map((product) =>
          changedIds.has(product.id)
            ? changes.find((change) => change.id === product.id)!
            : product,
        ),
      });
      if (!demoMode) {
        const supabase = getSupabaseBrowserClient()!;
        const { error } = await supabase.rpc("apply_price_changes", {
          p_changes: changes.map((product) => ({
            id: product.id,
            wholesalePrice: product.wholesalePrice,
          })),
        });
        if (error) {
          setNotice(error.message);
          throw error;
        }
      }
      setNotice(`${changes.length} precios actualizados`);
    },
    [data, demoMode, persist],
  );

  const stats = useMemo(() => {
    const activeReceipts = data.receipts.filter((receipt) => receipt.status === "active");
    return {
      sales: activeReceipts.reduce((sum, receipt) => sum + receipt.total, 0),
      pending: activeReceipts.reduce((sum, receipt) => sum + receipt.pendingAmount, 0),
      receipts: activeReceipts.length,
      review: data.products.filter((product) => product.requiresReview).length,
    };
  }, [data]);

  return {
    data,
    stats,
    loading,
    notice,
    clearNotice: () => setNotice(null),
    addProduct,
    updateProduct,
    addCustomer,
    saveReceipt,
    cancelReceipt,
    applyPriceChanges,
  };
}
