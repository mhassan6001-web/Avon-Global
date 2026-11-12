import { NextResponse, type NextRequest } from "next/server";

/**
 * Convenience redirect only: send visitors without a session cookie to sign-in.
 * Real access control is enforced by the API on every request.
 */
const PUBLIC_PREFIXES = ["/sign-in", "/two-factor", "/invite", "/reset-password", "/healthz"];

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (PUBLIC_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return NextResponse.next();
  }
  if (!request.cookies.get("aven_session")) {
    const url = request.nextUrl.clone();
    url.pathname = "/sign-in";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  // Skip API proxy, Next internals and static files.
  matcher: ["/((?!api/|_next/|favicon|.*\\.[a-zA-Z0-9]+$).*)"],
};
