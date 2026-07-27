"use server";

import { redirect } from "next/navigation";
import { z } from "zod";
import { getSupabaseServerClient } from "@/lib/supabase/server";

const loginSchema = z.object({
  email: z.string().trim().email().max(254),
  password: z.string().min(8).max(72),
});

export async function login(formData: FormData) {
  const supabase = await getSupabaseServerClient();
  if (!supabase) redirect("/");
  const parsed = loginSchema.safeParse({
    email: formData.get("email"),
    password: formData.get("password"),
  });
  if (!parsed.success) {
    redirect(`/login?error=${encodeURIComponent("Revisa el correo y la contraseña")}`);
  }

  const { email, password } = parsed.data;
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) {
    const authCode = "code" in error ? error.code : undefined;
    const message =
      authCode === "email_not_confirmed"
        ? "Tu cuenta está creada, pero falta confirmar el correo. Revisa tu bandeja o reenvía el mensaje."
        : "Correo o contraseña incorrectos";
    redirect(`/login?error=${encodeURIComponent(message)}&unconfirmed=${authCode === "email_not_confirmed" ? "1" : "0"}`);
  }

  const { data: userData } = await supabase.auth.getUser();
  const { data: profile } = await supabase
    .from("profiles")
    .select("role, active")
    .eq("id", userData.user?.id || "")
    .maybeSingle();
  if (!profile?.active || !["admin", "employee"].includes(profile.role)) {
    await supabase.auth.signOut();
    redirect(
      `/login?error=${encodeURIComponent("Esta cuenta todavía no tiene acceso al sistema")}`,
    );
  }
  redirect("/");
}

export async function resendConfirmation(formData: FormData) {
  const supabase = await getSupabaseServerClient();
  if (!supabase) redirect("/login");

  const email = z.string().trim().email().max(254).safeParse(formData.get("email"));
  if (!email.success) {
    redirect(`/login?error=${encodeURIComponent("Escribe tu correo para reenviar la confirmación")}`);
  }

  const { error } = await supabase.auth.resend({
    type: "signup",
    email: email.data,
  });
  if (error) {
    const limited = "code" in error && error.code === "over_email_send_rate_limit";
    redirect(
      `/login?error=${encodeURIComponent(
        limited
          ? "Espera unos minutos antes de solicitar otro correo"
          : "No se pudo reenviar el correo en este momento",
      )}`,
    );
  }

  redirect(
    `/login?message=${encodeURIComponent(
      "Confirmación reenviada. Revisa también la carpeta de correo no deseado.",
    )}`,
  );
}

export async function logout() {
  const supabase = await getSupabaseServerClient();
  if (supabase) await supabase.auth.signOut();
  redirect("/login");
}
