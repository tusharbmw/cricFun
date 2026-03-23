import { useEffect, useState } from 'react'
import { notificationsAPI } from '@/api/notifications'

const VAPID_PUBLIC_KEY = import.meta.env.VITE_VAPID_PUBLIC_KEY ?? ''

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64  = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw     = atob(base64)
  return Uint8Array.from([...raw].map(c => c.charCodeAt(0)))
}

export function usePush() {
  const supported = typeof window !== 'undefined'
    && 'serviceWorker' in navigator
    && 'PushManager' in window

  const [permission, setPermission] = useState(
    supported ? Notification.permission : 'default'
  )
  const [subscribed, setSubscribed] = useState(false)
  const [loading,    setLoading]    = useState(false)

  // Check if already subscribed on mount
  useEffect(() => {
    if (!supported) return
    navigator.serviceWorker.ready.then(reg =>
      reg.pushManager.getSubscription().then(sub => setSubscribed(!!sub))
    )
  }, [supported])

  async function subscribe() {
    if (!VAPID_PUBLIC_KEY) {
      console.warn('VITE_VAPID_PUBLIC_KEY is not set')
      return
    }
    setLoading(true)
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      })
      await notificationsAPI.savePush(sub.toJSON())
      setSubscribed(true)
      setPermission(Notification.permission)
    } catch (err) {
      console.error('Push subscribe failed:', err)
      setPermission(Notification.permission)
    } finally {
      setLoading(false)
    }
  }

  async function unsubscribe() {
    setLoading(true)
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        await notificationsAPI.deletePush({ endpoint: sub.endpoint })
        await sub.unsubscribe()
        setSubscribed(false)
      }
    } catch (err) {
      console.error('Push unsubscribe failed:', err)
    } finally {
      setLoading(false)
    }
  }

  return {
    supported,
    subscribed,
    loading,
    denied: permission === 'denied',
    subscribe,
    unsubscribe,
  }
}
