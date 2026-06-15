// LiveStream Felix Service Worker v1.0
const STATIC_CACHE = 'lsf-static-v1';
const DYNAMIC_CACHE = 'lsf-dynamic-v1';

const PRECACHE_URLS = [
  '/dashboard/',
  '/accounts/login/',
  '/rooms/join/',
  '/billing/pricing/',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(PRECACHE_URLS.map(url => new Request(url, {mode:'no-cors'}))))
      .then(() => self.skipWaiting())
      .catch(err => console.log('[SW] Install error:', err))
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== STATIC_CACHE && k !== DYNAMIC_CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  if (url.protocol === 'ws:' || url.protocol === 'wss:') return;
  if (request.method !== 'GET') return;
  if (url.pathname.startsWith('/admin/')) return;

  if (url.pathname.startsWith('/static/') || url.hostname !== self.location.hostname) {
    event.respondWith(cacheFirst(request));
  } else {
    event.respondWith(networkFirst(request));
  }
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch { return new Response('Offline', {status:503}); }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(`<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Offline - LiveStream Felix</title><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#080c14;color:#eef2ff;font-family:Inter,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;padding:24px}.wrap{max-width:400px}.icon{font-size:72px;margin-bottom:20px}h1{font-size:26px;font-weight:700;margin-bottom:12px}p{color:#6b7db3;margin-bottom:24px;line-height:1.6}button{background:#5b6ef5;color:#fff;border:none;padding:14px 28px;border-radius:10px;font-size:16px;font-weight:700;cursor:pointer;width:100%}</style></head><body><div class="wrap"><div class="icon">📡</div><h1>You are Offline</h1><p>LiveStream Felix needs internet to connect you with others.</p><button onclick="location.reload()">Retry Connection</button></div></body></html>`, {headers:{'Content-Type':'text/html'}});
  }
}

self.addEventListener('push', event => {
  let data = {title:'LiveStream Felix', body:'New notification', icon:'/static/icons/icon-192.png'};
  if (event.data) { try { data = {...data,...event.data.json()}; } catch{} }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || '/static/icons/icon-192.png',
      badge: '/static/icons/icon-72.png',
      vibrate: [100,50,100],
      data: {url: data.url || '/dashboard/'},
      actions: [{action:'open',title:'Open'},{action:'dismiss',title:'Dismiss'}],
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  if (event.action === 'dismiss') return;
  const url = event.notification.data?.url || '/dashboard/';
  event.waitUntil(
    clients.matchAll({type:'window',includeUncontrolled:true}).then(list => {
      for (const c of list) { if ('focus' in c) { c.navigate(url); return c.focus(); } }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
