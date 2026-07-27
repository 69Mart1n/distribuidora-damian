import Image from "next/image";
import { LockKeyhole } from "lucide-react";
import { login, resendConfirmation } from "./actions";
import { Input, Label } from "@/components/ui/field";
import { Button } from "@/components/ui/button";
import { isSupabaseConfigured } from "@/lib/supabase/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; message?: string; unconfirmed?: string }>;
}) {
  const { error, message, unconfirmed } = await searchParams;
  const configured = isSupabaseConfigured();
  let canCreateInitialAdmin = false;
  if (configured) {
    const supabase = await getSupabaseServerClient();
    const result = await supabase?.rpc("can_bootstrap_admin");
    canCreateInitialAdmin = result?.data === true;
  }
  return (
    <main className="grid min-h-screen place-items-center bg-[#f4f1e9] px-4">
      <div className="w-full max-w-md rounded-3xl border border-white/70 bg-white/90 p-8 shadow-2xl shadow-emerald-950/10 backdrop-blur">
        <Image
          src="/logo.png"
          alt="Distribuidora Damián"
          width={260}
          height={190}
          priority
          className="mx-auto h-auto w-52"
        />
        <div className="mt-6 text-center">
          <div className="mx-auto mb-3 grid size-10 place-items-center rounded-full bg-emerald-100 text-emerald-800">
            <LockKeyhole className="size-5" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-stone-900">
            Ingreso al sistema
          </h1>
          <p className="mt-1 text-sm text-stone-500">Gestión comercial y de boletas</p>
        </div>
        {configured ? (
          <form action={login} className="mt-7 space-y-4">
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
                autoComplete="current-password"
                required
                minLength={8}
                maxLength={72}
              />
            </div>
            {error && (
              <p className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
            )}
            {message && (
              <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                {message}
              </p>
            )}
            <Button className="w-full" size="lg">Ingresar</Button>
            {unconfirmed === "1" && (
              <Button
                className="w-full"
                variant="outline"
                type="submit"
                formAction={resendConfirmation}
                formNoValidate
              >
                Reenviar correo de confirmación
              </Button>
            )}
            {canCreateInitialAdmin && (
              <a
                href="/setup"
                className="block text-center text-sm font-semibold text-emerald-800 hover:underline"
              >
                Crear el administrador inicial
              </a>
            )}
          </form>
        ) : (
          <div className="mt-7 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            El modo local está activo. Al configurar las variables de Supabase, este acceso se
            habilita automáticamente.
          </div>
        )}
      </div>
    </main>
  );
}
