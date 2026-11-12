/* AVEN GLOBAL service worker.
 * Caches only the static application shell (scripts, styles, brand images) so
 * the app installs and opens quickly. Business data (/api) is NEVER cached:
 * every record comes live from the central server, and sign-out leaves nothing
 * behind on the device. */
const CACHE = "aven-shell-v1";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return; // live data only, never cached
  const isStatic = url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/brand/");
  if (!isStatic) {
    // Pages: network first; offline shows a plain notice instead of stale data.
    if (event.request.mode === "navigate") {
      event.respondWith(
        fetch(event.request).catch(
          () =>
            new Response(
              "<!doctype html><meta name=viewport content='width=device-width'><title>AVEN GLOBAL</title>" +
                "<body style='background:#08090c;color:#e8e2d4;font-family:system-ui;padding:2rem'>" +
                "<h1>You are offline</h1><p>AVEN GLOBAL needs a connection to the central server. " +
                "Reconnect and try again.</p></body>",
              { headers: { "Content-Type": "text/html; charset=utf-8" } },
            ),
        ),
      );
    }
    return;
  }
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const hit = await cache.match(event.request);
      if (hit) return hit;
      const response = await fetch(event.request);
      if (response.ok) cache.put(event.request, response.clone());
      return response;
    }),
  );
});
