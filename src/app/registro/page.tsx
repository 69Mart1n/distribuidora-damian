import Image from "next/image";
import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/field";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { registerInvitedAdmin } from "./actions";

export default async function AdminRegistrationPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string; error?: string }>;
}) {
  const { token = "", error } = await searchParams;
  const supabase = await getSupabaseServerClient();
  const tokenFormatIsValid = /^[a-f0-9]{48}$/.test(token);
  const invitation = tokenFormatIsValid
    ? await supabase?.rpc("admin_invitation_is_valid", { p_token: token })
    : null;
  const canRegister = invitation?.data === true && !invitation.error;

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
            Crear cuenta administradora
          </h1>
          <p className="mt-1 text-sm text-stone-500">
            Completa tus datos usando la invitación recibida.
          </p>
        </div>

        {canRegister ? (
          <form action={registerInvitedAdmin} className="mt-7 space-y-4">
            <input type="hidden" name="token" value={token} />
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
            <Button className="w-full" size="lg">Crear mi cuenta</Button>
          </form>
        ) : (
          <div className="mt-7 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            Esta invitación venció, ya fue utilizada o no es válida. Solicita una nueva al
            administrador.
          </div>
        )}
      </div>
    </main>
  );
}
