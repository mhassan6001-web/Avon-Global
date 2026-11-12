/** Liveness endpoint for the web container (does not call the API). */
export const dynamic = "force-dynamic";

export function GET() {
  return Response.json(
    { status: "ok", service: "aven-global-web" },
    { headers: { "Cache-Control": "no-store" } },
  );
}
