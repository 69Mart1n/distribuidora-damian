import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

function applySecurityHeaders(response: NextResponse, csp: string) {
  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), browsing-topics=()",
  );
  if (process.env.NODE_ENV === "production") {
    response.headers.set("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload");
  }
  return response;
}

export async function updateSession(
  request: NextRequest,
  requestHeaders: Headers,
  csp: string,
) {
  const next = () =>
    applySecurityHeaders(NextResponse.next({ request: { headers: requestHeaders } }), csp);
  const redirectTo = (pathname: string) =>
    applySecurityHeaders(NextResponse.redirect(new URL(pathname, request.url)), csp);

  let response = next();
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return response;

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = next();
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
      },
    },
  });

  const { data } = await supabase.auth.getClaims();
  const pathname = request.nextUrl.pathname;
  const isPublic = pathname.startsWith("/login") || pathname.startsWith("/setup");

  if (!data?.claims) {
    return isPublic ? response : redirectTo("/login");
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("role, active")
    .eq("id", String(data.claims.sub))
    .maybeSingle();
  const hasStaffAccess =
    profile?.active === true && ["admin", "employee"].includes(String(profile.role));

  if (!hasStaffAccess) {
    await supabase.auth.signOut();
    return redirectTo(
      `/login?error=${encodeURIComponent("Esta cuenta todavía no tiene acceso al sistema")}`,
    );
  }
  if (isPublic) return redirectTo("/");
  return response;
}
