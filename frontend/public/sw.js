/* global clients */
// CricFun Service Worker — handles Web Push events and notification clicks.

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', event => event.waitUntil(clients.claim()))

// ── Push received ──────────────────────────────────────────────────────────
self.addEventListener('push', event => {
  let data = {}
  try { data = event.data?.json() ?? {} } catch { /* ignore malformed payload */ }

  const title   = data.title ?? 'CricFun'
  const options = {
    body:      data.body  ?? '',
    icon:      '/logo.PNG',
    badge:     '/logo.PNG',
    tag:       data.tag ?? 'cricfun-notification',
    renotify:  true,
    data:      { url: data.url ?? '/' },
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

// ── Notification clicked ───────────────────────────────────────────────────
self.addEventListener('notificationclick', event => {
  event.notification.close()
  const url = event.notification.data?.url ?? '/'

  event.waitUntil(
    clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then(list => {
        // Focus existing tab if open
        for (const client of list) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.navigate(url)
            return client.focus()
          }
        }
        // Otherwise open a new tab
        return clients.openWindow(url)
      })
  )
})
