import { create } from 'zustand'
import * as Sentry from '@sentry/react'
import { authAPI } from '@/api/auth'

const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  init: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) { set({ isLoading: false }); return }
    try {
      const { data } = await authAPI.me()
      Sentry.setUser({ id: data.id, username: data.username })
      set({ user: data, isAuthenticated: true, isLoading: false })
    } catch {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  login: async (credentials) => {
    const { data } = await authAPI.login(credentials)
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    const { data: user } = await authAPI.me()
    Sentry.setUser({ id: user.id, username: user.username })
    set({ user, isAuthenticated: true })
    return user
  },

  logout: async () => {
    try {
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) await authAPI.logout({ refresh })
    } catch { /* token already expired or invalid — nothing to do */ }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    Sentry.setUser(null)
    set({ user: null, isAuthenticated: false })
  },

  setUser: (user) => set({ user }),
}))

export default useAuthStore
