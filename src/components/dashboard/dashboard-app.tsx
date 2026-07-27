"use client";

import { useState } from "react";
import Image from "next/image";
import {
  FileClock,
  FilePlus2,
  Home,
  LogOut,
  Menu,
  PackageSearch,
  SlidersHorizontal,
  Users,
  UserCog,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AppRole, Product, Promotion } from "@/lib/types";
import { useAppStore } from "@/hooks/use-app-store";
import { Overview } from "./overview";
import { ProductsView } from "./products-view";
import { CustomersView } from "./customers-view";
import { ReceiptBuilder } from "./receipt-builder";
import { ReceiptHistory } from "./receipt-history";
import { PriceUpdates } from "./price-updates";
import { AdminUsersView } from "./admin-users-view";
import { Button } from "@/components/ui/button";
import { logout } from "@/app/login/actions";

export type ViewName =
  | "Inicio"
  | "Nueva boleta"
  | "Productos"
  | "Clientes"
  | "Historial"
  | "Precios"
  | "Usuarios";

const navItems: { name: ViewName; icon: typeof Home }[] = [
  { name: "Inicio", icon: Home },
  { name: "Nueva boleta", icon: FilePlus2 },
  { name: "Productos", icon: PackageSearch },
  { name: "Clientes", icon: Users },
  { name: "Historial", icon: FileClock },
  { name: "Precios", icon: SlidersHorizontal },
  { name: "Usuarios", icon: UserCog },
];

export function DashboardApp({
  initialProducts,
  promotions,
  demoMode,
  userRole,
}: {
  initialProducts: Product[];
  promotions: Promotion[];
  demoMode: boolean;
  userRole: AppRole;
}) {
  const [view, setView] = useState<ViewName>("Inicio");
  const [mobileOpen, setMobileOpen] = useState(false);
  const store = useAppStore(initialProducts, demoMode);

  const navigate = (next: ViewName) => {
    setView(next);
    setMobileOpen(false);
  };

  return (
    <div className="min-h-screen bg-[#f7f6f2] text-stone-900">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-emerald-950/10 bg-[#163d2a] text-white transition-transform lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-28 items-center border-b border-white/10 px-5">
          <div className="flex flex-1 items-center justify-center">
            <Image
              src="/logo.png"
              alt="Distribuidora Damián"
              width={190}
              height={130}
              priority
              className="h-auto max-h-20 w-48 object-contain brightness-0 invert"
            />
          </div>
          <button
            className="ml-auto rounded-lg p-2 text-white/70 hover:bg-white/10 lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar menú"
          >
            <X className="size-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {navItems
            .filter(
              (item) =>
                userRole === "admin" || !["Precios", "Usuarios"].includes(item.name),
            )
            .map((item) => (
            <button
              key={item.name}
              onClick={() => navigate(item.name)}
              className={cn(
                "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition",
                view === item.name
                  ? "bg-white text-emerald-950 shadow-sm"
                  : "text-emerald-50/75 hover:bg-white/10 hover:text-white",
              )}
            >
              <item.icon className="size-4.5" />
              {item.name}
            </button>
            ))}
        </nav>
        <div className="border-t border-white/10 p-4 text-xs text-emerald-100/60">
          <div className="mb-1 flex items-center gap-2">
            <span
              className={cn(
                "size-2 rounded-full",
                demoMode ? "bg-amber-400" : "bg-emerald-400",
              )}
            />
            {demoMode ? "Modo local" : "Conectado a la base de datos"}
          </div>
          <p>Distribuidora Damián</p>
        </div>
      </aside>

      {mobileOpen && (
        <button
          className="fixed inset-0 z-30 bg-black/35 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Cerrar menú"
        />
      )}

      <div className="dashboard-shell lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center border-b border-stone-200/80 bg-[#f7f6f2]/90 px-4 backdrop-blur md:px-7">
          <Button
            variant="ghost"
            size="icon"
            className="mr-2 lg:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Abrir menú"
          >
            <Menu className="size-5" />
          </Button>
          <div>
            <h1 className="text-base font-bold">{view}</h1>
            <p className="hidden text-xs text-stone-500 sm:block">
              Gestión comercial de Distribuidora Damián
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden rounded-full border border-stone-200 bg-white px-3 py-1 text-xs font-medium text-stone-600 sm:inline">
              {store.data.products.length} productos
            </span>
            {!demoMode && (
              <form action={logout}>
                <Button variant="outline" size="sm" type="submit" title="Cerrar sesión">
                  <LogOut className="size-4" />
                  <span className="hidden md:inline">Salir</span>
                </Button>
              </form>
            )}
            <Button size="sm" onClick={() => navigate("Nueva boleta")}>
              <FilePlus2 className="size-4" /> Nueva boleta
            </Button>
          </div>
        </header>

        <main className="mx-auto max-w-[1500px] p-4 md:p-7">
          {store.loading ? (
            <div className="grid min-h-[60vh] place-items-center text-sm text-stone-500">
              Sincronizando datos…
            </div>
          ) : (
            <>
              {view === "Inicio" && (
                <Overview data={store.data} stats={store.stats} navigate={navigate} />
              )}
              {view === "Productos" && (
                <ProductsView
                  products={store.data.products}
                  onAdd={store.addProduct}
                  onUpdate={store.updateProduct}
                />
              )}
              {view === "Clientes" && (
                <CustomersView
                  customers={store.data.customers}
                  receipts={store.data.receipts}
                  onAdd={store.addCustomer}
                  onNewReceipt={() => navigate("Nueva boleta")}
                />
              )}
              {view === "Nueva boleta" && (
                <ReceiptBuilder
                  products={store.data.products}
                  customers={store.data.customers}
                  promotions={promotions}
                  onSave={store.saveReceipt}
                  onSaved={() => navigate("Historial")}
                />
              )}
              {view === "Historial" && (
                <ReceiptHistory
                  receipts={store.data.receipts}
                  onCancel={store.cancelReceipt}
                  allowCancel={userRole === "admin"}
                />
              )}
              {view === "Precios" && userRole === "admin" && (
                <PriceUpdates
                  products={store.data.products}
                  promotions={promotions}
                  onApply={store.applyPriceChanges}
                />
              )}
              {view === "Usuarios" && userRole === "admin" && <AdminUsersView />}
            </>
          )}
        </main>
      </div>

      {store.notice && (
        <button
          onClick={store.clearNotice}
          className="fixed bottom-5 right-5 z-50 max-w-sm rounded-xl bg-stone-950 px-4 py-3 text-sm font-medium text-white shadow-xl"
          aria-label="Cerrar notificación"
        >
          {store.notice}
        </button>
      )}
    </div>
  );
}
