/**
 * Service Worker — Image Cache + Offline Page
 * Caches proxied song thumbnails in CacheStorage for fast revisits.
 * Background images (.webp) are also cached on first load.
 * Serves a themed offline page when the network is unavailable.
 */

const CACHE_NAME = "song-dl-images-v1";
const OFFLINE_CACHE = "song-dl-offline-v1";
const OFFLINE_PAGE = "/offline.html";
const MAX_CACHE_ENTRIES = 500;

// Patterns to cache
const CACHEABLE = [
  /\/proxy_image\?/, // backend proxy
  /\/api\/proxy-image\?/, // frontend proxy path
  /\.webp(\?|$)/, // background textures
];

function shouldCache(url) {
  return CACHEABLE.some((re) => re.test(url));
}

// Install — pre-cache background textures + offline page
self.addEventListener("install", (event) => {
  event.waitUntil(
    Promise.all([
      caches
        .open(CACHE_NAME)
        .then((cache) =>
          cache
            .addAll([
              "/dark.webp",
              "/light.webp",
              "/mobile_dark.webp",
              "/mobile_light.webp",
            ])
            .catch(() => {}),
        ),
      caches
        .open(OFFLINE_CACHE)
        .then((cache) => cache.add(OFFLINE_PAGE).catch(() => {})),
    ]),
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener("activate", (event) => {
  const keepCaches = [CACHE_NAME, OFFLINE_CACHE];
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k.startsWith("song-dl-") && !keepCaches.includes(k))
            .map((k) => caches.delete(k)),
        ),
      ),
  );
  self.clients.claim();
});

// Fetch — cache-first for images, offline fallback for navigation
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  // Navigation requests (HTML pages) — network first, offline fallback
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.open(OFFLINE_CACHE).then((cache) => cache.match(OFFLINE_PAGE)),
      ),
    );
    return;
  }

  // Cacheable assets (images, webp) — cache first
  if (!shouldCache(event.request.url)) return;

  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const cached = await cache.match(event.request);
      if (cached) return cached;

      try {
        const response = await fetch(event.request);
        if (response.ok) {
          // Clone before consuming
          cache.put(event.request, response.clone());
          // Trim cache to MAX_CACHE_ENTRIES
          trimCache(cache);
        }
        return response;
      } catch {
        return new Response("", { status: 404 });
      }
    }),
  );
});

async function trimCache(cache) {
  const keys = await cache.keys();
  if (keys.length > MAX_CACHE_ENTRIES) {
    // Delete oldest entries (first in list)
    const toDelete = keys.slice(0, keys.length - MAX_CACHE_ENTRIES);
    await Promise.all(toDelete.map((k) => cache.delete(k)));
  }
}
