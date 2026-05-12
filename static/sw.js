self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('pib-v1').then(cache => {
      return cache.addAll([
        '/',
        '/static/manifest.json'
      ]);
    })
  );
});
self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then(response => response || fetch(e.request))
  );
});