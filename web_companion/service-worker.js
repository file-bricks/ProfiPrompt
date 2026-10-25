const CACHE_NAME = "profiprompt-companion-v7";
const ASSETS = [
  "./",
  "./index.html",
  "./app.css",
  "./app.js",
  "./i18n.js",
  "./translations.json",
  "./library.js",
  "./manifest.webmanifest",
  "./service-worker.js",
  "./sample-library.json",
  "./icons/profiprompt-companion.svg",
  "./icons/Icon-192.png",
  "./icons/Icon-512.png",
  "./icons/Icon-maskable-192.png",
  "./icons/Icon-maskable-512.png",
  "./icons/apple-touch-icon-180.png",
  "./icons/favicon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }
  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(event.request).then((response) => {
        if (!response || response.status !== 200 || response.type === "opaque") {
          return response;
        }
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone)).catch(() => {});
        return response;
      }).catch(() => {
        if (event.request.mode === "navigate") {
          return caches.match("./index.html").then((shell) =>
            shell ?? new Response("", { status: 503, statusText: "Service Unavailable" }),
          );
        }
        return new Response("", { status: 503, statusText: "Service Unavailable" });
      });
    }),
  );
});
