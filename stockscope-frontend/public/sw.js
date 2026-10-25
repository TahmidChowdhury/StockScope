// Only this public fallback is stored. Research, sessions, API responses and
// Next.js assets always use the network, so deployments cannot serve stale data.
const OFFLINE_CACHE_PREFIX = 'stockscope-offline-'
// Bump this version whenever offline.html changes so installed apps refresh it.
const OFFLINE_CACHE = `${OFFLINE_CACHE_PREFIX}v1`
const OFFLINE_URL = '/offline.html'

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(OFFLINE_CACHE).then((cache) =>
      cache.add(new Request(OFFLINE_URL, { cache: 'reload', credentials: 'omit' })),
    ),
  )
  // Let updates activate after existing windows close. Never reload an active
  // research session or mix an existing page with a newly activated worker.
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys
        .filter((key) => key.startsWith(OFFLINE_CACHE_PREFIX) && key !== OFFLINE_CACHE)
        .map((key) => caches.delete(key)),
    )),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)
  if (
    request.method !== 'GET' ||
    request.mode !== 'navigate' ||
    url.origin !== self.location.origin ||
    url.pathname === '/api' ||
    url.pathname.startsWith('/api/')
  ) return

  event.respondWith(
    fetch(request).catch(async () => {
      const cache = await caches.open(OFFLINE_CACHE)
      const fallback = await cache.match(OFFLINE_URL)
      return fallback || Response.error()
    }),
  )
})
