{% load static %}// NKMB Help Desk service worker.
// Strategy: pages always come from the network (they are user-specific and must never be
// served stale); static files are cached after first use; an offline page is the fallback.
const CACHE = "nkmb-helpdesk-v2";
const OFFLINE_URL = "{% url 'pwa_offline' %}";
const PRECACHE = [
  OFFLINE_URL,
  "{% static 'images/icons/icon-192.png' %}",
  "{% static 'images/NKMBV-37.png' %}"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // Page navigations: network only, offline page if the network is down.
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  // Static files: serve from cache, refresh in the background.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.open(CACHE).then((cache) =>
        cache.match(req).then((hit) => {
          const fresh = fetch(req).then((res) => {
            if (res.ok) cache.put(req, res.clone());
            return res;
          }).catch(() => hit);
          return hit || fresh;
        })
      )
    );
  }
});
