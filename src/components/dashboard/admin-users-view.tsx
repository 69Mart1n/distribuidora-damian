"use client";

import { useEffect, useState } from "react";
import { Check, Copy, Link2, ShieldCheck, UserCog } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

type AdminProfile = {
  id: string;
  full_name: string;
  email: string | null;
  active: boolean;
};

export function AdminUsersView() {
  const [admins, setAdmins] = useState<AdminProfile[]>([]);
  const [invitationUrl, setInvitationUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) return;

    async function loadAdmins() {
      const result = await supabase
        .from("profiles")
        .select("id, full_name, email, active")
        .eq("role", "admin")
        .order("full_name");
      setAdmins((result.data || []) as AdminProfile[]);
    }

    void loadAdmins();
  }, []);

  async function createInvitation() {
    const supabase = getSupabaseBrowserClient();
    if (!supabase) return;
    setLoading(true);
    setError("");
    setCopied(false);

    const { data, error: invitationError } = await supabase.rpc(
      "create_admin_invitation",
    );
    if (invitationError || typeof data !== "string") {
      setError("No se pudo crear la invitación. Inténtalo nuevamente.");
      setLoading(false);
      return;
    }

    setInvitationUrl(`${window.location.origin}/registro?token=${data}`);
    setLoading(false);
  }

  async function copyInvitation() {
    if (!invitationUrl) return;
    await navigator.clipboard.writeText(invitationUrl);
    setCopied(true);
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Usuarios administradores</h2>
        <p className="text-sm text-stone-500">
          Invita personas de confianza con los mismos permisos de administración.
        </p>
      </div>

      <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
            <Link2 className="size-5" />
          </div>
          <div className="flex-1">
            <h3 className="font-bold">Nueva invitación</h3>
            <p className="mt-1 text-sm text-stone-500">
              El enlace funciona una sola vez y vence después de 72 horas.
            </p>
            <Button className="mt-4" onClick={createInvitation} disabled={loading}>
              <UserCog className="size-4" />
              {loading ? "Creando…" : "Crear enlace de administrador"}
            </Button>
          </div>
        </div>

        {invitationUrl && (
          <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-sm font-semibold text-emerald-950">Enlace listo para compartir</p>
            <p className="mt-2 break-all font-mono text-xs text-emerald-900">{invitationUrl}</p>
            <Button className="mt-3" variant="outline" onClick={copyInvitation}>
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
              {copied ? "Copiado" : "Copiar enlace"}
            </Button>
          </div>
        )}
        {error && <p className="mt-4 text-sm text-red-700">{error}</p>}
      </section>

      <section className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
        <div className="border-b border-stone-200 px-5 py-4">
          <h3 className="font-bold">Administradores actuales</h3>
        </div>
        <div className="divide-y divide-stone-100">
          {admins.map((admin) => (
            <div key={admin.id} className="flex items-center gap-3 px-5 py-4">
              <div className="grid size-9 place-items-center rounded-full bg-emerald-50 text-emerald-700">
                <ShieldCheck className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{admin.full_name}</p>
                <p className="truncate text-sm text-stone-500">{admin.email}</p>
              </div>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
                {admin.active ? "Activo" : "Inactivo"}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
