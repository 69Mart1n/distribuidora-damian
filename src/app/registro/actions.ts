"use server";

import { redirect } from "next/navigation";
import { z } from "zod";
import { getSupabaseServerClient } from "@/lib/supabase/server";

const registrationSchema = z
  .object({
    token: z.string().regex(/^[a-f0-9]{48}$/),
    fullName: z.string().trim().min(2, "Escribe el nombre").max(120),
    email: z.string().trim().email("Escribe un correo válido").max(254),
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

export async function registerInvitedAdmin(formData: FormData) {
  const supabase = await getSupabaseServerClient();
  if (!supabase) redirect("/login");

  const parsed = registrationSchema.safeParse({
    token: formData.get("token"),
    fullName: formData.get("fullName"),
    email: formData.get("email"),
    password: formData.get("password"),
    confirmPassword: formData.get("confirmPassword"),
  });
  if (!parsed.success) {
    const token = String(formData.get("token") || "");
    redirect(
      `/registro?token=${encodeURIComponent(token)}&error=${encodeURIComponent(
        parsed.error.issues[0]?.message || "Revisa los datos",
      )}`,
    );
  }

  const { token, fullName, email, password } = parsed.data;
  const { data: validInvitation, error: invitationError } = await supabase.rpc(
    "admin_invitation_is_valid",
    { p_token: token },
  );
  if (invitationError || validInvitation !== true) {
    redirect(`/registro?error=${encodeURIComponent("La invitación venció o ya fue utilizada")}`);
  }

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName,
        admin_invitation_token: token,
      },
    },
  });
  if (error) {
    redirect(
      `/registro?token=${encodeURIComponent(token)}&error=${encodeURIComponent(
        error.message.toLowerCase().includes("already")
          ? "Ese correo ya está registrado"
          : "No se pudo crear la cuenta. Revisa los datos e inténtalo nuevamente",
      )}`,
    );
  }

  if (data.session) redirect("/");
  redirect(
    `/login?message=${encodeURIComponent(
      "Cuenta administradora creada. Confirma el correo y luego inicia sesión.",
    )}`,
  );
}
