"use server";

import { redirect } from "next/navigation";
import { z } from "zod";
import { getSupabaseServerClient } from "@/lib/supabase/server";

const setupSchema = z
  .object({
    fullName: z.string().trim().min(2).max(120),
    email: z.string().trim().email().max(254),
    password: z
      .string()
      .min(8, "La contraseña debe tener al menos 8 caracteres")
      .max(72),
    confirmPassword: z.string(),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Las contraseñas no coinciden",
    path: ["confirmPassword"],
  });

export async function createInitialAdmin(formData: FormData) {
  const supabase = await getSupabaseServerClient();
  if (!supabase) redirect("/setup?error=Supabase todavía no está configurado");

  const parsed = setupSchema.safeParse({
    fullName: formData.get("fullName"),
    email: formData.get("email"),
    password: formData.get("password"),
    confirmPassword: formData.get("confirmPassword"),
  });
  if (!parsed.success) {
    redirect(
      `/setup?error=${encodeURIComponent(parsed.error.issues[0]?.message || "Datos inválidos")}`,
    );
  }

  const { data: canSetup, error: setupError } = await supabase.rpc("can_bootstrap_admin");
  if (setupError || !canSetup) {
    redirect(
      `/login?error=${encodeURIComponent("El administrador inicial ya fue creado")}`,
    );
  }

  const { fullName, email, password } = parsed.data;
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: { full_name: fullName } },
  });
  if (error) {
    redirect(
      `/setup?error=${encodeURIComponent(
        error.message.toLowerCase().includes("already")
          ? "Ese correo ya está registrado"
          : "No se pudo crear la cuenta. Revisa los datos e inténtalo nuevamente",
      )}`,
    );
  }

  if (data.session) redirect("/");
  redirect(
    `/login?message=${encodeURIComponent(
      "Cuenta creada. Revisa tu correo para confirmarla y luego inicia sesión.",
    )}`,
  );
}
