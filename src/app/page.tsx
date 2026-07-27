import productsData from "@/data/products.json";
import promotionsData from "@/data/promotions.json";
import { DashboardApp } from "@/components/dashboard/dashboard-app";
import { isSupabaseConfigured } from "@/lib/supabase/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import type { AppRole, Product, Promotion } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Home() {
  const demoMode = !isSupabaseConfigured();
  let userRole: AppRole = "admin";
  if (!demoMode) {
    const supabase = await getSupabaseServerClient();
    const { data: claimsData } = await supabase!.auth.getClaims();
    const { data: profile } = await supabase!
      .from("profiles")
      .select("role")
      .eq("id", String(claimsData?.claims?.sub || ""))
      .single();
    userRole = (profile?.role as AppRole) || "client";
  }
  return (
    <DashboardApp
      initialProducts={productsData as Product[]}
      promotions={promotionsData as Promotion[]}
      demoMode={demoMode}
      userRole={userRole}
    />
  );
}
