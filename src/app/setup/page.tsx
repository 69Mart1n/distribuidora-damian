import Image from "next/image";
import { ShieldCheck } from "lucide-react";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/field";
import { isSupabaseConfigured } from "@/lib/supabase/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { createInitialAdmin } from "./actions";

export default async function SetupPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  const configured = isSupabaseConfigured();
  let canSetup = false;

  if (configured) {
    const supabase = await getSupabaseServerClient();
    const result = await supabase?.rpc("can_bootstrap_admin");
    canSetup = result?.data === true;
    if (!result?.error && !canSetup) redirect("/login");
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#f4f1e9] px-4 py-8">
      <div className="w-full max-w-md rounded-3xl border border-white/70 bg-white/95 p-8 shadow-2xl shadow-emerald-950/10">
        <Image
          src="/logo.png"
          alt="Distribuidora Damián"
          width={260}
          height={190}
          priority
          className="mx-auto h-auto w-48"
        />
        <div className="mt-5 text-center">
          <div className="mx-auto mb-3 grid size-10 place-items-center rounded-full bg-emerald-100 text-emerald-800">
            <ShieldCheck className="size-5" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-stone-900">
            Crear administrador
          </h1>
          <p className="mt-1 text-sm text-stone-500">
            Esta opción se desactiva después de crear la primera cuenta.
          </p>
        </div>

        {configured && canSetup ? (
          <form action={createInitialAdmin} className="mt-7 space-y-4">
            <div>
              <Label htmlFor="fullName">Nombre</Label>
              <Input id="fullName" name="fullName" autoComplete="name" required maxLength={120} />
            </div>
            <div>
              <Label htmlFor="email">Correo</Label>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                maxLength={254}
              />
            </div>
            <div>
              <Label htmlFor="password">Contraseña</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                maxLength={72}
              />
              <p className="mt-1.5 text-xs text-stone-500">
                Mínimo 8 caracteres. No es obligatorio usar símbolos.
              </p>
            </div>
            <div>
              <Label htmlFor="confirmPassword">Repetir contraseña</Label>
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                maxLength={72}
              />
            </div>
            {error && (
              <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
            )}
            <Button className="w-full" size="lg">Crear cuenta segura</Button>
            <a href="/login" className="block text-center text-sm text-stone-500 hover:underline">
              Volver al ingreso
            </a>
          </form>
        ) : (
          <div className="mt-7 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            Primero hay que aplicar la migración y configurar la conexión segura con Supabase.
          </div>
        )}
      </div>
    </main>
  );
}
